import requests
from google.transit import gtfs_realtime_pb2
from datetime import datetime
import csv
import pathlib
import toml

#get current file path
cwd = pathlib.Path(__file__).parent.parent

# Load the TOML file
with open(cwd / 'settings.toml', 'r') as file:
    config = toml.load(file)

MTA_FEED_BASE_URL = config["MTA_FEED_BASE_URL"]
MTA_FEEDS = {
    'gtfs-bdfm':['B','D','F','FS','FX','M'], 
    'gtfs-g':['G','GS'],
    'gtfs':['1','2','3','4','5','5X','6','6X','7','7X'],
    'gtfs-ace':['A','C','E'],
    'gtfs-jz':['J','Z'],
    'gtfs-l':['L'],
    'gtfs-nqrw':['N','Q','R','W'],
    'gtfs-si':['SI'],
    }



def get_stops(station, directions=None):
    stops = []
    with open(cwd / 'data' / 'stops.txt', 'r') as file:
        for line in file:
            row = line.strip().split(',')
            if row[1] == station:
                if directions is None or row[0][-1] in directions:
                    stops.append(row[0])
    return stops

def get_trip_directions():
    trip_directions = {}
    with open(cwd / 'data' / 'trips.txt', 'r') as file:
        for line in file:
            row = line.strip().split(',')
            trip_directions[row[1].split('.')[-1]] = row[3]
    return trip_directions

def get_route_colors():
    route_colors = {}
    with open(cwd / 'data' / 'routes.txt', 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for row in reader:
            route_colors[row[1]] = row[7]  # route_id and route_color
    return route_colors

def get_mta_data(routes, stations, trip_directions):
    trips = []
    urls = set([f"{MTA_FEED_BASE_URL}{feed}" for feed,lines in MTA_FEEDS.items() if any([route in lines for route in routes])])
    
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
                        if entity_trip.trip.route_id in routes and t.stop_id in stations:
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
