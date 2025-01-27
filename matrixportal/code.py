import time
import board
from adafruit_matrixportal.matrixportal import MatrixPortal
import gc  # Import garbage collection module


### Parameters
# Define the grid size
GRID_SIZE = 3
FONT = "/10-Adobe-Helvetica.bdf"
LINE_FONT = "/mta.bdf"
FONT_SCALE = 0.5
TIME_DELAY = 4  # Time delay between each row update for bottom row
REFRESH_TIME_DELAY = 30 # Time delay between each data refresh from API

# Endpoint URL
DATA_SOURCE = "http://192.168.1.223:5000/subway-times"

# Display Grid Parameters
START_Y = -3  # Define the starting y reference point
COUNTDOWN_POSITION = (0, 26)  # Add a position for the countdown timer
CELL_POSITIONS = [ # MTA FONT POSITIONS
    (-5, -4), (-3, 5), (12, -3), (53, -4),
    (-5, 6), (-3, 15), (12, 7), (53, 6),
    (-5, 16), (-3, 25), (12, 17), (53, 16)
]

# # Define the x, y positions for each cell
# CELL_POSITIONS = [
#     (0, -4), (6, -4), (15, -3), (53, -4),
#     (0, 6), (6, 6), (15, 7), (53, 6),
#     (0, 16), (6, 16), (15, 17), (53, 16)
# ]

# Initialize the MatrixPortal
matrixportal = MatrixPortal(status_neopixel=board.NEOPIXEL, bit_depth=3, url=DATA_SOURCE)

### Functions
# Fetch trip data with proper reconnection logic
def fetch_trip_data(retries=3):
    gc.collect()  # Force garbage collection
    attempt = 0
    while attempt < retries:
        try:
            trip_data = matrixportal.network.fetch(DATA_SOURCE, timeout=60)
            trips = trip_data.json()  # Parse JSON data
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

# Function to clear all text boxes
def clear_text_boxes():
    # matrixportal.remove_all_text()
    for i in range(12):  # Assuming there are 12 text boxes
        try: matrixportal.set_text("", i)
        except: pass

def build_trip_text(trip, column, index):
    if column == 0:
        return str(index)
    elif column == 1:
        return trip["line"]
    elif column == 2:
        return trip["direction"]
    elif column == 3:
        return str(trip["minutes_until_arrival"])

# Function to update the countdown timer
def update_countdown_timer(start_time, refresh_time_delay):
    elapsed_time = time.monotonic() - start_time
    total_pixels = 32  # Assuming the width of the display is 32 pixels
    pixels_on = int(((refresh_time_delay - elapsed_time) / refresh_time_delay) * total_pixels)
    countdown_text = "i" * pixels_on + " " * (total_pixels - pixels_on)
    matrixportal.set_text(countdown_text, 12)
    return

def start_grid(trip_json):
    for j in range(4):
        # Display the first trip
        matrixportal.set_text(build_trip_text(TRIP_JSON[0], j, 1), j)
        matrixportal.set_text_color(int(TRIP_JSON[0].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, j)
        # Display the second trip
        matrixportal.set_text(build_trip_text(TRIP_JSON[1], j, 2), 4 + j)
        matrixportal.set_text_color(int(TRIP_JSON[1].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, 4 + j)
    return

def update_grid(trip_json, start_index=2):
    trip_size = len(trip_json)
    for i in range(start_index, trip_size):
        for j in range(4):
            # Display the first trip
            matrixportal.set_text(build_trip_text(trip_json[0], j, 1), j)
            matrixportal.set_text_color(int(trip_json[0].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, j)
            # Display the second trip
            matrixportal.set_text(build_trip_text(trip_json[1], j, 2), 4 + j)
            matrixportal.set_text_color(int(trip_json[1].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, 4 + j)
            # Display the third trip
            matrixportal.set_text(build_trip_text(trip_json[i], j, i+1), 8 + j)
            matrixportal.set_text_color(int(trip_json[i].get('route_color', 'FFFFFF'), 16) if j != 0 else 0xFFFFFF, 8 + j)
        update_countdown_timer(start_time, REFRESH_TIME_DELAY)
        time.sleep(TIME_DELAY)
    return


### Prepare the Display

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


### Main Loop
# Keep the display on and update trip data in a loop
start_time = time.monotonic()
time.sleep(1)  # Wait for the display to initialize
TRIP_JSON = fetch_trip_data()
while True:
    if (time.monotonic() - start_time) > REFRESH_TIME_DELAY:
        clear_text_boxes()
        TRIP_JSON = fetch_trip_data()
        start_time = time.monotonic()
        start_grid(TRIP_JSON)
    update_grid(TRIP_JSON, start_index=2)  # Update only the last row
    gc.collect()  # Force garbage collection
