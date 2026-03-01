## Purpose
Define the current behavior of the Flask web configuration control plane, including config persistence, service control side effects, reset workflow, and logging.

## Requirements
### Requirement: Web Configuration UI Reads and Writes JSON Settings
The web control plane SHALL load and persist configuration in `setup/matrix_config.json` using `wifi`, `display`, and `feed` sections.

#### Scenario: Initial config load
- **WHEN** `/` is requested with GET
- **THEN** the app renders `templates/index.html` with current JSON values or empty section defaults when file is missing

#### Scenario: Settings save
- **WHEN** `/` receives POST form data
- **THEN** the app maps form fields into JSON config keys and writes formatted JSON back to `setup/matrix_config.json`

### Requirement: Save Operation Triggers Runtime Control Commands
The web control plane SHALL execute WiFi and service control commands after successful POST save.

#### Scenario: Post-save side effects
- **WHEN** settings are saved on POST
- **THEN** the app invokes `wpa_cli reconfigure`, restarts `subway-sign`, and stops `hostapd` and `dnsmasq`

### Requirement: Factory Reset Restores Default Config and Restarts Display Service
The web control plane SHALL restore defaults from `setup/matrix_config_default.json` when `/reset` is invoked.

#### Scenario: Reset success
- **WHEN** `/reset` receives POST and default file exists
- **THEN** it copies default config to active config and restarts `subway-sign`

#### Scenario: Reset missing default
- **WHEN** `/reset` receives POST and default file is missing
- **THEN** it returns HTTP 500 with an error message

### Requirement: Web UI Operates Without Authentication
The web control plane SHALL expose configuration and reset endpoints without auth checks in current baseline behavior.

#### Scenario: Unauthenticated access
- **WHEN** an HTTP client reaches `/` or `/reset`
- **THEN** requests are processed without credential challenge

### Requirement: Control Plane Logs to Shared Log File
The web control plane SHALL write events to `/var/log/subway_sign.log` for setting updates, reset operations, and service actions.

#### Scenario: Settings update log record
- **WHEN** POST update succeeds
- **THEN** log records include submitted form values and subsequent service/AP command events
