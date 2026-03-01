## Purpose
Define the current runtime behavior of the LED display loop, render cadence, row layout, and fatal error handling in `python/main.py` and `python/display.py`.

## Requirements
### Requirement: Display Loop Polls and Renders on Fixed Intervals
The display runtime SHALL poll trip data every `REFRESH_TIME_DELAY` seconds and refresh the LED matrix every `SCREEN_REFRESH_INTERVAL` seconds.

#### Scenario: Trip data refresh interval
- **WHEN** `time.monotonic() - start_time > REFRESH_TIME_DELAY`
- **THEN** the runtime fetches new trip data and resets `start_time`

#### Scenario: Matrix redraw interval
- **WHEN** each loop iteration completes
- **THEN** the runtime clears the canvas, redraws rows/progress bar, swaps the frame, and sleeps for `SCREEN_REFRESH_INTERVAL`

### Requirement: Display Layout Uses Two Fixed Rows and One Rotating Row
The display runtime SHALL render three rows where row 1 uses trip index `0`, row 2 uses trip index `1`, and row 3 rotates through trip indexes `2..len(TRIP_JSON)-1`.

#### Scenario: Rotating row index updates
- **WHEN** `time.monotonic() - rotate_time > ROTATE_TRIP_DELAY`
- **THEN** `bottom_row_index` advances by 1 or wraps to `2`

### Requirement: Display Uses Route Color and Direction Truncation
The display runtime SHALL derive row text color from `route_color` and truncate direction text to `LINE_DIRECTION_MAX_LENGTH`.

#### Scenario: Route color conversion
- **WHEN** a trip contains `route_color` as hex text
- **THEN** the runtime converts it to RGB components and renders route, direction, and minutes with that color

#### Scenario: Missing route color fallback
- **WHEN** a trip does not contain `route_color`
- **THEN** the runtime uses `FFFFFF` as the fallback color

### Requirement: Progress Bar Reflects Time to Next Data Poll
The display runtime SHALL draw a bottom-row horizontal progress bar representing remaining time until next trip data fetch.

#### Scenario: Progress bar shrinks over refresh window
- **WHEN** elapsed time since `start_time` increases
- **THEN** `pixels_on` decreases proportionally from `LED_COLUMNS` to `0`

### Requirement: Runtime Depends on Root-Accessible LED Stack
The display runtime SHALL import and use `rgbmatrix` from the local `rpi-rgb-led-matrix` binding path and requires hardware access compatible with root execution.

#### Scenario: RGBMatrix import path setup
- **WHEN** startup initializes runtime
- **THEN** the process appends `<repo-parent>/rpi-rgb-led-matrix/bindings/python` to `sys.path` before importing `rgbmatrix`

### Requirement: Runtime Error Handling Is Fatal
The display runtime SHALL log uncaught loop exceptions to `/var/log/subway_sign.log` and re-raise the exception.

#### Scenario: Fatal render/runtime exception
- **WHEN** an exception escapes the main loop
- **THEN** the runtime logs `Display Error: <exception>` and exits by re-raising
