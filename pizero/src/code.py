import time
import board
from adafruit_matrixportal.matrixportal import MatrixPortal
import gtfs_realtime_pb2
import gc  # Import garbage collection module
import os

from adafruit_datetime import datetime

# Load configuration from environment variables
REFRESH_TIME_DELAY = int(os.getenv("REFRESH_TIME_DELAY"))
DATA_SOURCE = os.getenv("DATA_SOURCE")
MTA_ROUTES = list(os.getenv("MTA_ROUTES").split(','))
MTA_STOP = os.getenv("MTA_STOP")
MTA_DIRECTIONS = list(os.getenv("MTA_DIRECTIONS").split(','))

MTA_FEED_BASE_URL = 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2F'

MTA_FEEDS = ['gtfs-bdfm', 'gtfs-g']


## Display 
GRID_SIZE = 3 
FONT = "/10-Adobe-Helvetica.bdf"
LINE_FONT = "/mta.bdf"
FONT_SCALE = 0.5
TIME_DELAY = 4
START_Y = -3
COUNTDOWN_POSITION = [0, 26]
CELL_POSITIONS = [
    [-5, -4], [-3, 5], [12, -3], [53, -4],
    [-5, 6], [-3, 15], [12, 7], [53, 6],
    [-5, 16], [-3, 25], [12, 17], [53, 16]
]



#TODO: Ensure that trips are ordered properly when passing midnight, 00:05 shows as before 23:55 and we don't want that since its later becuase its the next day

def get_stops(station, directions=None):
    stops = []
    with open('data/stops.txt', 'r') as file:
        for line in file:
            row = line.strip().split(',')
            if row[1] == station:
                if directions is None or row[0][-1] in directions:
                    stops.append(row[0])
    return stops

def get_trip_directions(routes):
    trip_directions = {}
    with open('data/trips.txt', 'r') as file:
        for line in file:
            lineroute = line[0]
            if lineroute in routes: pass
            else: continue
            row = line.strip().split(',')
            trip_directions[row[1].split('.')[-1]] = row[3]
    return trip_directions

def get_route_colors(routes):
    route_colors = {}
    with open('data/routes.txt', 'r') as file:
        for line in file:
            row = line.strip().split(',')
            routeid = row[1]
            if routeid in routes: pass
            else: continue
            route_colors[routeid] = row[-2]  # route_id and route_color
    return route_colors

