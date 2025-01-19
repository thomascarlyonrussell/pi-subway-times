import time
import board
import terminalio
from adafruit_matrixportal.matrixportal import MatrixPortal
import json

time.sleep(5)

# Define the grid size
GRID_SIZE = 3
# FONT = terminalio.FONT
FONT = "/10-Adobe-Helvetica.bdf"
LINE_FONT = "/mta.bdf"
FONT_SCALE = 0.5
TIME_DELAY = 4

# Endpoint URL
DATA_SOURCE = "http://192.168.1.49:5000/subway-times"
# TRIP_JSON_PATH = ["subway-times"]

# Demo mode flag
DEMO_MODE = True
DEMO_FILE = "demo_data.json"

# Initialize the MatrixPortal
matrixportal = MatrixPortal(status_neopixel=board.NEOPIXEL, bit_depth=3, url=DATA_SOURCE)

# Connect to Wi-Fi
def connect_wifi():
    if not matrixportal.network.is_connected:
        matrixportal.network.connect()
        print("Connected to Wi-Fi")
        print("IP Address:", matrixportal.network.ip_address)

if not DEMO_MODE:
    connect_wifi()

# Function to fetch trip data
def fetch_trip_data():
    if DEMO_MODE:
        try:
            with open(DEMO_FILE, 'r') as file:
                trips = json.load(file)
                if not trips:
                    raise ValueError("No trips found")
                return trips
        except Exception as e:
            print("Error loading demo data:", e)
            return None
    else:
        try:
            trip_data = matrixportal.network.fetch(DATA_SOURCE)
            trips = matrixportal.network.json_traverse(trip_data.json())
            if not trips:
                raise ValueError("No trips found")
            return trips
        except Exception as e:
            print("Error fetching trip data:", e)
            return None

def build_trip_text(trip, column, index):
    if column == 0:
        return str(index)
    elif column == 1:
        return trip["line"]
    elif column == 2:
        return trip["direction"]
    elif column == 3:
        return str(trip["minutes_until_arrival"])

def display_grid(trip_json):
    trip_size = len(trip_json)
    for j in range(4):
        # Display the first trip
        matrixportal.set_text(build_trip_text(trip_json[0], j, 1), j)
        matrixportal.set_text_color(int(trip_json[0].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, j)
        # Display the second trip
        matrixportal.set_text(build_trip_text(trip_json[1], j, 2), 4 + j)
        matrixportal.set_text_color(int(trip_json[1].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, 4 + j)
        # Display the third trip (rotating through rest of trips)
    for i in range(2, trip_size):
        for j in range(4):
            matrixportal.set_text(build_trip_text(trip_json[i], j, i+1), 8 + j)
            matrixportal.set_text_color(int(trip_json[i].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, 8 + j)
        time.sleep(TIME_DELAY)

# Define the starting y reference point
START_Y = -3

# Define the x, y positions for each cell
CELL_POSITIONS = [
    (0, -4), (2, 5), (15, -3), (53, -4),
    (0, 6), (2, 15), (15, 7), (53, 6),
    (0, 16), (2, 25), (15, 17), (53, 16)
]

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
            text_maxlen=8 if j == 2 else 2,
        )

# Keep the display on and update trip data in a loop
while True:
    TRIP_JSON = fetch_trip_data()
    if not TRIP_JSON:
        matrixportal.set_text("No trip data available", 0)
        matrixportal.set_text_color(0xFF0000, 0)
        if not DEMO_MODE:
            connect_wifi()  # Attempt to reconnect to Wi-Fi
    else:
        display_grid(TRIP_JSON)  # Display all trips
    time.sleep(0.5)  # Fetch new data every 30 seconds
