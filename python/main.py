import pathlib
import time
import os
import time
import logging

LOG_FILE = "/var/log/subway_sign.log"
logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG,
                    format="%(asctime)s [%(levelname)s] %(message)s")

#get current file path
app_dir = pathlib.Path(__file__).parent.parent
rgb_dir = app_dir.parent / 'rpi-rgb-led-matrix' / 'bindings' / 'python'

# Add rgbmatrix folder to system path
os.sys.path.append(str(rgb_dir))

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from display import get_clamped_color
from config import load_runtime_config
from trips import Trips

# Load configuration from canonical source.
config = load_runtime_config()
display_config = config["display"]
feed_config = config["feed"]

REFRESH_TIME_DELAY = display_config["refresh_time_delay"]
ROTATE_TRIP_DELAY = display_config["rotate_trip_delay"]
SCREEN_REFRESH_INTERVAL = display_config["screen_refresh_interval"]
MINIMUM_ARRIVAL_MINUTES = display_config["minimum_arrival_minutes"]
LED_ROWS = display_config["led_rows"]
LED_COLUMNS = display_config["led_columns"]
LED_CHAIN_LENGTH = display_config["led_chain_length"]
LED_PARALLEL = display_config["led_parallel"]
LED_HARDWARE_MAPPING = display_config["led_hardware_mapping"]
LINE_DIRECTION_MAX_LENGTH = display_config["line_direction_max_length"]

MTA_ROUTES = [route.strip() for route in feed_config["mta_routes"].split(",") if route.strip()]
MTA_STOP = feed_config["mta_stop"]
MTA_DIRECTIONS = [direction.strip() for direction in display_config["mta_directions"].split(",") if direction.strip()]

# Load data once at startup
trips = Trips(MTA_STOP, MTA_DIRECTIONS, MTA_ROUTES, config=config)

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
bottom_row_index = 2

try:
    while True:
        if (time.monotonic() - start_time) > REFRESH_TIME_DELAY:
            TRIP_JSON = trips.fetch_trip_data()
            start_time = time.monotonic()
        if (time.monotonic() - rotate_time) > ROTATE_TRIP_DELAY:
            bottom_row_index =  bottom_row_index + 1 if bottom_row_index < len(TRIP_JSON) - 1 else 2
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
        time.sleep(SCREEN_REFRESH_INTERVAL)

except Exception as e:
    logging.error(f"Display Error: {e}")
    raise
