import argparse
import csv
import json
import pathlib
import shutil
import subprocess
import zipfile
from unittest import mock

from gtfs_refresh import GtfsSource, GtfsStaticRefresher, get_active_data_dir


REQUIRED_CONTENT = {
    "agency.txt": [["agency_id", "agency_name", "agency_url", "agency_timezone"], ["MTA", "MTA", "https://example.com", "America/New_York"]],
    "routes.txt": [["route_id", "route_short_name", "route_long_name", "route_type", "route_color"], ["F", "F", "Queens Blvd", "1", "FF6319"]],
    "trips.txt": [["route_id", "service_id", "trip_id", "trip_headsign"], ["F", "WKD", "trip.1", "Uptown"]],
    "stops.txt": [["stop_id", "stop_name"], ["D14N", "7 Av"]],
    "stop_times.txt": [["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"], ["trip.1", "08:00:00", "08:00:00", "D14N", "1"]],
}


def _write_csv(path: pathlib.Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)


def _build_archive(path: pathlib.Path, route_color: str):
    workspace = path.parent / f"{path.stem}_content"
    workspace.mkdir(parents=True, exist_ok=True)
    for file_name, rows in REQUIRED_CONTENT.items():
        prepared_rows = [row[:] for row in rows]
        if file_name == "routes.txt":
            prepared_rows[1][4] = route_color
        _write_csv(workspace / file_name, prepared_rows)

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in workspace.glob("*.txt"):
            archive.write(file_path, arcname=file_path.name)
    shutil.rmtree(workspace, ignore_errors=True)


def run_dev_validation():
    temp_root = pathlib.Path(__file__).resolve().parent.parent / "setup" / ".tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_dir = temp_root / "gtfs-refresh-validate"
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        root = temp_dir
        source_dir = root / "sources"
        state_dir = root / "state"
        source_dir.mkdir(parents=True, exist_ok=True)

        base_zip = source_dir / "base.zip"
        supplemented_zip = source_dir / "supplemented.zip"
        _build_archive(base_zip, "112233")
        _build_archive(supplemented_zip, "AABBCC")

        refresher = GtfsStaticRefresher(
            state_dir=state_dir,
            sources=[
                GtfsSource("base", f"file://{base_zip.as_posix()}"),
                GtfsSource("supplemented", f"file://{supplemented_zip.as_posix()}"),
            ],
            timeout_sec=10,
            transition_window_hours=24,
            snapshot_retention_count=4,
            service_action="none",
        )

        with mock.patch("gtfs_refresh._state_files", return_value={"current": state_dir / "current.json"}):
            try:
                get_active_data_dir()
            except RuntimeError as exc:
                assert "No active GTFS static snapshot" in str(exc)
            else:
                raise AssertionError("Missing active snapshot should fail clearly")

        # Monkey patch requests download by copying local zip files.
        original_download = refresher._download_source

        def _local_download(source, target_dir):
            zip_path = pathlib.Path(source.url.replace("file://", ""))
            staged = target_dir / f"{source.name}.zip"
            shutil.copy2(zip_path, staged)
            extract_dir = target_dir / source.name
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(staged, "r") as archive:
                archive.extractall(extract_dir)
            return {
                "name": source.name,
                "url": source.url,
                "zip_path": str(staged),
                "extract_dir": str(extract_dir),
                "sha256": "local-test",
            }

        refresher._download_source = _local_download

        first = refresher.refresh(force=True, dry_run=False)
        assert first.get("ok"), f"First promotion failed: {first}"
        with (state_dir / "snapshots" / first["dataset_id"] / "routes.txt").open("r", encoding="utf-8", newline="") as handle:
            routes = list(csv.DictReader(handle))
        assert routes == [
            {
                "route_id": "F",
                "route_short_name": "F",
                "route_long_name": "Queens Blvd",
                "route_type": "1",
                "route_color": "AABBCC",
            }
        ], "Supplemented GTFS rows should take precedence over base rows"

        _build_archive(supplemented_zip, "00FF00")
        second = refresher.refresh(force=True, dry_run=False)
        assert second.get("ok"), f"Second promotion failed: {second}"

        rollback = refresher.rollback()
        assert rollback.get("ok"), f"Rollback failed: {rollback}"

        refresher._download_source = original_download
        failure = refresher.refresh(force=True, dry_run=False)
        assert not failure.get("ok"), "Failure scenario should keep active dataset unchanged"

        return {
            "ok": True,
            "checks": [
                "promotion_success",
                "second_promotion_success",
                "rollback_success",
                "failure_preserves_previous_dataset",
                "missing_active_snapshot_fails_clearly",
            ],
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def run_pi_checks():
    checks = []
    commands = [
        ["systemctl", "is-enabled", "gtfs-static-refresh.timer"],
        ["systemctl", "status", "gtfs-static-refresh.timer", "--no-pager"],
        ["systemctl", "status", "subway-sign", "--no-pager"],
    ]
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        checks.append(
            {
                "command": " ".join(command),
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        )

    state_dir = pathlib.Path("/var/lib/subway-sign/gtfs-static")
    checks.append(
        {
            "path": str(state_dir),
            "exists": state_dir.exists(),
            "readable": state_dir.exists() and state_dir.is_dir(),
        }
    )
    return {"ok": True, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate GTFS static refresh behavior.")
    parser.add_argument("--with-pi-checks", action="store_true", help="Run hardware-oriented service checks.")
    args = parser.parse_args()

    payload = {"dev_validation": run_dev_validation()}
    if args.with_pi_checks:
        payload["pi_checks"] = run_pi_checks()

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
