import csv
import pathlib
import time
from collections import defaultdict
from datetime import datetime

import requests
from google.transit import gtfs_realtime_pb2

from config import load_runtime_config
from gtfs_refresh import get_active_data_dir, get_lookup_data_dirs


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


def _to_csv_tokens(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [token.strip().upper() for token in value.split(",") if token.strip()]
    return [str(token).strip().upper() for token in value if str(token).strip()]


def _parse_directions(value):
    tokens = _to_csv_tokens(value)
    directions = []
    for token in tokens:
        for char in token:
            if char in {"N", "S", "E", "W"} and char not in directions:
                directions.append(char)
    return directions


def _stop_direction(stop_id):
    if not stop_id:
        return ""
    direction = stop_id[-1].upper()
    if direction in {"N", "S", "E", "W"}:
        return direction
    return ""


def _read_csv(path):
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _load_discovery_catalog():
    active_dir = get_active_data_dir(DATA_DIR)
    routes_rows = _read_csv(active_dir / "routes.txt")
    stops_rows = _read_csv(active_dir / "stops.txt")
    trips_rows = _read_csv(active_dir / "trips.txt")
    stop_times_rows = _read_csv(active_dir / "stop_times.txt")

    trip_to_route = {}
    for row in trips_rows:
        trip_id = row.get("trip_id", "").strip()
        route_id = row.get("route_id", "").strip().upper()
        if trip_id and route_id:
            trip_to_route[trip_id] = route_id

    stop_to_routes = defaultdict(set)
    for row in stop_times_rows:
        trip_id = row.get("trip_id", "").strip()
        stop_id = row.get("stop_id", "").strip()
        route_id = trip_to_route.get(trip_id)
        if stop_id and route_id:
            stop_to_routes[stop_id].add(route_id)

    route_options = []
    known_routes = set()
    for row in routes_rows:
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

    stop_options = {}
    for row in stops_rows:
        stop_id = row.get("stop_id", "").strip()
        stop_name = row.get("stop_name", "").strip()
        if not stop_id or not stop_name:
            continue

        direction = _stop_direction(stop_id)
        route_ids = sorted(route for route in stop_to_routes.get(stop_id, set()) if route in known_routes)
        if not route_ids:
            continue

        key = stop_name.lower()
        if key not in stop_options:
            stop_options[key] = {
                "stop_name": stop_name,
                "stop_ids": set(),
                "route_ids": set(),
                "directions": set(),
            }
        stop_options[key]["stop_ids"].add(stop_id)
        stop_options[key]["route_ids"].update(route_ids)
        if direction:
            stop_options[key]["directions"].add(direction)

    normalized_stops = []
    for stop in stop_options.values():
        normalized_stops.append(
            {
                "stop_name": stop["stop_name"],
                "stop_ids": sorted(stop["stop_ids"]),
                "route_ids": sorted(stop["route_ids"]),
                "directions": sorted(stop["directions"]),
            }
        )
    normalized_stops.sort(key=lambda item: item["stop_name"])

    generated_at_epoch = int(max((path.stat().st_mtime for path in active_dir.glob("*.txt")), default=0))
    return {
        "generated_at_epoch": generated_at_epoch,
        "routes": route_options,
        "stops": normalized_stops,
    }


def get_discoverable_routes():
    return _load_discovery_catalog()["routes"]


def get_discoverable_stops(routes=None, directions=None):
    selected_routes = set(_to_csv_tokens(routes))
    selected_directions = set(_parse_directions(directions))

    matched = []
    for stop in _load_discovery_catalog()["stops"]:
        stop_routes = set(stop["route_ids"])
        stop_directions = set(stop["directions"])

        if selected_routes and not stop_routes.intersection(selected_routes):
            continue
        if selected_directions and not stop_directions.intersection(selected_directions):
            continue
        matched.append(stop)

    return matched


def get_discovery_metadata():
    catalog = _load_discovery_catalog()
    return {
        "generated_at_epoch": catalog["generated_at_epoch"],
        "routes": catalog["routes"],
    }


def validate_route_stop_selection(routes, stop_name, directions):
    route_tokens = _to_csv_tokens(routes)
    if not route_tokens:
        raise ValueError("At least one route must be selected")
    if not stop_name or not stop_name.strip():
        raise ValueError("A stop must be selected")

    stop_name_normalized = stop_name.strip().lower()
    matching_stops = get_discoverable_stops(route_tokens, directions)
    if not any(stop["stop_name"].lower() == stop_name_normalized for stop in matching_stops):
        direction_tokens = _parse_directions(directions)
        direction_hint = f" and direction(s) {','.join(direction_tokens)}" if direction_tokens else ""
        raise ValueError(
            f"Stop '{stop_name.strip()}' is not compatible with route(s) {','.join(route_tokens)}{direction_hint}"
        )

    return True


class Trips:
    def __init__(self, station, directions, routes, config=None):
        self.cwd = REPO_ROOT
        self.config = config or load_runtime_config()
        self.MTA_FEED_BASE_URL = self.config["feed"]["mta_feed_base_url"]
        self.MTA_FEEDS = {
            'gtfs-bdfm':['B','D','F','FS','FX','M'], 
            'gtfs-g':['G','GS'],
            'gtfs':['1','2','3','4','5','5X','6','6X','7','7X'],
            'gtfs-ace':['A','C','E'],
            'gtfs-jz':['J','Z'],
            'gtfs-l':['L'],
            'gtfs-nqrw':['N','Q','R','W'],
            'gtfs-si':['SI'],
        }
        self.station = station
        self.directions = directions
        self.routes = routes

    def _lookup_dirs(self):
        return get_lookup_data_dirs(DATA_DIR)

    def get_stops(self):
        stops = []
        seen = set()
        for lookup_dir in self._lookup_dirs():
            with open(lookup_dir / "stops.txt", "r", newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    stop_id = row.get("stop_id", "").strip()
                    stop_name = row.get("stop_name", "").strip()
                    if stop_name == self.station:
                        direction = _stop_direction(stop_id)
                        if self.directions is None or direction in self.directions:
                            if stop_id not in seen:
                                stops.append(stop_id)
                                seen.add(stop_id)
        return stops

    def get_trip_directions(self):
        trip_directions = {}
        lookup_dirs = self._lookup_dirs()
        for lookup_dir in reversed(lookup_dirs):
            with open(lookup_dir / "trips.txt", "r", newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    route_id = row.get("route_id", "").strip()
                    if not self.routes or route_id in self.routes:
                        trip_id = row.get("trip_id", "").strip()
                        trip_headsign = row.get("trip_headsign", "").strip()
                        trip_directions[trip_id.split(".")[-1]] = trip_headsign
        return trip_directions

    def get_route_colors(self):
        route_colors = {}
        lookup_dirs = self._lookup_dirs()
        for lookup_dir in reversed(lookup_dirs):
            with open(lookup_dir / "routes.txt", "r", encoding="utf-8", newline="") as file:
                reader = csv.reader(file)
                next(reader)  # Skip header
                for row in reader:
                    if not self.routes or row[1] in self.routes:
                        route_colors[row[1]] = row[7]  # route_id and route_color
                    else:
                        continue
        return route_colors

    def get_mta_data(self, stations, trip_directions):
        trips = []
        urls = set([f"{self.MTA_FEED_BASE_URL}{feed}" for feed,lines in self.MTA_FEEDS.items() if any([route in lines for route in self.routes])])
        
        for url in urls:
            current_time = datetime.now().timestamp()
            response = requests.get(url)
            if response.status_code == 200:
                feed = gtfs_realtime_pb2.FeedMessage()
                feed.ParseFromString(response.content)
                for entity in feed.entity:
                    # grab trip updates
                    if entity.HasField('trip_update'):
                        entity_trip = entity.trip_update
                        # check if trip has one of our stations
                        for t in entity_trip.stop_time_update:
                            if entity_trip.trip.route_id in self.routes and t.stop_id in stations:
                                arrival_time = datetime.fromtimestamp(t.arrival.time)
                                trip = {}
                                trip['line'] = entity_trip.trip.route_id
                                trip['arrival_time'] = arrival_time.strftime('%H:%M')
                                trip['minutes_until_arrival'] = int((arrival_time.timestamp() - current_time) // 60)
                                trip['direction'] = trip_directions.get(entity_trip.trip.trip_id.split('.')[-1], 'Unknown')
                                trips.append(trip)
            else:
                print(f"Failed to retrieve data from {url}: {response.status_code}")

        return trips

    def get_subway_times(self, stations, trip_directions, route_colors, max_list=5, min_arrival=0, max_arrival=99):
        trips = self.get_mta_data(stations, trip_directions)

        # Filter out trips that are too close to arrival
        trips = [trip for trip in trips if (trip['minutes_until_arrival'] >= min_arrival) & (trip['minutes_until_arrival'] <= max_arrival)]

        # Sort trips by arrival time and get the specified number of trips
        sorted_trips = sorted(trips, key=lambda x: x['minutes_until_arrival'])[:max_list]

        # Add route color to each trip
        for trip in sorted_trips:
            trip['route_color'] = route_colors.get(trip['line'], 'FFFFFF')

        return sorted_trips

    def fetch_trip_data(self, retries=3):
        attempt = 0
        while attempt < retries:
            try:
                trips = self.get_subway_times(
                            self.get_stops(), self.get_trip_directions(), self.get_route_colors(),
                            max_list=5, 
                            min_arrival=int(self.config["display"]["minimum_arrival_minutes"]),
                            max_arrival=int(self.config["display"]["maximum_arrival_minutes"])
                            )
                if not trips:
                    raise ValueError("No trips found")
                return trips
            except Exception as e:
                print(f"Error fetching trip data (attempt {attempt + 1}): {e}")
                attempt += 1
                time.sleep(int(self.config["display"]["refresh_time_delay"]))  # Wait before retrying

        return None
