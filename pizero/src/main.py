from trips import get_stops, get_trip_directions, get_mta_data, get_route_colors
import toml
import pathlib
import time
import gc
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from display import clear_text_boxes, start_grid, update_grid

#get current file path
cwd = pathlib.Path(__file__).parent.parent

# Load the TOML file
with open(cwd / 'settings.toml', 'r') as file:
    config = toml.load(file)

# Load configuration from environment variables
REFRESH_TIME_DELAY = int(config["REFRESH_TIME_DELAY"])
ROTATE_TRIP_DELAY = int(config["ROTATE_TRIP_DELAY"])
MINIMUM_ARRIVAL_MINUTES = int(config["MINIMUM_ARRIVAL_MINUTES"])
MTA_ROUTES = list(config["MTA_ROUTES"].split(','))
MTA_STOP = config["MTA_STOP"]
MTA_DIRECTIONS = list(config["MTA_DIRECTIONS"].split(','))

MTA_FEED_BASE_URL = config['MTA_FEED_BASE_URL']

# Load data once at startup
stations = get_stops(MTA_STOP, MTA_DIRECTIONS)
trip_directions = get_trip_directions()
route_colors = get_route_colors()

def get_subway_times(max_list=5, min_arrival=MINIMUM_ARRIVAL_MINUTES):
    trips = get_mta_data(MTA_ROUTES, stations, trip_directions)

    # Filter out trips that are too close to arrival
    trips = [trip for trip in trips if trip['minutes_until_arrival'] >= min_arrival]

    # Sort trips by arrival time and get the specified number of trips
    sorted_trips = sorted(trips, key=lambda x: x['minutes_until_arrival'])[:max_list]

    # Add route color to each trip
    for trip in sorted_trips:
        trip['route_color'] = route_colors.get(trip['line'], 'FFFFFF')

    return sorted_trips

# Fetch trip data with proper reconnection logic
def fetch_trip_data(retries=3):
    gc.collect()  # Force garbage collection
    attempt = 0
    while attempt < retries:
        try:
            trips = get_subway_times()
            if not trips:
                raise ValueError("No trips found")
            return trips
        except Exception as e:
            print(f"Error fetching trip data (attempt {attempt + 1}): {e}")
            attempt += 1
            time.sleep(REFRESH_TIME_DELAY)  # Wait before retrying

    return None

# Initialize the RGBMatrix
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 1
options.parallel = 1
options.hardware_mapping = 'adafruit-hat'
matrix = RGBMatrix(options=options)
offscreen_canvas = matrix.CreateFrameCanvas()
font = graphics.Font()
font.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/7x13.bdf")

# Prepare Station Data
stops = get_stops(MTA_STOP, MTA_DIRECTIONS)
trip_directions = get_trip_directions(routes=MTA_ROUTES)
route_colors = get_route_colors(routes=MTA_ROUTES)

# Main Loop
start_time = time.monotonic()
time.sleep(1)
TRIP_JSON = fetch_trip_data()

while True:
    if (time.monotonic() - start_time) > REFRESH_TIME_DELAY:
        clear_text_boxes(matrix, offscreen_canvas)
        TRIP_JSON = fetch_trip_data()
        start_time = time.monotonic()
        start_grid(matrix, offscreen_canvas, font, TRIP_JSON)
    update_grid(matrix, offscreen_canvas, font, TRIP_JSON, start_index=2, time_delay=ROTATE_TRIP_DELAY)
    gc.collect()

