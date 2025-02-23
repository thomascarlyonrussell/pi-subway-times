from trips import Trips
import toml
import pathlib
import time
import gc
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from display import start_grid, get_clamped_color

#get current file path
cwd = pathlib.Path(__file__).parent.parent

# Load the TOML file
with open(cwd / 'settings.toml', 'r') as file:
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
font.LoadFont(str(cwd / 'fonts' / "10-Adobe-Helvetica.bdf"))
## Set route font
route_font = graphics.Font()
route_font.LoadFont(str(cwd / 'fonts' / "mta.bdf"))

# Main Loop
start_time = time.monotonic()
time.sleep(1)
TRIP_JSON = trips.fetch_trip_data()
bottom_row_index = 0

while True:
    if (time.monotonic() - start_time) > REFRESH_TIME_DELAY:
        canvas.Clear()
        TRIP_JSON = trips.fetch_trip_data()
        start_time = time.monotonic()
    if (time.monotonic() - rotate_time) > ROTATE_TRIP_DELAY:
        bottom_row_index =  bottom_row_index + 1 if bottom_row_index < len(TRIP_JSON) - 1 else 0
        rotate_time = time.monotonic()

    # First Row
    color_value = int(TRIP_JSON[0].get('route_color', 'FFFFFF'), 16)
    color = get_clamped_color(color_value)
    graphics.DrawText(canvas, font, 0, 0, color, TRIP_JSON[0]["line"])
    graphics.DrawText(canvas, font, 10, 0, color, TRIP_JSON[0]["direction"])
    graphics.DrawText(canvas, font, 25, 0, color, str(TRIP_JSON[0]["minutes_until_arrival"]))

    # Second Row
    color_value = int(TRIP_JSON[1].get('route_color', 'FFFFFF'), 16)
    color = get_clamped_color(color_value)
    graphics.DrawText(canvas, font, 0, 10, color, TRIP_JSON[1]["line"])
    graphics.DrawText(canvas, font, 10, 10, color, TRIP_JSON[1]["direction"])
    graphics.DrawText(canvas, font, 25, 10, color, str(TRIP_JSON[1]["minutes_until_arrival"]))

    # Third Row
    color_value = int(TRIP_JSON[bottom_row_index].get('route_color', 'FFFFFF'), 16)
    color = get_clamped_color(color_value)
    graphics.DrawText(canvas, font, 0, 20, color, TRIP_JSON[bottom_row_index]["line"])
    graphics.DrawText(canvas, font, 10, 20, color, TRIP_JSON[bottom_row_index]["direction"])
    graphics.DrawText(canvas, font, 25, 20, color, str(TRIP_JSON[bottom_row_index]["minutes_until_arrival"]))

    elapsed_time = time.monotonic() - start_time
    pixels_on = int(((REFRESH_TIME_DELAY - elapsed_time) / REFRESH_TIME_DELAY) * LED_ROWS)
    countdown_text = "i" * pixels_on + " " * (LED_ROWS - pixels_on)
    color = graphics.Color(255, 255, 255)
    graphics.DrawText(canvas, font, 0, 30, color, countdown_text)

    matrix.SwapOnVSync(canvas)
    time.sleep(0.5)