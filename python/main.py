import pathlib
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
from route_symbols import build_route_symbol_renderer
from trips import Trips

# Load configuration from canonical source.
config = load_runtime_config()
display_config = config["display"]
feed_config = config["feed"]

REFRESH_TIME_DELAY = display_config["refresh_time_delay"]
STALE_DATA_GRACE_SEC = display_config["stale_data_grace_sec"]
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


def _placeholder_trips():
    placeholder = {
        "line": "--",
        "direction": "No Data",
        "minutes_until_arrival": "--",
        "route_color": "FFFFFF",
    }
    return [dict(placeholder), dict(placeholder), dict(placeholder)]


def _normalize_for_render(trip_data):
    if not trip_data:
        return _placeholder_trips()
    rows = list(trip_data)
    while len(rows) < 3:
        rows.append(dict(rows[-1]))
    return rows


def _parse_color_value(raw_color):
    try:
        return int(str(raw_color or "FFFFFF"), 16)
    except ValueError:
        return int("FFFFFF", 16)

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
route_symbol_renderer = build_route_symbol_renderer(display_config, route_font, font, logging.getLogger(__name__))

# Main Loop
start_time = time.monotonic()
rotate_time = start_time
time.sleep(1)
TRIP_JSON = trips.fetch_trip_data()
last_success_time = time.monotonic() if TRIP_JSON else 0.0
current_refresh_delay = max(1, int(getattr(trips, "last_refresh_interval_sec", REFRESH_TIME_DELAY)))
bottom_row_index = 2

try:
    while True:
        now = time.monotonic()
        elapsed_since_fetch = now - start_time
        stale_elapsed = (now - last_success_time) if last_success_time else float("inf")
        if elapsed_since_fetch > current_refresh_delay or stale_elapsed > STALE_DATA_GRACE_SEC:
            latest_trips = trips.fetch_trip_data()
            start_time = time.monotonic()
            current_refresh_delay = max(1, int(getattr(trips, "last_refresh_interval_sec", REFRESH_TIME_DELAY)))
            if latest_trips:
                TRIP_JSON = latest_trips
                last_success_time = time.monotonic()

        render_rows = _normalize_for_render(TRIP_JSON)
        if (time.monotonic() - rotate_time) > ROTATE_TRIP_DELAY:
            bottom_row_index = bottom_row_index + 1 if bottom_row_index < len(render_rows) - 1 else 2
            rotate_time = time.monotonic()

        canvas.Clear()
        # First Row
        color_value = _parse_color_value(render_rows[0].get("route_color"))
        color = get_clamped_color(color_value)
        route_symbol_renderer.render(canvas, render_rows[0].get("line", ""), 0, 10, color_value)
        graphics.DrawText(canvas, font, 11, 9, color, render_rows[0]["direction"][:LINE_DIRECTION_MAX_LENGTH])
        graphics.DrawText(canvas, font, 55, 9, color, str(render_rows[0]["minutes_until_arrival"]))

        # Second Row
        color_value = _parse_color_value(render_rows[1].get("route_color"))
        color = get_clamped_color(color_value)
        route_symbol_renderer.render(canvas, render_rows[1].get("line", ""), 0, 20, color_value)
        graphics.DrawText(canvas, font, 11, 19, color, render_rows[1]["direction"][:LINE_DIRECTION_MAX_LENGTH])
        graphics.DrawText(canvas, font, 55, 19, color, str(render_rows[1]["minutes_until_arrival"]))

        # Third Row
        color_value = _parse_color_value(render_rows[bottom_row_index].get("route_color"))
        color = get_clamped_color(color_value)
        route_symbol_renderer.render(canvas, render_rows[bottom_row_index].get("line", ""), 0, 30, color_value)
        graphics.DrawText(canvas, font, 11, 29, color, render_rows[bottom_row_index]["direction"][:LINE_DIRECTION_MAX_LENGTH])
        graphics.DrawText(canvas, font, 55, 29, color, str(render_rows[bottom_row_index]["minutes_until_arrival"]))

        elapsed_time = time.monotonic() - start_time
        remaining = max(0.0, current_refresh_delay - elapsed_time)
        pixels_on = int((remaining / float(current_refresh_delay)) * LED_COLUMNS)
        color = graphics.Color(255, 255, 255)
        graphics.DrawLine(canvas, 0, 31, pixels_on, 31, color)


        matrix.SwapOnVSync(canvas)
        time.sleep(SCREEN_REFRESH_INTERVAL)

except Exception as e:
    logging.error(f"Display Error: {e}")
    raise
