import requests
from google.transit import gtfs_realtime_pb2
from datetime import datetime
import csv
import pathlib
import toml
import time

class Trips:
    def __init__(self, station, directions, routes):
        self.cwd = pathlib.Path(__file__).parent.parent
        with open(self.cwd / 'settings.toml', 'r') as file:
            config = toml.load(file)
        self.MTA_FEED_BASE_URL = config["MTA_FEED_BASE_URL"]
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
        self.config = config

    def get_stops(self):
        stops = []
        with open(self.cwd / 'data' / 'stops.txt', 'r') as file:
            for line in file:
                row = line.strip().split(',')
                if row[1] == self.station:
                    if self.directions is None or row[0][-1] in self.directions:
                        stops.append(row[0])
        return stops

    def get_trip_directions(self):
        trip_directions = {}
        with open(self.cwd / 'data' / 'trips.txt', 'r') as file:
            for line in file:
                row = line.strip().split(',')
                if not self.routes or row[0] in self.routes:
                    trip_directions[row[1].split('.')[-1]] = row[3]
                else: continue
        return trip_directions

    def get_route_colors(self):
        route_colors = {}
        with open(self.cwd / 'data' / 'routes.txt', 'r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header
            for row in reader:
                if not self.routes or row[1] in self.routes:
                    route_colors[row[1]] = row[7]  # route_id and route_color
                else: continue
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

    def get_subway_times(self, stations, trip_directions, route_colors, max_list=5, min_arrival=0):
        trips = self.get_mta_data(stations, trip_directions)

        # Filter out trips that are too close to arrival
        trips = [trip for trip in trips if trip['minutes_until_arrival'] >= min_arrival]

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
                            max_list=5, min_arrival=int(self.config["MINIMUM_ARRIVAL_MINUTES"])
                            )
                if not trips:
                    raise ValueError("No trips found")
                return trips
            except Exception as e:
                print(f"Error fetching trip data (attempt {attempt + 1}): {e}")
                attempt += 1
                time.sleep(int(self.config["REFRESH_TIME_DELAY"]))  # Wait before retrying

        return None