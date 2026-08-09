import copy
import importlib
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

from subway_sign.config import DEFAULT_CONFIG, load_runtime_config, save_canonical_config, validate_config
from subway_sign.console_emulator import ConsoleEmulator, normalize_rows


class StubTrips:
    def __init__(self, results, interval=30, error="Feed unavailable"):
        self.results = iter(results)
        self.last_refresh_interval_sec = interval
        self.last_fetch_error = error

    def fetch_trip_data(self):
        result = next(self.results)
        if isinstance(result, Exception):
            raise result
        return result


class ConsoleEmulatorValidation(unittest.TestCase):
    def setUp(self):
        self.config = copy.deepcopy(DEFAULT_CONFIG)
        self.config["feed"]["mta_stop"] = "Test Station"
        self.config["feed"]["mta_routes"] = "F,G"
        self.config["display"]["mta_directions"] = "N,S"
        self.config["display"]["rotate_trip_delay"] = 4
        self.config["display"]["stale_data_grace_sec"] = 30
        self.config = validate_config(self.config)

    def test_matrix_config_path_selects_alternate_configuration(self):
        alternate = copy.deepcopy(self.config)
        alternate["feed"]["mta_stop"] = "Alternate Station"
        with tempfile.TemporaryDirectory() as temp_dir:
            path = pathlib.Path(temp_dir) / "matrix_config.json"
            save_canonical_config(alternate, path)
            with mock.patch.dict(os.environ, {"MATRIX_CONFIG_PATH": str(path)}):
                self.assertEqual(load_runtime_config()["feed"]["mta_stop"], "Alternate Station")

    def test_import_does_not_load_physical_display_modules(self):
        sys.modules.pop("subway_sign.console_emulator", None)
        importlib.import_module("subway_sign.console_emulator")
        self.assertNotIn("rgbmatrix", sys.modules)

    def test_normalization_and_third_row_rotation(self):
        self.assertEqual(len(normalize_rows([])), 3)
        rows = [
            {"line": "A", "direction": "One", "minutes_until_arrival": 1},
            {"line": "B", "direction": "Two", "minutes_until_arrival": 2},
            {"line": "C", "direction": "Three", "minutes_until_arrival": 3},
            {"line": "D", "direction": "Four", "minutes_until_arrival": 4},
        ]
        clock = lambda: 0
        emulator = ConsoleEmulator(self.config, StubTrips([rows]), clock=clock, wall_clock=lambda: 1000)
        emulator.fetch_if_due(0)
        self.assertEqual(emulator.selected_rows(0)[2]["line"], "C")
        self.assertEqual(emulator.selected_rows(4)[2]["line"], "D")
        self.assertEqual(emulator.selected_rows(8)[2]["line"], "C")

    def test_scheduling_failure_retention_stale_transition_and_diagnostics(self):
        rows = [{"line": "F", "direction": "Downtown", "minutes_until_arrival": 5}]
        trips = StubTrips([rows, None], interval=17, error="Network down")
        emulator = ConsoleEmulator(self.config, trips, clock=lambda: 0, wall_clock=lambda: 1000)
        self.assertTrue(emulator.fetch_if_due(0))
        self.assertEqual(emulator.next_fetch_at, 17)
        self.assertFalse(emulator.fetch_if_due(17))
        self.assertEqual(emulator.render_rows(17)[0]["line"], "F")
        self.assertIn("Fetch error: Network down", emulator.render_frame(17))
        self.assertEqual(emulator.freshness(31), "STALE")
        self.assertEqual(emulator.render_rows(31)[0]["line"], "--")


if __name__ == "__main__":
    unittest.main()
