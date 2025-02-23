import toml
import pathlib
import time
import os

#get current file path
app_dir = pathlib.Path(__file__).parent.parent
rgb_dir = app_dir.parent.parent / 'rpi-rgb-led-matrix' / 'bindings' / 'python'

# Add rgbmatrix folder to system path
os.sys.path.append(str(rgb_dir))

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from display import get_clamped_color
from trips import Trips


# Load the TOML file
with open(app_dir / 'settings.toml', 'r') as file:
    config = toml.load(file)

# Load configuration from environment variables
REFRESH_TIME_DELAY = int(config["REFRESH_TIME_DELAY"])
ROTATE_TRIP_DELAY = int(config["ROTATE_TRIP_DELAY"])
MINIMUM_ARRIVAL_MINUTES = int(config["MINIMUM_ARRIVAL_MINUTES"])
LED_ROWS = int(config["LED_ROWS"])
LED_COLUMNS = int(config["LED_COLUMNS"])
LED_CHAIN_LENGTH = int(config["LED_CHAIN_LENGTH"])
LED_PARALLEL = int(config["LED_PARALLEL"])
LED_HARDWARE_MAPPING = config["LED_HARDWARE_MAPPING"]
LINE_DIRECTION_MAX_LENGTH = int(config["LINE_DIRECTION_MAX_LENGTH"])

MTA_ROUTES = list(config["MTA_ROUTES"].split(','))
MTA_STOP = config["MTA_STOP"]
MTA_DIRECTIONS = list(config["MTA_DIRECTIONS"].split(','))
MTA_FEED_BASE_URL = config['MTA_FEED_BASE_URL']

# Load data once at startup
trips = Trips(MTA_STOP, MTA_DIRECTIONS, MTA_ROUTES)

# Initialize the RGBMatrix
options = RGBMatrixOptions()
options.rows = LED_ROWS
options.cols = LED_COLUMNS
options.chain_length = LED_CHAIN_LENGTH
options.parallel = LED_PARALLEL
options.hardware_mapping = LED_HARDWARE_MAPPING
## send the options to the RGBMatrix
matrix = RGBMatrix(options=options)
## create a frame canvas
canvas = matrix.CreateFrameCanvas()

## Set main text font
font = graphics.Font()
font.LoadFont(str(app_dir / 'fonts' / "10-Adobe-Helvetica.bdf"))
## Set route font
route_font = graphics.Font()
route_font.LoadFont(str(app_dir / 'fonts' / "mta.bdf"))

# Main Loop
start_time = time.monotonic()
rotate_time = start_time
time.sleep(1)
TRIP_JSON = trips.fetch_trip_data()
bottom_row_index = 0

while True:
    if (time.monotonic() - start_time) > REFRESH_TIME_DELAY:
        TRIP_JSON = trips.fetch_trip_data()
        start_time = time.monotonic()
    if (time.monotonic() - rotate_time) > ROTATE_TRIP_DELAY:
        bottom_row_index =  bottom_row_index + 1 if bottom_row_index < len(TRIP_JSON) - 1 else 0
        rotate_time = time.monotonic()

    canvas.Clear()
    # First Row
    color_value = int(TRIP_JSON[0].get('route_color', 'FFFFFF'), 16)
    color = get_clamped_color(color_value)
    graphics.DrawText(canvas, route_font, 0, 10, color, TRIP_JSON[0]["line"])
    graphics.DrawText(canvas, font, 11, 9, color, TRIP_JSON[0]["direction"][:LINE_DIRECTION_MAX_LENGTH])
    graphics.DrawText(canvas, font, 55, 9, color, str(TRIP_JSON[0]["minutes_until_arrival"]))

    # Second Row
    color_value = int(TRIP_JSON[1].get('route_color', 'FFFFFF'), 16)
    color = get_clamped_color(color_value)
    graphics.DrawText(canvas, route_font, 0, 20, color, TRIP_JSON[1]["line"])
    graphics.DrawText(canvas, font, 11, 19, color, TRIP_JSON[1]["direction"][:LINE_DIRECTION_MAX_LENGTH])
    graphics.DrawText(canvas, font, 55, 19, color, str(TRIP_JSON[1]["minutes_until_arrival"]))

    # Third Row
    color_value = int(TRIP_JSON[bottom_row_index].get('route_color', 'FFFFFF'), 16)
    color = get_clamped_color(color_value)
    graphics.DrawText(canvas, route_font, 0, 30, color, TRIP_JSON[bottom_row_index]["line"])
    graphics.DrawText(canvas, font, 11, 29, color, TRIP_JSON[bottom_row_index]["direction"][:LINE_DIRECTION_MAX_LENGTH])
    graphics.DrawText(canvas, font, 55, 29, color, str(TRIP_JSON[bottom_row_index]["minutes_until_arrival"]))

    elapsed_time = time.monotonic() - start_time
    pixels_on = int(((REFRESH_TIME_DELAY - elapsed_time) / REFRESH_TIME_DELAY) * LED_COLUMNS)
    color = graphics.Color(255, 255, 255)
    graphics.DrawLine(canvas, 0, 31, pixels_on, 31, color)


    matrix.SwapOnVSync(canvas)
    time.sleep(1)