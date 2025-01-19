import requests
from google.transit import gtfs_realtime_pb2
from datetime import datetime
from config import MTA_FEED_BASE_URL, MTA_FEEDS
import csv

def get_station_stops(stations, directions=None):
    stops = []
    with open('data/stops.txt', 'r') as file:
        for line in file:
            row = line.strip().split(',')
            if row[1] in stations:
                if directions is None or row[0][-1] in directions:
                    stops.append(row[0])
    return stops

def get_trip_directions():
    trip_directions = {}
    with open('data/trips.txt', 'r') as file:
        for line in file:
            row = line.strip().split(',')
            trip_directions[row[1].split('.')[-1]] = row[3]
    return trip_directions

def get_route_colors():
    route_colors = {}
    with open('data/routes.txt', 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for row in reader:
            route_colors[row[1]] = row[7]  # route_id and route_color
    return route_colors

def get_mta_data(stations, trip_directions):
    trips = []
    urls = [f"{MTA_FEED_BASE_URL}{feed}" for feed in MTA_FEEDS]
    
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
                        if entity_trip.trip.route_id in ['F', 'G'] and t.stop_id in stations:
                            arrival_time = datetime.fromtimestamp(t.arrival.time)
                            trip = {}
                            trip['line'] = entity_trip.trip.route_id
                            trip['arrival_time'] = arrival_time.strftime('%H:%M')
                            trip['minutes_until_arrival'] = round((arrival_time.timestamp() - current_time) / 60)
                            trip['direction'] = trip_directions.get(entity_trip.trip.trip_id.split('.')[-1], 'Unknown')
                            trips.append(trip)
        else:
            print(f"Failed to retrieve data from {url}: {response.status_code}")
    
    return trips
