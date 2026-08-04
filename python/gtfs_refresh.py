import argparse
import csv
import hashlib
import io
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
DISCOVERY_CATALOG_FILE = "discovery_catalog.json"
DOWNLOAD_PROGRESS_BYTES = 1024 * 1024
MERGE_PROGRESS_ROWS = 100000
SQLITE_BATCH_SIZE = 10000

BASE_ARCHIVE_NAME = "google_transit.zip"
SUPPLEMENT_ARCHIVE_NAME = "google_transit_supplemented.zip"

REQUIRED_FILES = {
    "agency.txt",
    "routes.txt",
    "trips.txt",
    "stops.txt",
}
EXCLUDED_SNAPSHOT_FILES = {"shapes.txt", "stop_times.txt"}

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
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(console_handler)
    logger.propagate = False
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


def _format_bytes(byte_count: int) -> str:
    if byte_count < 1024 * 1024:
        return f"{byte_count / 1024:.1f} KiB"
    return f"{byte_count / (1024 * 1024):.1f} MiB"


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


def _iter_archive_csv_rows(archive_path: pathlib.Path, file_name: str):
    with zipfile.ZipFile(archive_path, "r") as archive:
        with archive.open(file_name, "r") as binary_handle:
            text_handle = io.TextIOWrapper(binary_handle, encoding="utf-8", newline="")
            yield from csv.DictReader(text_handle)


