## ADDED Requirements

### Requirement: Local console emulator launches without display hardware
The system SHALL provide a local console emulator entry point that runs without importing or initializing `rgbmatrix`, accessing GPIO, requiring root privileges, or starting a systemd service.

#### Scenario: Launch on a development machine
- **WHEN** a developer starts the console emulator on a machine without Raspberry Pi LED hardware
- **THEN** the emulator starts its terminal session without attempting to initialize the physical LED matrix

### Requirement: Console emulator uses runtime configuration
The console emulator SHALL load the runtime configuration through the existing configuration loader, including an alternate configuration selected with `MATRIX_CONFIG_PATH`, and SHALL display the selected station, routes, and directions in its terminal output.

#### Scenario: Alternate configuration is selected
- **WHEN** `MATRIX_CONFIG_PATH` identifies a valid emulator configuration file
- **THEN** the emulator uses that configuration's station, routes, directions, and display timing settings

### Requirement: Console emulator fetches production trip data
The console emulator SHALL construct and use the existing `Trips` pipeline to obtain live trip data, including its normal filtering, direction mapping, and adaptive refresh calculation.

#### Scenario: Successful live fetch
- **WHEN** the MTA feed returns eligible arrivals for the configured station
- **THEN** the emulator displays the returned route, direction, and minutes-until-arrival values and records the pipeline's next refresh interval

### Requirement: Console emulator follows logical sign row selection
The console emulator SHALL display the first two available trips as fixed rows and SHALL display a third row that rotates through available trip indexes from index two onward using the configured `rotate_trip_delay`.

#### Scenario: More than three trips are available
- **WHEN** the trip pipeline returns four or more trips and the configured rotation interval elapses
- **THEN** the emulator advances the third displayed row to the next eligible trip and wraps back to index two after the last trip

#### Scenario: Fewer than three trips are available
- **WHEN** the trip pipeline returns fewer than three trips
- **THEN** the emulator displays normalized logical rows without failing

### Requirement: Console emulator schedules feed requests using runtime cadence
The console emulator SHALL request trip data at startup and SHALL schedule later requests using the current `Trips.last_refresh_interval_sec` value, including adaptive intervals derived from the latest successful response.

#### Scenario: Adaptive interval changes after a fetch
- **WHEN** a successful fetch causes the trip pipeline to calculate a new refresh interval
- **THEN** the emulator bases its next data request countdown on that new interval

### Requirement: Console emulator exposes refresh and error state
The console emulator SHALL show the last successful fetch time, the remaining time until the next request, the active refresh interval, and the current freshness status. It SHALL preserve the last successful logical rows during a failed fetch and SHALL visibly report the fetch error and stale state once the configured stale-data grace interval is exceeded.

#### Scenario: Fetch fails during the stale-data grace interval
- **WHEN** a data request fails before the last successful result has exceeded `stale_data_grace_sec`
- **THEN** the emulator continues displaying the last successful rows and shows the fetch error

#### Scenario: Fetch fails after the stale-data grace interval
- **WHEN** a data request fails after the last successful result has exceeded `stale_data_grace_sec`
- **THEN** the emulator marks the state as stale and shows normalized no-data rows with the failure information