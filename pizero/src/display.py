from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
import time
import pathlib
import toml

#get current file path
cwd = pathlib.Path(__file__).parent.parent

# Load the TOML file
with open(cwd / 'settings.toml', 'r') as file:
    config = toml.load(file)

LED_ROWS = int(config["LED_ROWS"])

def clamp_color_value(value):
    return max(0, min(value, 255))

def get_clamped_color(color_value):
    return graphics.Color(clamp_color_value((color_value >> 16) & 0xFF),
                          clamp_color_value((color_value >> 8) & 0xFF),
                          clamp_color_value(color_value & 0xFF))

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
def update_countdown_timer(matrix, canvas, start_time, refresh_time_delay):
    elapsed_time = time.monotonic() - start_time
    total_pixels = LED_ROWS  # Assuming the width of the display is 32 pixels
    pixels_on = int(((refresh_time_delay - elapsed_time) / refresh_time_delay) * total_pixels)
    countdown_text = "i" * pixels_on + " " * (total_pixels - pixels_on)
    color = graphics.Color(255, 255, 255)
    canvas.Clear()
    graphics.DrawText(canvas, font, 0, 30, color, countdown_text)
    matrix.SwapOnVSync(canvas)
    return

def start_grid(matrix, canvas, trip_json):
    for j in range(4):
        if len(trip_json) > 0:
            text = build_trip_text(trip_json[0], j, 1)
            color_value = int(trip_json[0].get('route_color', 'FFFFFF'), 16)
            color = get_clamped_color(color_value)
            graphics.DrawText(canvas, font, 0, j * 10 + 10, color, text)
        if len(trip_json) > 1:
            text = build_trip_text(trip_json[1], j, 2)
            color_value = int(trip_json[1].get('route_color', 'FFFFFF'), 16)
            color = get_clamped_color(color_value)
            graphics.DrawText(canvas, font, 0, j * 10 + 20, color, text)
    matrix.SwapOnVSync(canvas)

def update_grid(matrix, canvas, trip_json, start_index=2, time_delay=0.5):
    trip_size = len(trip_json)
    for i in range(start_index, trip_size):
        for j in range(4):
            if trip_size > 0:
                text = build_trip_text(trip_json[0], j, 1)
                color_value = int(trip_json[0].get('route_color', 'FFFFFF'), 16)
                color = get_clamped_color(color_value)
                graphics.DrawText(canvas, font, 0, j * 10 + 10, color, text)
            if trip_size > 1:
                text = build_trip_text(trip_json[1], j, 2)
                color_value = int(trip_json[1].get('route_color', 'FFFFFF'), 16)
                color = get_clamped_color(color_value)
                graphics.DrawText(canvas, font, 0, j * 10 + 20, color, text)
            if trip_size > i:
                text = build_trip_text(trip_json[i], j, i + 1)
                color_value = int(trip_json[i].get('route_color', 'FFFFFF'), 16)
                color = get_clamped_color(color_value)
                graphics.DrawText(canvas, font, 0, j * 10 + 30, color, text)
        matrix.SwapOnVSync(canvas)
        time.sleep(time_delay)
    return