def _merge_csv(base_file: pathlib.Path, supplement_file: pathlib.Path, output_file: pathlib.Path, key_fields: Sequence[str]) -> None:
    started_at = time.monotonic()
    with base_file.open("r", encoding="utf-8", newline="") as base_handle, supplement_file.open(
        "r", encoding="utf-8", newline=""
    ) as supplement_handle:
        base_reader = csv.DictReader(base_handle)
        supplement_reader = csv.DictReader(supplement_handle)
        base_headers = list(base_reader.fieldnames or [])
        supplement_headers = list(supplement_reader.fieldnames or [])
        headers = list(dict.fromkeys(base_headers + supplement_headers))
        matching_headers = base_headers == supplement_headers

    output_file.parent.mkdir(parents=True, exist_ok=True)
    descriptor, database_name = tempfile.mkstemp(prefix="gtfs-merge-", suffix=".sqlite3", dir=str(output_file.parent))
    os.close(descriptor)
    database_path = pathlib.Path(database_name)
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute("PRAGMA cache_size=-8192")
        connection.execute("CREATE TABLE seen_keys (key TEXT PRIMARY KEY) WITHOUT ROWID")

        LOG.info("Indexing supplemented rows for %s", output_file.name)
        supplement_rows = 0
        key_batch = []
        with supplement_file.open("r", encoding="utf-8", newline="") as supplement_handle:
            supplement_reader = csv.DictReader(supplement_handle)
            for row in supplement_reader:
                key_batch.append((_stable_row_key(row, key_fields),))
                supplement_rows += 1
                if len(key_batch) >= SQLITE_BATCH_SIZE:
                    connection.executemany("INSERT OR IGNORE INTO seen_keys VALUES (?)", key_batch)
                    key_batch.clear()
                if supplement_rows % MERGE_PROGRESS_ROWS == 0:
                    LOG.info("Indexed %s supplemented rows for %s", f"{supplement_rows:,}", output_file.name)
        if key_batch:
            connection.executemany("INSERT OR IGNORE INTO seen_keys VALUES (?)", key_batch)
        connection.commit()

        if matching_headers:
            LOG.info("Copying supplemented rows for %s", output_file.name)
            shutil.copy2(supplement_file, output_file)
        else:
            with output_file.open("w", encoding="utf-8", newline="") as output_handle:
                writer = csv.DictWriter(output_handle, fieldnames=headers)
                writer.writeheader()
                with supplement_file.open("r", encoding="utf-8", newline="") as supplement_handle:
                    supplement_reader = csv.DictReader(supplement_handle)
                    for row in supplement_reader:
                        writer.writerow(row)

        with output_file.open("a", encoding="utf-8", newline="") as output_handle:
            writer = csv.DictWriter(output_handle, fieldnames=headers)

            LOG.info("Writing base-only rows for %s", output_file.name)
            base_rows = 0
            base_only_rows = 0
            with base_file.open("r", encoding="utf-8", newline="") as base_handle:
                base_reader = csv.DictReader(base_handle)
                for row in base_reader:
                    base_rows += 1
                    key = _stable_row_key(row, key_fields)
                    if connection.execute("SELECT 1 FROM seen_keys WHERE key = ?", (key,)).fetchone():
                        pass
                    else:
                        connection.execute("INSERT INTO seen_keys VALUES (?)", (key,))
                        writer.writerow(row)
                        base_only_rows += 1
                    if base_rows % MERGE_PROGRESS_ROWS == 0:
                        LOG.info(
                            "Processed %s base rows for %s (%s retained)",
                            f"{base_rows:,}",
                            output_file.name,
                            f"{base_only_rows:,}",
                        )

        LOG.info(
            "Merged %s: %s supplemented rows and %s base-only rows",
            output_file.name,
            f"{supplement_rows:,}",
            f"{base_only_rows:,}",
        )
        LOG.info("Finished merging %s in %.1f seconds", output_file.name, time.monotonic() - started_at)
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
        status_renderer=None,
    ):
        self.state_dir = state_dir
        self.sources = list(sources)
        self.timeout_sec = timeout_sec
        self.transition_window_hours = transition_window_hours
        self.snapshot_retention_count = snapshot_retention_count
        self.service_action = service_action
        self.alert_command = alert_command
        self.status_renderer = status_renderer

        self.snapshots_dir = self.state_dir / SNAPSHOTS_DIR_NAME
        self.current_file = self.state_dir / CURRENT_STATE_FILE
        self.previous_file = self.state_dir / PREVIOUS_STATE_FILE

    def _status(self, phase: str, completed: int = 0, total: int = 0, detail: str = "") -> None:
        if self.status_renderer is not None:
            try:
                self.status_renderer.update(phase, completed, total, detail)
            except Exception as exc:
                LOG.exception("Bootstrap status renderer disabled: %s", exc)
                self.status_renderer = None

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
            snapshot_retention_count=int(refresh_cfg.get("snapshot_retention_count", 2)),
            service_action=str(refresh_cfg.get("service_action", "restart")).strip().lower(),
            alert_command=str(refresh_cfg.get("alert_command", "")).strip(),
        )

    def _download_source(self, source: GtfsSource, target_dir: pathlib.Path) -> Dict[str, str]:
        download_started_at = time.monotonic()
        LOG.info("Downloading GTFS archive '%s' from %s", source.name, source.url)
        zip_path = target_dir / f"{source.name}.zip"
        downloaded_bytes = 0
        last_reported_bytes = 0
        with requests.get(source.url, timeout=self.timeout_sec, stream=True) as response:
            response.raise_for_status()
            content_length = int(response.headers.get("content-length", 0))
            self._status("download", 0, content_length, source.name)
            with zip_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    downloaded_bytes += len(chunk)
                    self._status("download", downloaded_bytes, content_length, source.name)
                    if downloaded_bytes - last_reported_bytes >= DOWNLOAD_PROGRESS_BYTES:
                        if content_length:
                            LOG.info(
                                "Downloaded %s / %s for %s",
                                _format_bytes(downloaded_bytes),
                                _format_bytes(content_length),
                                source.name,
                            )
                        else:
                            LOG.info("Downloaded %s for %s", _format_bytes(downloaded_bytes), source.name)
                        last_reported_bytes = downloaded_bytes
        if zip_path.stat().st_size == 0:
            raise RuntimeError(f"Downloaded empty archive: {source.url}")
        LOG.info(
            "Finished downloading %s (%s) in %.1f seconds",
            source.name,
            _format_bytes(downloaded_bytes),
            time.monotonic() - download_started_at,
        )

        checksum = _sha256_file(zip_path)
        extract_dir = target_dir / source.name
        extract_dir.mkdir(parents=True, exist_ok=True)
        extraction_started_at = time.monotonic()
        LOG.info("Extracting GTFS archive %s", source.name)
        self._status("unpack", 0, 0, source.name)
        with zipfile.ZipFile(zip_path, "r") as archive:
            members = [
                entry
                for entry in archive.infolist()
                if pathlib.PurePosixPath(entry.filename).name not in EXCLUDED_SNAPSHOT_FILES
            ]
            archive.extractall(extract_dir, members)
        LOG.info("Finished extracting GTFS archive %s in %.1f seconds", source.name, time.monotonic() - extraction_started_at)

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

        catalog = _load_json(dataset_dir / DISCOVERY_CATALOG_FILE)
        if not catalog or not isinstance(catalog.get("routes"), list) or not isinstance(catalog.get("stops"), list):
            raise RuntimeError("GTFS discovery catalog is missing or invalid")

    def _build_discovery_catalog(
        self,
        base_archive: pathlib.Path,
        supplement_archive: pathlib.Path,
        snapshot_dir: pathlib.Path,
    ) -> None:
        LOG.info("Building compact GTFS discovery catalog")
        self._status("stations", 0, 0, "routes")
        trip_to_route: Dict[str, str] = {}
        for archive_path in (base_archive, supplement_archive):
            for row in _iter_archive_csv_rows(archive_path, "trips.txt"):
                trip_id = row.get("trip_id", "").strip()
                route_id = row.get("route_id", "").strip().upper()
                if trip_id and route_id:
                    trip_to_route[trip_id] = route_id

        route_options = []
        known_routes = set()
        with (snapshot_dir / "routes.txt").open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                route_id = row.get("route_id", "").strip().upper()
                if not route_id:
                    continue
                known_routes.add(route_id)
                route_options.append(
                    {
                        "route_id": route_id,
                        "route_short_name": row.get("route_short_name", "").strip(),
                        "route_long_name": row.get("route_long_name", "").strip(),
                        "route_color": row.get("route_color", "").strip().upper() or "FFFFFF",
                    }
                )
        route_options.sort(key=lambda item: item["route_id"])

        stop_to_routes: Dict[str, set] = {}
        for archive_path in (supplement_archive, base_archive):
            source_name = archive_path.stem
            LOG.info("Scanning %s stop times for discovery catalog", source_name)
            self._status("stations", 0, 0, source_name)
            row_count = 0
            for row in _iter_archive_csv_rows(archive_path, "stop_times.txt"):
                trip_id = row.get("trip_id", "").strip()
                stop_id = row.get("stop_id", "").strip()
                route_id = trip_to_route.get(trip_id)
                if stop_id and route_id:
                    stop_to_routes.setdefault(stop_id, set()).add(route_id)
                row_count += 1
                if row_count % MERGE_PROGRESS_ROWS == 0:
                    LOG.info("Scanned %s stop times from %s", f"{row_count:,}", source_name)
                    self._status("stations", row_count, 0, f"{source_name[:4]} {row_count // 1000}K")

        stops_by_name: Dict[str, Dict] = {}
        with (snapshot_dir / "stops.txt").open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                stop_id = row.get("stop_id", "").strip()
                stop_name = row.get("stop_name", "").strip()
                route_ids = sorted(route for route in stop_to_routes.get(stop_id, set()) if route in known_routes)
                if not stop_id or not stop_name or not route_ids:
                    continue

                stop_key = stop_name.lower()
                stop = stops_by_name.setdefault(
                    stop_key,
                    {"stop_name": stop_name, "stop_ids": set(), "route_ids": set(), "directions": set()},
                )
                stop["stop_ids"].add(stop_id)
                stop["route_ids"].update(route_ids)
                direction = stop_id[-1].upper()
                if direction in {"N", "S", "E", "W"}:
                    stop["directions"].add(direction)

        stops = [
            {
                "stop_name": stop["stop_name"],
                "stop_ids": sorted(stop["stop_ids"]),
                "route_ids": sorted(stop["route_ids"]),
                "directions": sorted(stop["directions"]),
            }
            for stop in stops_by_name.values()
        ]
        stops.sort(key=lambda item: item["stop_name"])
        _save_json_atomic(
            snapshot_dir / DISCOVERY_CATALOG_FILE,
            {"version": 1, "generated_at_epoch": int(time.time()), "routes": route_options, "stops": stops},
        )
        LOG.info("Built discovery catalog with %s routes and %s stops", len(route_options), len(stops))

    def _merge_archives(self, base_dir: pathlib.Path, supplement_dir: pathlib.Path, output_dir: pathlib.Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        base_files = {path.name: path for path in base_dir.glob("*.txt")}
        supplement_files = {path.name: path for path in supplement_dir.glob("*.txt")}
        all_names = sorted(set(base_files.keys()) | set(supplement_files.keys()))

        for file_name in all_names:
            if file_name in EXCLUDED_SNAPSHOT_FILES:
                continue
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
        refresh_started_at = time.monotonic()
        self._status("setup", 0, 0, "data")
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
            self._build_discovery_catalog(
                pathlib.Path(by_name["base"]["zip_path"]),
                pathlib.Path(by_name["supplemented"]["zip_path"]),
                snapshot_dir,
            )
            LOG.info("Validating candidate snapshot %s", dataset_id)
            self._validate_dataset(snapshot_dir)

            if dry_run:
                shutil.rmtree(snapshot_dir, ignore_errors=True)
                LOG.info("GTFS static refresh dry run completed in %.1f seconds", time.monotonic() - refresh_started_at)
                return {
                    "ok": True,
                    "promoted": False,
                    "dry_run": True,
                    "downloads": downloaded,
                }

            LOG.info("Calculating candidate snapshot checksums for %s", dataset_id)
            self._status("finalize", 0, 0, "checks")
            checksums = {
                path.name: _sha256_file(path)
                for path in snapshot_dir.iterdir()
                if path.is_file() and path.name != "manifest.json"
            }
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

            LOG.info(
                "GTFS static refresh promoted dataset %s in %.1f seconds",
                dataset_id,
                time.monotonic() - refresh_started_at,
            )
            self._status("ready", 1, 1, "")
            return {
                "ok": True,
                "promoted": True,
                "dataset_id": dataset_id,
                "downloads": downloaded,
                "service": service_result,
            }
        except Exception as exc:
            self._status("failed", 0, 0, "terminal")
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