def get_mta_data(stations, trip_directions):
    trips = []
    urls = [f"{MTA_FEED_BASE_URL}{feed}" for feed in MTA_FEEDS]
    
    for url in urls:
        current_time = datetime.now().timestamp()
        response = matrixportal.network.fetch(url, timeout=60) #requests.get(url)
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
                            trip['minutes_until_arrival'] = int((arrival_time.timestamp() - current_time) // 60)
                            if trip.get('line')=='F': direction = 'Manhatta'
                            elif trip.get('line')=='G': direction = 'Queens'
                            else: direction =='Adventure Time'
                            trip['direction'] = direction
                            # trip['direction'] = trip_directions.get(entity_trip.trip.trip_id.split('.')[-1], 'Unknown')
                            trips.append(trip)
        else:
            print(f"Failed to retrieve data from {url}: {response.status_code}")
    
    return trips




def get_subway_times(count=5):
    trips = get_mta_data(stops, trip_directions)

    # Sort trips by arrival time and get the specified number of trips
    sorted_trips = sorted(trips, key=lambda x: x['arrival_time'])[:count]

    # Add route color to each trip
    for trip in sorted_trips:
        trip['route_color'] = route_colors.get(trip['line'], 'Unknown')

    return sorted_trips




### Functions
# Fetch trip data with proper reconnection logic
def fetch_trip_data(retries=3):
    gc.collect()  # Force garbage collection
    attempt = 0
    while attempt < retries:
        try:
            trip_data = matrixportal.network.fetch(DATA_SOURCE, timeout=60)
            trips = get_subway_times()
            # with open(DEMO_FILE, 'r') as file:
            #     trips = json.load(file)
            if not trips:
                raise ValueError("No trips found")
            return trips
        except Exception as e:
            matrixportal.set_text("No trip data available", 0)
            matrixportal.set_text_color(0xFF0000, 0)
            print(f"Error fetching trip data (attempt {attempt + 1}): {e}")
            attempt += 1
            time.sleep(REFRESH_TIME_DELAY)  # Wait before retrying

    return None

# # Function to clear all text boxes
# def clear_text_boxes():
#     # matrixportal.remove_all_text()
#     for i in range(12):  # Assuming there are 12 text boxes
#         try: matrixportal.set_text("", i)
#         except: pass

# def build_trip_text(trip, column, index):
#     if column == 0:
#         return str(index)
#     elif column == 1:
#         return trip["line"]
#     elif column == 2:
#         return trip["direction"]
#     elif column == 3:
#         return str(trip["minutes_until_arrival"])

# # Function to update the countdown timer
# def update_countdown_timer(start_time, refresh_time_delay):
#     elapsed_time = time.monotonic() - start_time
#     total_pixels = 32  # Assuming the width of the display is 32 pixels
#     pixels_on = int(((refresh_time_delay - elapsed_time) / refresh_time_delay) * total_pixels)
#     countdown_text = "i" * pixels_on + " " * (total_pixels - pixels_on)
#     matrixportal.set_text(countdown_text, 12)
#     return

# def start_grid(trip_json):
#     for j in range(4):
#         if len(trip_json) > 0:
#             # Display the first trip
#             matrixportal.set_text(build_trip_text(trip_json[0], j, 1), j)
#             matrixportal.set_text_color(int(trip_json[0].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, j)
#         if len(trip_json) > 1:
#             # Display the second trip
#             matrixportal.set_text(build_trip_text(trip_json[1], j, 2), 4 + j)
#             matrixportal.set_text_color(int(trip_json[1].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, 4 + j)
#     return

# def update_grid(trip_json, start_index=2):
#     trip_size = len(trip_json)
#     for i in range(start_index, trip_size):
#         for j in range(4):
#             if trip_size > 0:
#                 # Display the first trip
#                 matrixportal.set_text(build_trip_text(trip_json[0], j, 1), j)
#                 matrixportal.set_text_color(int(trip_json[0].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, j)
#             if trip_size > 1:
#                 # Display the second trip
#                 matrixportal.set_text(build_trip_text(trip_json[1], j, 2), 4 + j)
#                 matrixportal.set_text_color(int(trip_json[1].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, 4 + j)
#             if trip_size > i:
#                 # Display the third trip
#                 matrixportal.set_text(build_trip_text(trip_json[i], j, i+1), 8 + j)
#                 matrixportal.set_text_color(int(trip_json[i].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, 8 + j)
#         update_countdown_timer(start_time, REFRESH_TIME_DELAY)
#         time.sleep(TIME_DELAY)
#     return


### Prepare the Display
# Initialize the MatrixPortal
matrixportal = MatrixPortal(status_neopixel=board.NEOPIXEL, bit_depth=3)

# Build the grid
for i in range(3):
    for j in range(4):
        cell_index = i * 4 + j
        matrixportal.add_text(
            text_font=FONT if j!=1 else LINE_FONT,
            text_scale=FONT_SCALE,
            text_position=CELL_POSITIONS[cell_index],
            text_color=0xFFFFFF,
            text="",
            scrolling=False,
            text_maxlen=10 if j == 2 else 2,
        )

# Add the countdown timer text box
matrixportal.add_text(
    text_font=FONT,
    text_scale=FONT_SCALE,
    text_position=COUNTDOWN_POSITION,
    text_color=0xFFFFFF,
    text="",
    scrolling=False,
    text_maxlen=200,
)


# Prepare Station Data
matrixportal.set_text("booting...", 2)
matrixportal.set_text(MTA_STOP, 6)
matrixportal.set_text(f"{','.join(MTA_ROUTES)}", 10)
# Load data once at startup
stops = get_stops(MTA_STOP, MTA_DIRECTIONS)
trip_directions = get_trip_directions(routes=MTA_ROUTES)
route_colors = get_route_colors(routes=MTA_ROUTES)
#reset text
matrixportal.set_text("", 2)
matrixportal.set_text("", 6)
matrixportal.set_text("", 10)
# report configuration
line_textbox = 1
station_textbox = 2
increment = 0
for r in MTA_ROUTES:
    matrixportal.set_text_color(int(route_colors.get(r, 'FFFFFF'), 16), line_textbox+increment)
    matrixportal.set_text(f"{r}", line_textbox+increment)
    increment += 4

time.sleep(5)



### Main Loop
# Keep the display on and update trip data in a loop
start_time = time.monotonic()
time.sleep(1)  # Wait for the display to initialize
TRIP_JSON = fetch_trip_data()
# while True:
#     if (time.monotonic() - start_time) > REFRESH_TIME_DELAY:
#         clear_text_boxes()
#         TRIP_JSON = fetch_trip_data()
#         start_time = time.monotonic()
#         start_grid(TRIP_JSON)
#     update_grid(TRIP_JSON, start_index=2)  # Update only the last row
#     gc.collect()  # Force garbage collection
