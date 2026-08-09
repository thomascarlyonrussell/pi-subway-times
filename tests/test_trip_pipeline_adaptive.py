import copy
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

from subway_sign.config import DEFAULT_CONFIG, validate_config
from subway_sign.trips import Trips


class TripPipelineAdaptiveValidation(unittest.TestCase):
    def _build_config(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["feed"]["mta_routes"] = "A,F,G,L,N,SI"
        cfg["display"]["adaptive_refresh_enabled"] = True
        cfg["display"]["adaptive_refresh_min_sec"] = 15
        cfg["display"]["adaptive_refresh_max_sec"] = 60
        cfg["display"]["adaptive_refresh_imminent_threshold_min"] = 5
        cfg["display"]["adaptive_refresh_far_threshold_min"] = 20
        cfg["display"]["realtime_feed_cadence_sec"] = 30
        cfg["display"]["direction_mapping_rules"] = [
            {
                "match": {"route_id": "F", "stop_id": "D14N", "direction": "CONEY ISLAND-STILLWELL AV"},
                "label": "Downtown",
                "priority": 10,
            }
        ]
        return validate_config(cfg)

    def test_direction_mapping_priority_and_fallback(self):
        cfg = self._build_config()
        trips = Trips("7 Av", ["N"], ["F"], config=cfg)

        mapped = trips._apply_direction_mapping("F", "D14N", "Coney Island-Stillwell Av")  # pylint: disable=protected-access
        self.assertEqual(mapped, "Downtown")

        fallback = trips._apply_direction_mapping("F", "D14S", "Uptown")  # pylint: disable=protected-access
        self.assertEqual(fallback, "Uptown")

    def test_direction_resolution_handles_realtime_schedule_transition_ids(self):
        cfg = self._build_config()
        trips = Trips("7 Av", ["N"], ["F"], config=cfg)
        static_directions = {
            "N07R": "Jamaica-179 St",
            "N20R": "Jamaica-179 St",
            "S07R": "Coney Island-Stillwell Av",
        }

        exact = trips._resolve_trip_direction("ASP26GEN..N07R", static_directions)  # pylint: disable=protected-access
        transition = trips._resolve_trip_direction("111450_F..N", static_directions)  # pylint: disable=protected-access
        ambiguous = trips._resolve_trip_direction(  # pylint: disable=protected-access
            "111450_F..N", {"N07R": "Jamaica-179 St", "N20R": "Forest Hills-71 Av"}
        )
        unavailable = trips._resolve_trip_direction("unmapped-trip", static_directions)  # pylint: disable=protected-access

        self.assertEqual(exact, "Jamaica-179 St")
        self.assertEqual(transition, "Jamaica-179 St")
        self.assertEqual(ambiguous, "North")
        self.assertEqual(unavailable, "Direction unavailable")

    def test_direction_resolution_uses_compact_cardinal_fallbacks(self):
        cfg = self._build_config()
        trips = Trips("7 Av", ["N"], ["F"], config=cfg)

        for token, expected_direction in {
            "N": "North",
            "S": "South",
            "E": "East",
            "W": "West",
        }.items():
            with self.subTest(token=token):
                self.assertEqual(
                    trips._resolve_trip_direction(f"112650_F..{token}", {}),  # pylint: disable=protected-access
                    expected_direction,
                )

    def test_direction_resolution_scopes_transition_suffixes_to_the_route(self):
        cfg = self._build_config()
        trips = Trips("7 Av", ["N"], ["F", "G"], config=cfg)
        static_directions = {
            ("F", "N07R"): "Jamaica-179 St",
            ("G", "N09X002"): "Bedford-Nostrand Avs",
        }

        resolved = trips._resolve_trip_direction(  # pylint: disable=protected-access
            "112650_F..N",
            static_directions,
            "F",
        )

        self.assertEqual(resolved, "Jamaica-179 St")

    def test_direction_resolution_uses_trip_resolution_index(self):
        cfg = self._build_config()
        trips = Trips("7 Av", ["N"], ["G"], config=cfg)
        trips.resolution_trips = {
            "081400_G..N": {
                "route_id": "G",
                "service_id": "WKD",
                "trip_id": "081400_G..N",
                "trip_headsign": "Court Sq",
                "start_time": "08:14:00",
                "stop_ids": ["F20N", "G26N", "G22N"],
            },
            "082200_G..N": {
                "route_id": "G",
                "service_id": "WKD",
                "trip_id": "082200_G..N",
                "trip_headsign": "Bedford-Nostrand Avs",
                "start_time": "08:22:00",
                "stop_ids": ["F20N", "G26N"],
            },
        }
        trips.resolution_route_start_map = {
            ("G", "08:14:00"): [trips.resolution_trips["081400_G..N"]],
            ("G", "08:22:00"): [trips.resolution_trips["082200_G..N"]],
        }

        exact_headsign = trips._resolve_trip_direction("081400_G..N", {})  # pylint: disable=protected-access
        self.assertEqual(exact_headsign, "Court Sq")

        matched_court_sq = trips._resolve_trip_direction(  # pylint: disable=protected-access
            "111450_G..N",
            {},
            route_id="G",
            start_time="08:14:00",
            stop_id="G26N",
        )
        self.assertEqual(matched_court_sq, "Court Sq")

        matched_bedford = trips._resolve_trip_direction(  # pylint: disable=protected-access
            "112250_G..N",
            {},
            route_id="G",
            start_time="082200",
            stop_id="G26N",
        )
        self.assertEqual(matched_bedford, "Bedford-Nostrand Avs")

    def test_direction_resolution_does_not_match_opposite_directional_platform(self):
        cfg = self._build_config()
        trips = Trips("7 Av", ["N"], ["G"], config=cfg)
        trips.resolution_trips = {}
        trips.resolution_route_start_map = {
            ("G", "17:36:30"): [
                {
                    "trip_headsign": "Church Ave",
                    "stop_ids": ["F24S"],
                }
            ]
        }

        resolved = trips._resolve_trip_direction(  # pylint: disable=protected-access
            "105650_G..N",
            {},
            route_id="G",
            start_time="17:36:30",
            stop_id="F24N",
        )

        self.assertEqual(resolved, "North")

    def test_feed_group_resolution_covers_all_selected_route_families(self):
        cfg = self._build_config()
        routes = ["1", "A", "F", "G", "J", "L", "N", "SI"]
        trips = Trips("7 Av", ["N"], routes, config=cfg)
        feed_groups = set(trips.resolve_feed_groups())

        self.assertEqual(
            feed_groups,
            {"gtfs", "gtfs-ace", "gtfs-bdfm", "gtfs-g", "gtfs-jz", "gtfs-l", "gtfs-nqrw", "gtfs-si"},
        )

    def test_route_colors_use_standard_gtfs_column_names(self):
        cfg = self._build_config()
        trips = Trips("7 Av", ["N"], ["F"], config=cfg)
        with tempfile.TemporaryDirectory() as temp_dir:
            routes_path = pathlib.Path(temp_dir) / "routes.txt"
            routes_path.write_text(
                "route_id,agency_id,route_short_name,route_long_name,route_desc,route_type,route_url,route_color,route_text_color\n"
                "F,MTABC,F,Queens Boulevard Local,,1,,FF6319,FFFFFF\n",
                encoding="utf-8",
            )
            with mock.patch.object(trips, "_lookup_dirs", return_value=[pathlib.Path(temp_dir)]):
                self.assertEqual(trips.get_route_colors(), {"F": "FF6319"})

    def test_adaptive_cadence_transitions(self):
        cfg = self._build_config()
        trips = Trips("7 Av", ["N"], ["F"], config=cfg)

        self.assertEqual(trips.calculate_next_refresh_interval(2), 15)
        self.assertEqual(trips.calculate_next_refresh_interval(30), 60)
        self.assertGreaterEqual(trips.calculate_next_refresh_interval(10), 15)
        self.assertLessEqual(trips.calculate_next_refresh_interval(10), 60)

    def test_fetch_updates_last_interval_from_nearest_arrival(self):
        cfg = self._build_config()
        trips = Trips("7 Av", ["N"], ["F"], config=cfg)

        mocked_rows = [
            {"line": "F", "minutes_until_arrival": 3, "route_color": "FFFFFF", "direction": "Downtown"},
            {"line": "F", "minutes_until_arrival": 12, "route_color": "FFFFFF", "direction": "Downtown"},
        ]
        with mock.patch.object(trips, "get_subway_times", return_value=mocked_rows):
            result = trips.fetch_trip_data(retries=1)
        self.assertEqual(result, mocked_rows)
        self.assertEqual(trips.last_refresh_interval_sec, 15)


if __name__ == "__main__":
    unittest.main()
