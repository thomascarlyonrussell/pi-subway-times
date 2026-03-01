## Purpose
Define the current configuration contracts and source-of-truth boundaries between TOML runtime settings and JSON web and setup settings.

## Requirements
### Requirement: Display Runtime Reads TOML at Startup
The display runtime SHALL load configuration keys from `settings.toml` during process startup.

#### Scenario: Startup config load
- **WHEN** `python/main.py` initializes
- **THEN** it reads timing, LED, route, stop, direction, and feed URL keys from `settings.toml`

### Requirement: Trip Pipeline Reads TOML for Feed and Arrival Bounds
The trip data pipeline SHALL load `settings.toml` for `MTA_FEED_BASE_URL` and fetch bounds used in retry and filter logic.

#### Scenario: Trip config dependency
- **WHEN** `Trips` is instantiated and `fetch_trip_data()` runs
- **THEN** trip fetch behavior depends on values from `settings.toml`

### Requirement: Web Control Plane Reads and Writes JSON Config
The web control plane SHALL persist all user-updated values in `setup/matrix_config.json`.

#### Scenario: Web config persistence
- **WHEN** settings are submitted via UI
- **THEN** fields are written to JSON keys under `wifi`, `display`, and `feed`

### Requirement: No Automatic TOML-JSON Synchronization Exists
Current baseline behavior SHALL treat TOML and JSON config files as independent data stores.

#### Scenario: JSON update does not update display runtime config source
- **WHEN** web UI updates only `setup/matrix_config.json`
- **THEN** display runtime remains bound to `settings.toml` unless separate manual or scripted synchronization occurs

### Requirement: Provisioning Seeds Separate Config Location in /etc
Provisioning SHALL create `/etc/matrix_config_default.json` and `/etc/matrix_config.json` as a separate runtime config location.

#### Scenario: Setup-created config path divergence
- **WHEN** setup script and web control plane paths are compared
- **THEN** baseline records path divergence between `/etc/matrix_config*.json` and `setup/matrix_config*.json`
