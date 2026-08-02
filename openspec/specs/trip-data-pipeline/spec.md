## Purpose
Define the current behavior of GTFS static parsing, MTA realtime feed ingestion, filtering, sorting, enrichment, and retry behavior in `python/trips.py`.

## Requirements
### Requirement: Static GTFS Inputs Are Read from the Active Local Dataset
The trip data pipeline SHALL read stops, trips, and routes metadata from the active promoted GTFS snapshot on each fetch cycle. When no snapshot is active, it SHALL use local files under `data/` as a bootstrap fallback; during the configured transition window, it SHALL also consult the previous snapshot for lookup compatibility.

#### Scenario: Stop filtering by station and direction
- **WHEN** `get_stops()` is called with configured `station` and `directions`
- **THEN** it returns stop IDs from the active lookup dataset whose stop name matches and whose suffix direction matches configured directions

#### Scenario: Trip direction map generation
- **WHEN** `get_trip_directions()` is called
- **THEN** it builds a map from parsed trip ID suffix to `trip_headsign` using the active lookup dataset filtered by configured routes

### Requirement: MTA Realtime Feeds Are Selected by Route-to-Feed Mapping
The trip data pipeline SHALL build feed URLs by matching configured routes against internal `MTA_FEEDS` mapping and requesting each matching feed endpoint.

#### Scenario: Feed URL selection
- **WHEN** routes are configured (for example `F,G`)
- **THEN** the pipeline requests `MTA_FEED_BASE_URL + <feed-name>` for each feed containing at least one configured route

### Requirement: Realtime Trips Are Filtered and Normalized
The trip data pipeline SHALL keep only trip updates for configured routes and configured station IDs, compute `minutes_until_arrival`, and attach direction text.

#### Scenario: Trip update inclusion
- **WHEN** a realtime entity has `trip_update` entries for configured route and stop IDs
- **THEN** the pipeline emits normalized trip records with `line`, `arrival_time`, `minutes_until_arrival`, and `direction`

#### Scenario: Realtime trip ID differs from static schedule ID
- **WHEN** a realtime trip ID does not exactly match a static trip ID suffix during a schedule transition
- **THEN** the pipeline uses a unique static headsign matching the realtime directional suffix when available, otherwise a directional label or `Direction unavailable`

### Requirement: Arrival Window and Sorting Are Applied
The trip data pipeline SHALL filter trips to the configured arrival bounds and sort ascending by `minutes_until_arrival`, returning up to `max_list` rows.

#### Scenario: Arrival bounds filter
- **WHEN** `get_subway_times(..., min_arrival, max_arrival)` executes
- **THEN** trips outside bounds are excluded before sort/limit

#### Scenario: Route color enrichment
- **WHEN** sorted trips are returned
- **THEN** each trip receives `route_color` from `routes.txt` or falls back to `FFFFFF`

### Requirement: Fetch Retries Use Refresh Delay Backoff
The trip data pipeline SHALL retry failed trip fetches up to `retries` times with sleep equal to `REFRESH_TIME_DELAY`.

#### Scenario: Empty or failed fetch retries
- **WHEN** fetch encounters exception or empty trip result
- **THEN** it logs or prints retry context, sleeps `REFRESH_TIME_DELAY`, and retries until max attempts

#### Scenario: Retry exhaustion returns null data
- **WHEN** all retry attempts fail
- **THEN** `fetch_trip_data()` returns `None`
