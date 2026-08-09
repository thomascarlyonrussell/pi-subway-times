import argparse
import csv
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from unittest import mock

from subway_sign.gtfs_refresh import DISCOVERY_CATALOG_FILE, TRIP_RESOLUTION_INDEX_FILE, GtfsSource, GtfsStaticRefresher, get_active_data_dir


REQUIRED_CONTENT = {
    "agency.txt": [["agency_id", "agency_name", "agency_url", "agency_timezone"], ["MTA", "MTA", "https://example.com", "America/New_York"]],
    "routes.txt": [["route_id", "route_short_name", "route_long_name", "route_type", "route_color"], ["F", "F", "Queens Blvd", "1", "FF6319"]],
    "trips.txt": [["route_id", "service_id", "trip_id", "trip_headsign"], ["F", "WKD", "trip.1", "Uptown"]],
    "stops.txt": [["stop_id", "stop_name"], ["D14N", "7 Av"]],
    "stop_times.txt": [["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"], ["trip.1", "08:00:00", "08:00:00", "D14N", "1"]],
}


class StatusRecorder:
    def __init__(self):
        self.events = []

    def update(self, phase, completed=0, total=0, detail=""):
        self.events.append((phase, completed, total, detail))


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
    temp_root = pathlib.Path(__file__).resolve().parents[1] / "tests" / ".tmp"
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
        status_recorder = StatusRecorder()
        refresher.status_renderer = status_recorder

        with mock.patch("subway_sign.gtfs_refresh._state_files", return_value={"current": state_dir / "current.json"}):
            try:
                get_active_data_dir()
            except RuntimeError as exc:
                assert "No active GTFS static snapshot" in str(exc)
            else:
                raise AssertionError("Missing active snapshot should fail clearly")

        # Monkey patch requests download by copying local zip files.
        original_download = refresher._download_source
        download_calls = []

        def _local_download(source, target_dir):
            download_calls.append(source.name)
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
        snapshot_dir = state_dir / "snapshots" / first["dataset_id"]
        with (snapshot_dir / DISCOVERY_CATALOG_FILE).open("r", encoding="utf-8") as handle:
            catalog = json.load(handle)
        assert catalog["routes"][0]["route_color"] == "AABBCC", "Catalog should preserve supplemented route metadata"
        assert catalog["stops"] == [
            {"stop_name": "7 Av", "stop_ids": ["D14N"], "route_ids": ["F"], "directions": ["N"]}
        ], "Catalog should preserve route and direction discovery data"
        with (snapshot_dir / TRIP_RESOLUTION_INDEX_FILE).open("r", encoding="utf-8") as handle:
            res_index = json.load(handle)
        assert "trip.1" in res_index["trips"], "Trip resolution index should contain trip.1"
        assert res_index["trips"]["trip.1"] == {
            "route_id": "F",
            "service_id": "WKD",
            "trip_id": "trip.1",
            "trip_headsign": "Uptown",
            "start_time": "08:00:00",
            "stop_ids": ["D14N"],
        }, "Trip resolution index entry should match expected structure"
        assert not (snapshot_dir / "stop_times.txt").exists(), "Snapshots should omit unused stop_times.txt"
        assert not (snapshot_dir / "shapes.txt").exists(), "Snapshots should omit unused shapes.txt"
        with mock.patch("subway_sign.gtfs_refresh._state_files", return_value={"current": state_dir / "current.json"}):
            from subway_sign.trips import get_discoverable_routes, get_discoverable_stops

            assert get_discoverable_routes()[0]["route_color"] == "AABBCC"
            assert get_discoverable_stops(["F"], ["N"])[0]["stop_name"] == "7 Av"

            phases = {event[0] for event in status_recorder.events}
            assert {"setup", "stations", "finalize", "ready"}.issubset(phases), "Refresh should publish setup status phases"

            fresh_res = refresher.refresh(force=False, dry_run=False)
            assert fresh_res == {
                "ok": True,
                "promoted": False,
                "skipped": True,
                "reason": "active_snapshot_fresh",
                "dataset_id": first["dataset_id"],
                "downloads": [],
            }, "Fresh active snapshots should skip before download"
            assert download_calls == ["base", "supplemented"], "Fresh snapshots should avoid archive downloads"

            current_state_path = state_dir / "current.json"
            current_state = json.loads(current_state_path.read_text(encoding="utf-8"))
            current_state["activated_at_epoch"] = int(time.time()) - (24 * 60 * 60)
            current_state_path.write_text(json.dumps(current_state), encoding="utf-8")

            unchanged_res = refresher.refresh(force=False, dry_run=False)
            assert unchanged_res.get("ok") and unchanged_res.get("unchanged"), "Unchanged feeds should be bypassed when force=False"
            assert download_calls == ["base", "supplemented", "base", "supplemented"], "Stale snapshots should download archives"

        _build_archive(supplemented_zip, "00FF00")
        second = refresher.refresh(force=True, dry_run=False)
        assert second.get("ok"), f"Second promotion failed: {second}"
        assert download_calls == ["base", "supplemented", "base", "supplemented", "base", "supplemented"], "Forced refreshes should download archives"

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
                "fresh_snapshot_skips_downloads",
                "stale_snapshot_downloads_archives",
                "forced_refresh_downloads_archives",
                "unchanged_feed_bypassed",
                "failure_preserves_previous_dataset",
                "missing_active_snapshot_fails_clearly",
                "discovery_catalog_preserves_supplement_precedence",
                "configuration_discovery_reads_compact_catalog",
                "refresh_publishes_bootstrap_status_phases",
                "promoted_snapshot_omits_unused_large_files",
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


def test_gtfs_refresh_dev_validation():
    result = run_dev_validation()
    assert result.get("ok") is True, f"GTFS refresh validation failed: {result}"


def test_invalid_active_snapshot_state_does_not_skip_refresh():
    with tempfile.TemporaryDirectory() as temp_dir:
        state_dir = pathlib.Path(temp_dir)
        refresher = GtfsStaticRefresher(
            state_dir=state_dir,
            sources=[GtfsSource("base", "https://example.com/base.zip")],
            timeout_sec=10,
            transition_window_hours=24,
            snapshot_retention_count=2,
            service_action="none",
        )
        refresher._download_source = mock.Mock(side_effect=RuntimeError("download attempted"))

        for state in ("not json", json.dumps({"dataset_id": "future", "activated_at_epoch": time.time() + 1})):
            (state_dir / "current.json").write_text(state, encoding="utf-8")
            result = refresher.refresh()
            assert not result["ok"]
            refresher._download_source.assert_called_once()
            refresher._download_source.reset_mock()


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
