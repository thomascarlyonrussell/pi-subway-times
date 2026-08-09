## Purpose
Define the current behavior of the Flask web configuration control plane, including config persistence, service control side effects, reset workflow, and logging.

## Requirements
### Requirement: Web Configuration UI Reads and Writes JSON Settings
The web control plane SHALL load and persist canonical JSON at `/etc/matrix_config.json`. It SHALL expose only Wi-Fi credentials, brightness, routes, stop, and directions for owner editing.

#### Scenario: Initial config load
- **WHEN** `/` is requested with GET
- **THEN** the app renders `templates/index.html` with the current canonical JSON owner-editable values

#### Scenario: Settings save
- **WHEN** an authenticated `/` POST supplies owner-editable values
- **THEN** the app validates and atomically writes those values to canonical JSON while preserving deployment-managed values

### Requirement: Save Operation Triggers Runtime Control Commands
The web control plane SHALL execute WiFi and service control commands after successful POST save.

#### Scenario: Post-save side effects
- **WHEN** settings are saved on POST
- **THEN** the app invokes `wpa_cli reconfigure`, restarts `subway-sign`, and stops `hostapd` and `dnsmasq`

### Requirement: Factory Reset Restores Default Config and Restarts Display Service
The web control plane SHALL restore the installed default template, clear Wi-Fi credentials, and return the device to AP onboarding when `/reset` is invoked by an authenticated user.

#### Scenario: Reset success
- **WHEN** `/reset` receives an authenticated POST and the default file exists
- **THEN** it saves default configuration with empty Wi-Fi credentials and starts AP onboarding services

#### Scenario: Reset missing default
- **WHEN** `/reset` receives POST and default file is missing
- **THEN** it returns HTTP 500 with an error message

### Requirement: Web UI Requires Setup Authentication for Mutation
The web control plane SHALL require a valid setup session before changing configuration or resetting the device.

#### Scenario: Unauthenticated mutation
- **WHEN** an HTTP client posts configuration changes or invokes `/reset` without a valid setup session
- **THEN** the control plane returns HTTP 401 and does not change device state

### Requirement: Control Plane Logs to Shared Log File
The web control plane SHALL write events to `/var/log/subway_sign.log` for setting updates, reset operations, and service actions.

#### Scenario: Settings update log record
- **WHEN** POST update succeeds
- **THEN** log records include submitted form values and subsequent service/AP command events
