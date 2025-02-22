from data_processing import get_station_stops, get_trip_directions, get_mta_data, get_route_colors
from config import STATIONS, DIRECTIONS

# Load data once at startup
stations = get_station_stops(STATIONS, DIRECTIONS)
trip_directions = get_trip_directions()
route_colors = get_route_colors()

def get_subway_times(max_list=5):
    trips = get_mta_data(stations, trip_directions)

    # Sort trips by arrival time and get the specified number of trips
    sorted_trips = sorted(trips, key=lambda x: x['minutes_until_arrival'])[:max_list]

    # Add route color to each trip
    for trip in sorted_trips:
        trip['route_color'] = route_colors.get(trip['line'], 'Unknown')

    return sorted_trips

if __name__ == "__main__":
    print(get_subway_times())
