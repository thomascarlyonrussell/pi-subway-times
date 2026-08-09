import pathlib
import sys
import tempfile
import unittest
from unittest import mock


PYTHON_DIR = pathlib.Path(__file__).resolve().parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

import gtfs_bootstrap  # noqa: E402


class BootstrapConditionValidation(unittest.TestCase):
    def test_missing_snapshot_requires_bootstrap(self):
        with mock.patch("gtfs_bootstrap.get_active_data_dir", side_effect=RuntimeError("missing")):
            self.assertFalse(gtfs_bootstrap.has_valid_snapshot())

    def test_legacy_snapshot_requires_bootstrap(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = pathlib.Path(temp_dir)
            for file_name in ("routes.txt", "stops.txt", "trips.txt"):
                (snapshot_dir / file_name).write_text("data", encoding="utf-8")
            with mock.patch("gtfs_bootstrap.get_active_data_dir", return_value=snapshot_dir):
                self.assertFalse(gtfs_bootstrap.has_valid_snapshot())

    def test_catalog_snapshot_skips_bootstrap(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = pathlib.Path(temp_dir)
            for file_name in ("routes.txt", "stops.txt", "trips.txt", "discovery_catalog.json", "trip_resolution_index.json"):
                (snapshot_dir / file_name).write_text("data", encoding="utf-8")
            with mock.patch("gtfs_bootstrap.get_active_data_dir", return_value=snapshot_dir):
                self.assertTrue(gtfs_bootstrap.has_valid_snapshot())


if __name__ == "__main__":
    unittest.main()