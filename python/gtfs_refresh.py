import argparse
import csv
import hashlib
import json
import logging
import os
import pathlib
import shutil
import sqlite3
import subprocess
import tempfile
import time
import zipfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

import requests

from config import load_runtime_config


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_STATE_DIR = REPO_ROOT / "setup" / "gtfs_static_state"
SYSTEM_STATE_DIR = pathlib.Path("/var/lib/subway-sign/gtfs-static")

LOG_FILE = pathlib.Path("/var/log/subway_sign.log")
LOG_FILE_FALLBACK = REPO_ROOT / "setup" / "subway_sign.log"

CURRENT_STATE_FILE = "current.json"
PREVIOUS_STATE_FILE = "previous.json"
SNAPSHOTS_DIR_NAME = "snapshots"

BASE_ARCHIVE_NAME = "google_transit.zip"
SUPPLEMENT_ARCHIVE_NAME = "google_transit_supplemented.zip"

REQUIRED_FILES = {
    "agency.txt",
    "routes.txt",
    "trips.txt",
    "stops.txt",
    "stop_times.txt",
}

KEY_FIELDS_BY_FILE = {
    "agency.txt": ("agency_id",),
    "calendar.txt": ("service_id",),
    "calendar_dates.txt": ("service_id", "date"),
    "routes.txt": ("route_id",),
    "shapes.txt": ("shape_id", "shape_pt_sequence"),
    "stop_times.txt": ("trip_id", "stop_sequence", "stop_id"),
    "stops.txt": ("stop_id",),
    "transfers.txt": ("from_stop_id", "to_stop_id", "from_route_id", "to_route_id", "from_trip_id", "to_trip_id"),
    "trips.txt": ("trip_id",),
}

DEFAULT_SOURCES = (
    ("base", "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip"),
    ("supplemented", "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_supplemented.zip"),
)


def _configure_logger() -> logging.Logger:
    logger = logging.getLogger("gtfs_refresh")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    log_target = LOG_FILE if LOG_FILE.parent.exists() and os.access(LOG_FILE.parent, os.W_OK) else LOG_FILE_FALLBACK
    log_target.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_target, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    return logger


LOG = _configure_logger()


@dataclass(frozen=True)
class GtfsSource:
    name: str
    url: str


def _sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: pathlib.Path) -> Optional[Dict]:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _save_json_atomic(path: pathlib.Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent), encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temp_path = pathlib.Path(handle.name)
    os.replace(temp_path, path)


def _resolve_state_dir() -> pathlib.Path:
    system_parent = SYSTEM_STATE_DIR.parent
    if system_parent.exists() and os.access(system_parent, os.W_OK):
        SYSTEM_STATE_DIR.mkdir(parents=True, exist_ok=True)
        return SYSTEM_STATE_DIR
    if system_parent.parent.exists() and os.access(system_parent.parent, os.W_OK):
        SYSTEM_STATE_DIR.mkdir(parents=True, exist_ok=True)
        return SYSTEM_STATE_DIR
    DEFAULT_STATE_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_STATE_DIR


