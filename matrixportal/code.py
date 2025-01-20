import time
import board
import terminalio
from adafruit_matrixportal.matrixportal import MatrixPortal
import json
import gc  # Import garbage collection module

time.sleep(5)

# Define the grid size
GRID_SIZE = 3
# FONT = terminalio.FONT
FONT = "/10-Adobe-Helvetica.bdf"
LINE_FONT = "/mta.bdf"
FONT_SCALE = 0.5
TIME_DELAY = 4
# Refresh time delay in seconds
REFRESH_TIME_DELAY = 60

# Endpoint URL
DATA_SOURCE = "http://192.168.1.223:5000/subway-times"
# TRIP_JSON_PATH = ["subway-times"]

# Demo mode flag
DEMO_MODE = False
DEMO_FILE = "demo_data.json"

# Initialize the MatrixPortal
matrixportal = MatrixPortal(status_neopixel=board.NEOPIXEL, bit_depth=3, url=DATA_SOURCE)

# Connect to Wi-Fi with retry logic
def connect_wifi(retries=3):
    attempt = 0
    while attempt < retries:
        try:
            if not matrixportal.network.is_connected:
                matrixportal.network.connect()
                print("Connected to Wi-Fi")
                print("IP Address:", matrixportal.network.ip_address)
                return True
        except Exception as e:
            print(f"Wi-Fi connection attempt {attempt + 1} failed: {e}")
            attempt += 1
            time.sleep(REFRESH_TIME_DELAY)  # Wait before retrying
    return False

if not DEMO_MODE:
    if not connect_wifi():
        print("Failed to connect to Wi-Fi after multiple attempts")
        # Handle the failure case as needed

# Function to fetch trip data with memory management and retry logic
def fetch_trip_data(retries=3):
    gc.collect()  # Force garbage collection
    attempt = 0
    while attempt < retries:
        try:
            if DEMO_MODE:
                with open(DEMO_FILE, 'r') as file:
                    trips = json.load(file)
                    if not trips:
                        raise ValueError("No trips found")
                    return trips
            else:
                trip_data = matrixportal.network.fetch(DATA_SOURCE)
                trips = trip_data.json()  # matrixportal.network.json_traverse(trip_data.json())
                if not trips:
                    raise ValueError("No trips found")
                return trips
        except Exception as e:
            print(f"Error fetching trip data (attempt {attempt + 1}):", e)
            attempt += 1
            time.sleep(REFRESH_TIME_DELAY)  # Wait before retrying
            matrixportal.network.disconnect()  # Ensure the socket is closed
            matrixportal.network.connect()  # Reconnect to Wi-Fi
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

def start_grid(trip_json):
    for j in range(4):
        # Display the first trip
        matrixportal.set_text(build_trip_text(trip_json[0], j, 1), j)
        matrixportal.set_text_color(int(trip_json[0].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, j)
        # Display the second trip
        matrixportal.set_text(build_trip_text(trip_json[1], j, 2), 4 + j)
        matrixportal.set_text_color(int(trip_json[1].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, 4 + j)

def update_grid(trip_json, start_index=2):
    trip_size = len(trip_json)
    for i in range(start_index, trip_size):
        for j in range(4):
            matrixportal.set_text(build_trip_text(trip_json[i], j, i+1), 8 + j)
            matrixportal.set_text_color(int(trip_json[i].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, 8 + j)
        time.sleep(TIME_DELAY)

# Define the starting y reference point
START_Y = -3

# # Define the x, y positions for each cell
# CELL_POSITIONS = [
#     (0, -4), (6, -4), (15, -3), (53, -4),
#     (0, 6), (6, 6), (15, 7), (53, 6),
#     (0, 16), (6, 16), (15, 17), (53, 16)
# ]

# # MTA FONT POSITIONS
CELL_POSITIONS = [
    (-5, -4), (-3, 5), (12, -3), (53, -4),
    (-5, 6), (-3, 15), (12, 7), (53, 6),
    (-5, 16), (-3, 25), (12, 17), (53, 16)
]

# Add a position for the countdown timer
COUNTDOWN_POSITION = (0, 26)

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

# Function to update the countdown timer
def update_countdown_timer(start_time, refresh_time_delay):
    elapsed_time = time.monotonic() - start_time
    total_pixels = 32  # Assuming the width of the display is 32 pixels
    pixels_on = int(((refresh_time_delay - elapsed_time) / refresh_time_delay) * total_pixels)
    countdown_text = "i" * pixels_on + " " * (total_pixels - pixels_on)
    matrixportal.set_text(countdown_text, 12)

# Keep the display on and update trip data in a loop
while True:
    TRIP_JSON = fetch_trip_data()
    
    if not TRIP_JSON:
        matrixportal.set_text("No trip data available", 0)
        matrixportal.set_text_color(0xFF0000, 0)
        if not DEMO_MODE:
            if not connect_wifi():  # Attempt to reconnect to Wi-Fi
                print("Failed to reconnect to Wi-Fi")
                continue  # Skip the rest of the loop if Wi-Fi reconnection fails
    else:
        start_grid(TRIP_JSON)  # Initialize the grid with the first two rows
        start_time = time.monotonic()
        update_countdown_timer(start_time, REFRESH_TIME_DELAY)
        while (time.monotonic() - start_time) < REFRESH_TIME_DELAY:
            update_grid(TRIP_JSON, start_index=2)  # Update only the last row
            update_countdown_timer(start_time, REFRESH_TIME_DELAY)
            time.sleep(TIME_DELAY)
    gc.collect()  # Force garbage collection
