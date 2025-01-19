from flask import Flask, jsonify, request
from data_processing import get_station_stops, get_trip_directions, get_mta_data, get_route_colors
from config import STATIONS, DIRECTIONS
from waitress import serve

app = Flask(__name__)

# Load data once at startup
stations = get_station_stops(STATIONS, DIRECTIONS)
trip_directions = get_trip_directions()
route_colors = get_route_colors()

@app.route('/subway-times', methods=['GET'])
def get_subway_times():
    count = request.args.get('count', default=5, type=int)
    trips = get_mta_data(stations, trip_directions)

    # Sort trips by arrival time and get the specified number of trips
    sorted_trips = sorted(trips, key=lambda x: x['arrival_time'])[:count]

    # Add route color to each trip
    for trip in sorted_trips:
        trip['route_color'] = route_colors.get(trip['line'], 'Unknown')

    return jsonify(sorted_trips)

if __name__ == "__main__":
    serve(app, host='0.0.0.0', port=5000)
