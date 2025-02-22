from trips import get_stops, get_trip_directions, get_mta_data, get_route_colors
import toml
import pathlib

#get current file path
cwd = pathlib.Path(__file__).parent.parent

# Load the TOML file
with open(cwd / 'settings.toml', 'r') as file:
    config = toml.load(file)

# Load configuration from environment variables
REFRESH_TIME_DELAY = int(config["REFRESH_TIME_DELAY"])
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
    trips = get_mta_data(MTA_ROUTES,stations, trip_directions)

    # Filter out trips that are too close to arrival
    trips = [trip for trip in trips if trip['minutes_until_arrival'] >= min_arrival]

    # Sort trips by arrival time and get the specified number of trips
    sorted_trips = sorted(trips, key=lambda x: x['minutes_until_arrival'])[:max_list]

    # Add route color to each trip
    for trip in sorted_trips:
        trip['route_color'] = route_colors.get(trip['line'], 'FFFFFF')

    return sorted_trips

#!/usr/bin/env python
# Display a runtext with double-buffering.
from samplebase import SampleBase
from rgbmatrix import graphics
import time

class RunText(SampleBase):
    def __init__(self, *args, **kwargs):
        super(RunText, self).__init__(*args, **kwargs)
        self.parser.add_argument("-t", "--text", help="The text to scroll on the RGB LED panel", default="Hello world!")

    def run(self):
        offscreen_canvas = self.matrix.CreateFrameCanvas()
        font = graphics.Font()
        font.LoadFont("../../../fonts/7x13.bdf")
        textColor = graphics.Color(255, 255, 0)
        pos = offscreen_canvas.width
        my_text = self.args.text

        while True:
            offscreen_canvas.Clear()
            len = graphics.DrawText(offscreen_canvas, font, pos, 10, textColor, my_text)
            pos -= 1
            if (pos + len < 0):
                pos = offscreen_canvas.width

            time.sleep(0.05)
            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)


# Main function
if __name__ == "__main__":
    run_text = RunText()
    if (not run_text.process()):
        run_text.print_help()

