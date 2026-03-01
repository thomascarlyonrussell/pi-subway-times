## Context
Current runtime reads `settings.toml`, while web config writes JSON and setup seeds `/etc` JSON defaults. This produces drift and user-visible confusion when settings changes do not propagate.

## Goals / Non-Goals

**Goals:**
- Establish one canonical configuration source and schema.
- Define compatibility and migration from current TOML/JSON assets.
- Ensure settings updates consistently apply to running services.

**Non-Goals:**
- Redesign of UI/UX forms.
- Feature additions beyond configuration flow.

## Decisions
- Canonical source: JSON at `/etc/matrix_config.json` (service-accessible and already used by setup defaults).
- Runtime modules consume canonical config via a shared loader adapter to avoid duplicated parsing logic.
- TOML retained temporarily as read-only compatibility input during migration window, then deprecated.
- Config writes from web UI are validated and atomically persisted before service apply actions.

## Canonical JSON Schema and Mapping
Canonical shape:

```json
{
  "wifi": {
    "ssid": "string",
    "password": "string"
  },
  "display": {
    "brightness": "int 0..100",
    "mta_directions": "comma-separated directions",
    "refresh_time_delay": "int",
    "rotate_trip_delay": "int",
    "screen_refresh_interval": "int",
    "minimum_arrival_minutes": "int",
    "maximum_arrival_minutes": "int",
    "led_rows": "int",
    "led_columns": "int",
    "led_chain_length": "int",
    "led_parallel": "int",
    "led_hardware_mapping": "string",
    "line_direction_max_length": "int"
  },
  "feed": {
    "mta_routes": "comma-separated routes",
    "mta_stop": "string",
    "mta_feed_base_url": "string"
  }
}
```

Legacy TOML key mapping:
- `MTA_ROUTES` → `feed.mta_routes`
- `MTA_STOP` → `feed.mta_stop`
- `MTA_DIRECTIONS` → `display.mta_directions`
- `REFRESH_TIME_DELAY` → `display.refresh_time_delay`
- `ROTATE_TRIP_DELAY` → `display.rotate_trip_delay`
- `SCREEN_REFRESH_INTERVAL` → `display.screen_refresh_interval`
- `MINIMUM_ARRIVAL_MINUTES` → `display.minimum_arrival_minutes`
- `MAXIMUM_ARRIVAL_MINUTES` → `display.maximum_arrival_minutes`
- `LED_ROWS` → `display.led_rows`
- `LED_COLUMNS` → `display.led_columns`
- `LED_CHAIN_LENGTH` → `display.led_chain_length`
- `LED_PARALLEL` → `display.led_parallel`
- `LED_HARDWARE_MAPPING` → `display.led_hardware_mapping`
- `LINE_DIRECTION_MAX_LENGTH` → `display.line_direction_max_length`
- `MTA_FEED_BASE_URL` → `feed.mta_feed_base_url`

## Compatibility Window and Rollback
- Compatibility read path remains enabled while migrating hosts that still only have `settings.toml`.
- Runtime/web control-plane read order: canonical `/etc/matrix_config.json`, then defaults, then legacy TOML compatibility read.
- No reverse-sync is performed to TOML; canonical JSON is authoritative after first successful JSON save.
- Rollback behavior: if canonical JSON is invalid/missing and default JSON exists, runtime falls back to default JSON and logs warning.
- Emergency rollback: restore `/etc/matrix_config.json` from `/etc/matrix_config_default.json`, then restart `subway-sign`.

## Risks / Trade-offs
- [Risk] Migration can break startup if config file missing/invalid. → Mitigation: fallback to default template + clear error logs.
- [Risk] Service restarts on every save may interrupt display. → Mitigation: minimize restart scope and document when full restart is required.

## Migration Plan
1. Introduce shared config schema/loader and canonical path.
2. Add TOML-to-canonical migration command/path.
3. Switch runtime readers to canonical config.
4. Remove TOML dependency after verification.

## Open Questions
- Whether non-critical settings can be applied without full `subway-sign` restart.