def _stable_row_key(row: Dict[str, str], key_fields: Sequence[str]) -> str:
    values = [row.get(field, "").strip() for field in key_fields]
    if any(values):
        return "|".join(values)
    serialized = json.dumps(row, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _merge_csv(base_file: pathlib.Path, supplement_file: pathlib.Path, output_file: pathlib.Path, key_fields: Sequence[str]) -> None:
    with base_file.open("r", encoding="utf-8", newline="") as base_handle, supplement_file.open(
        "r", encoding="utf-8", newline=""
    ) as supplement_handle:
        base_reader = csv.DictReader(base_handle)
        supplement_reader = csv.DictReader(supplement_handle)
        headers = list(dict.fromkeys((base_reader.fieldnames or []) + (supplement_reader.fieldnames or [])))

        output_file.parent.mkdir(parents=True, exist_ok=True)
        descriptor, database_name = tempfile.mkstemp(prefix="gtfs-merge-", suffix=".sqlite3", dir=str(output_file.parent))
        os.close(descriptor)
        database_path = pathlib.Path(database_name)
        connection = sqlite3.connect(database_path)
        try:
            with output_file.open("w", encoding="utf-8", newline="") as output_handle:
                connection.execute("PRAGMA journal_mode=OFF")
                connection.execute("PRAGMA synchronous=OFF")
                connection.execute("CREATE TABLE seen_keys (key TEXT PRIMARY KEY) WITHOUT ROWID")

                writer = csv.DictWriter(output_handle, fieldnames=headers)
                writer.writeheader()
                for row in supplement_reader:
                    key = _stable_row_key(row, key_fields)
                    result = connection.execute("INSERT OR IGNORE INTO seen_keys VALUES (?)", (key,))
                    if result.rowcount:
                        writer.writerow(row)
                for row in base_reader:
                    key = _stable_row_key(row, key_fields)
                    result = connection.execute("INSERT OR IGNORE INTO seen_keys VALUES (?)", (key,))
                    if result.rowcount:
                        writer.writerow(row)
                connection.commit()
        finally:
            connection.close()
            database_path.unlink(missing_ok=True)


def _run_service_action(action: str) -> subprocess.CompletedProcess:
    command = ["systemctl", action, "subway-sign"]
    if os.name == "nt":
        message = "Skipped subway-sign service action because systemd is unavailable on Windows."
        LOG.info(message)
        return subprocess.CompletedProcess(command, returncode=0, stdout="", stderr=message)
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return result
    return subprocess.run(["sudo"] + command, capture_output=True, text=True, check=False)


class GtfsStaticRefresher:
    def __init__(
        self,
        state_dir: pathlib.Path,
        sources: Sequence[GtfsSource],
        timeout_sec: int,
        transition_window_hours: int,
        snapshot_retention_count: int,
        service_action: str,
        alert_command: str = "",
    ):
        self.state_dir = state_dir
        self.sources = list(sources)
        self.timeout_sec = timeout_sec
        self.transition_window_hours = transition_window_hours
        self.snapshot_retention_count = snapshot_retention_count
        self.service_action = service_action
        self.alert_command = alert_command

        self.snapshots_dir = self.state_dir / SNAPSHOTS_DIR_NAME
        self.current_file = self.state_dir / CURRENT_STATE_FILE
        self.previous_file = self.state_dir / PREVIOUS_STATE_FILE

    @classmethod
    def from_config(cls, config: Optional[Dict] = None) -> "GtfsStaticRefresher":
        runtime_config = config or load_runtime_config()
        refresh_cfg = runtime_config.get("gtfs_static_refresh", {})
        configured_sources = refresh_cfg.get("sources") or DEFAULT_SOURCES
        sources = [GtfsSource(name=str(name), url=str(url)) for name, url in configured_sources]
        return cls(
            state_dir=_resolve_state_dir(),
            sources=sources,
            timeout_sec=int(refresh_cfg.get("request_timeout_sec", 30)),
            transition_window_hours=int(refresh_cfg.get("transition_window_hours", 168)),
            snapshot_retention_count=int(refresh_cfg.get("snapshot_retention_count", 8)),
            service_action=str(refresh_cfg.get("service_action", "restart")).strip().lower(),
            alert_command=str(refresh_cfg.get("alert_command", "")).strip(),
        )

    def _download_source(self, source: GtfsSource, target_dir: pathlib.Path) -> Dict[str, str]:
        LOG.info("Downloading GTFS archive '%s' from %s", source.name, source.url)
        response = requests.get(source.url, timeout=self.timeout_sec)
        response.raise_for_status()

        zip_path = target_dir / f"{source.name}.zip"
        zip_path.write_bytes(response.content)
        if zip_path.stat().st_size == 0:
            raise RuntimeError(f"Downloaded empty archive: {source.url}")

        checksum = _sha256_file(zip_path)
        extract_dir = target_dir / source.name
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as archive:
            archive.extractall(extract_dir)

        return {
            "name": source.name,
            "url": source.url,
            "zip_path": str(zip_path),
            "extract_dir": str(extract_dir),
            "sha256": checksum,
        }

    def _validate_dataset(self, dataset_dir: pathlib.Path) -> None:
        for file_name in REQUIRED_FILES:
            file_path = dataset_dir / file_name
            if not file_path.exists():
                raise RuntimeError(f"Missing required GTFS file after merge: {file_name}")
            with file_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle)
                try:
                    next(reader)
                    next(reader)
                except StopIteration:
                    raise RuntimeError(f"GTFS file has no data rows: {file_name}")
            if file_path.stat().st_size == 0:
                raise RuntimeError(f"GTFS file has no data rows: {file_name}")

    def _merge_archives(self, base_dir: pathlib.Path, supplement_dir: pathlib.Path, output_dir: pathlib.Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        base_files = {path.name: path for path in base_dir.glob("*.txt")}
        supplement_files = {path.name: path for path in supplement_dir.glob("*.txt")}
        all_names = sorted(set(base_files.keys()) | set(supplement_files.keys()))

        for file_name in all_names:
            base_file = base_files.get(file_name)
            supplement_file = supplement_files.get(file_name)
            output_file = output_dir / file_name
            LOG.info("Merging GTFS file %s", file_name)
            if base_file and supplement_file and file_name in KEY_FIELDS_BY_FILE:
                _merge_csv(base_file, supplement_file, output_file, KEY_FIELDS_BY_FILE[file_name])
            elif supplement_file:
                shutil.copy2(supplement_file, output_file)
            elif base_file:
                shutil.copy2(base_file, output_file)

    def _cleanup_old_snapshots(self, protected_paths: Sequence[pathlib.Path]) -> None:
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        all_snapshots = sorted(
            [path for path in self.snapshots_dir.iterdir() if path.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        keep: List[pathlib.Path] = list(protected_paths)[:]
        for snapshot in all_snapshots:
            if snapshot in keep:
                continue
            if len(keep) < self.snapshot_retention_count:
                keep.append(snapshot)
                continue
            shutil.rmtree(snapshot, ignore_errors=True)

    def _state_for_snapshot(self, snapshot_dir: pathlib.Path, activated_at: int) -> Dict:
        return {
            "dataset_id": snapshot_dir.name,
            "path": str(snapshot_dir),
            "activated_at_epoch": activated_at,
            "transition_window_end_epoch": activated_at + (self.transition_window_hours * 3600),
        }

    def _notify_failure(self, message: str) -> None:
        LOG.error(message)
        if self.alert_command:
            subprocess.run(self.alert_command, shell=True, check=False, capture_output=True, text=True)

    def refresh(self, force: bool = False, dry_run: bool = False) -> Dict:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        working_dir = self.state_dir / "staging" / timestamp
        working_dir.mkdir(parents=True, exist_ok=True)

        downloaded = []
        try:
            for source in self.sources:
                downloaded.append(self._download_source(source, working_dir))

            by_name = {item["name"]: item for item in downloaded}
            if "base" not in by_name or "supplemented" not in by_name:
                raise RuntimeError("Source list must include both 'base' and 'supplemented'")

            dataset_id = timestamp
            snapshot_dir = self.snapshots_dir / dataset_id
            LOG.info("Merging GTFS archives into candidate snapshot %s", dataset_id)
            self._merge_archives(
                pathlib.Path(by_name["base"]["extract_dir"]),
                pathlib.Path(by_name["supplemented"]["extract_dir"]),
                snapshot_dir,
            )
            LOG.info("Validating candidate snapshot %s", dataset_id)
            self._validate_dataset(snapshot_dir)

            if dry_run:
                shutil.rmtree(snapshot_dir, ignore_errors=True)
                return {
                    "ok": True,
                    "promoted": False,
                    "dry_run": True,
                    "downloads": downloaded,
                }

            LOG.info("Calculating candidate snapshot checksums for %s", dataset_id)
            checksums = {path.name: _sha256_file(path) for path in snapshot_dir.glob("*.txt")}
            manifest = {
                "dataset_id": dataset_id,
                "created_at_epoch": int(time.time()),
                "sources": downloaded,
                "file_checksums": checksums,
                "force": force,
            }
            _save_json_atomic(snapshot_dir / "manifest.json", manifest)

            activated_at = int(time.time())
            prior_current = _load_json(self.current_file)
            if prior_current:
                _save_json_atomic(self.previous_file, prior_current)

            current_state = self._state_for_snapshot(snapshot_dir, activated_at)
            _save_json_atomic(self.current_file, current_state)

            protected = [snapshot_dir]
            previous_state = _load_json(self.previous_file)
            if previous_state:
                previous_path = pathlib.Path(previous_state.get("path", ""))
                if previous_path.exists():
                    protected.append(previous_path)
            self._cleanup_old_snapshots(protected)

            service_result = {"action": "none", "returncode": 0}
            if self.service_action in {"restart", "reload"}:
                run_result = _run_service_action(self.service_action)
                service_result = {
                    "action": self.service_action,
                    "returncode": run_result.returncode,
                    "stdout": run_result.stdout.strip(),
                    "stderr": run_result.stderr.strip(),
                }
                if run_result.returncode != 0:
                    raise RuntimeError(f"Failed to {self.service_action} subway-sign after promotion")

            LOG.info("GTFS static refresh promoted dataset %s", dataset_id)
            return {
                "ok": True,
                "promoted": True,
                "dataset_id": dataset_id,
                "downloads": downloaded,
                "service": service_result,
            }
        except Exception as exc:
            self._notify_failure(f"GTFS static refresh failed: {exc}")
            return {"ok": False, "error": str(exc), "downloads": downloaded}
        finally:
            shutil.rmtree(working_dir, ignore_errors=True)

    def rollback(self) -> Dict:
        current = _load_json(self.current_file)
        previous = _load_json(self.previous_file)
        if not current or not previous:
            return {"ok": False, "error": "Rollback requires both current and previous snapshots"}

        _save_json_atomic(self.current_file, previous)
        _save_json_atomic(self.previous_file, current)

        service_result = {"action": "none", "returncode": 0}
        if self.service_action in {"restart", "reload"}:
            run_result = _run_service_action(self.service_action)
            service_result = {
                "action": self.service_action,
                "returncode": run_result.returncode,
                "stdout": run_result.stdout.strip(),
                "stderr": run_result.stderr.strip(),
            }
            if run_result.returncode != 0:
                return {"ok": False, "error": f"Rollback promoted data but service {self.service_action} failed", "service": service_result}

        LOG.warning("GTFS static rollback restored dataset %s", previous.get("dataset_id"))
        return {"ok": True, "restored_dataset_id": previous.get("dataset_id"), "service": service_result}


def _state_files() -> Dict[str, pathlib.Path]:
    state_dir = _resolve_state_dir()
    return {
        "current": state_dir / CURRENT_STATE_FILE,
        "previous": state_dir / PREVIOUS_STATE_FILE,
    }


def get_active_data_dir() -> pathlib.Path:
    state = _load_json(_state_files()["current"])
    if state:
        candidate = pathlib.Path(state.get("path", ""))
        if candidate.exists():
            return candidate
    raise RuntimeError(
        "No active GTFS static snapshot is available. Run 'python3 python/gtfs_refresh.py --force' before starting the sign."
    )


def get_previous_data_dir_within_transition(now_epoch: Optional[int] = None) -> Optional[pathlib.Path]:
    state_paths = _state_files()
    current = _load_json(state_paths["current"]) or {}
    previous = _load_json(state_paths["previous"]) or {}
    if not current or not previous:
        return None

    transition_end = int(current.get("transition_window_end_epoch", 0))
    now_value = int(now_epoch or time.time())
    if now_value > transition_end:
        return None

    previous_path = pathlib.Path(previous.get("path", ""))
    if previous_path.exists():
        return previous_path
    return None


def get_lookup_data_dirs() -> List[pathlib.Path]:
    dirs = [get_active_data_dir()]
    previous = get_previous_data_dir_within_transition()
    if previous:
        dirs.append(previous)
    return dirs


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh static MTA GTFS datasets.")
    parser.add_argument("--force", action="store_true", help="Run refresh even if disabled in config.")
    parser.add_argument("--dry-run", action="store_true", help="Run download/merge/validate without promotion.")
    parser.add_argument("--rollback", action="store_true", help="Rollback to previous snapshot.")
    parser.add_argument(
        "--skip-service-action",
        action="store_true",
        help="Promote data without restarting or reloading the display service.",
    )
    args = parser.parse_args()

    config = load_runtime_config()
    refresh_cfg = config.get("gtfs_static_refresh", {})
    enabled = bool(refresh_cfg.get("enabled", True))
    if not enabled and not args.force and not args.rollback:
        output = {"ok": True, "skipped": True, "reason": "gtfs_static_refresh disabled"}
        print(json.dumps(output))
        return 0

    refresher = GtfsStaticRefresher.from_config(config=config)
    if args.skip_service_action:
        refresher.service_action = "none"
    result = refresher.rollback() if args.rollback else refresher.refresh(force=args.force, dry_run=args.dry_run)
    print(json.dumps(result))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
