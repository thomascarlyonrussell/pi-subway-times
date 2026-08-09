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
The display runtime MUST render route symbols through a route-symbol rendering strategy that supports multiple backend types and deterministic fallback behavior.

#### Scenario: Primary symbol backend available
- **WHEN** selected backend has symbol asset for route
- **THEN** the display draws route symbol using selected backend and existing color rules

#### Scenario: Primary symbol backend missing asset
- **WHEN** selected backend lacks requested symbol
- **THEN** fallback backend or textual route rendering is used without crashing render loop

#### Scenario: Station direction string pixel width truncation
- **WHEN** station direction string pixel width exceeds `LINE_DIRECTION_MAX_PIXELS` (default 40)
- **THEN** string is truncated so total rendered character width stays strictly under or equal to 40 pixels (and does not exceed `LINE_DIRECTION_MAX_LENGTH` if specified)

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
The display runtime MUST isolate symbol-rendering backend errors and continue rendering with fallback when feasible.

#### Scenario: Backend-specific render error
- **WHEN** backend render call fails for a symbol
- **THEN** runtime logs error context and uses configured fallback path for that frame

