import argparse
import json
import time

from bootstrap_status import BootstrapStatusRenderer
from config import load_runtime_config
from gtfs_refresh import GtfsStaticRefresher, get_active_data_dir


FAILURE_DISPLAY_SECONDS = 20


def has_valid_snapshot() -> bool:
    try:
        snapshot_dir = get_active_data_dir()
    except RuntimeError:
        return False
    return all((snapshot_dir / file_name).exists() for file_name in ("routes.txt", "stops.txt", "trips.txt", "discovery_catalog.json"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Visually bootstrap GTFS data when no active snapshot exists.")
    parser.add_argument("--force", action="store_true", help="Refresh even when an active snapshot exists.")
    args = parser.parse_args()

    if not args.force and has_valid_snapshot():
        print(json.dumps({"ok": True, "skipped": True, "reason": "active GTFS snapshot exists"}))
        return 0

    config = load_runtime_config()
    renderer = BootstrapStatusRenderer(config["display"])
    refresher = GtfsStaticRefresher.from_config(config=config)
    refresher.service_action = "none"
    refresher.status_renderer = renderer
    try:
        result = refresher.refresh(force=True)
        if not result.get("ok"):
            time.sleep(FAILURE_DISPLAY_SECONDS)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    finally:
        renderer.close()


if __name__ == "__main__":
    raise SystemExit(main())