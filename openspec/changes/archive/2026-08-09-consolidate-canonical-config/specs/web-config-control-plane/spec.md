## MODIFIED Requirements

### Requirement: Web Configuration UI Reads and Writes JSON Settings
The web control plane SHALL load and persist canonical JSON at `/etc/matrix_config.json`. It SHALL expose only Wi-Fi credentials, brightness, routes, stop, and directions for owner editing.

#### Scenario: Initial config load
- **WHEN** `/` is requested with GET
- **THEN** the app renders `templates/index.html` with the current canonical JSON owner-editable values

#### Scenario: Settings save
- **WHEN** an authenticated `/` POST supplies owner-editable values
- **THEN** the app validates and atomically writes those values to canonical JSON while preserving deployment-managed values

### Requirement: Factory Reset Restores Default Config and Restarts Display Service
The web control plane SHALL restore the installed default template, clear Wi-Fi credentials, and return the device to AP onboarding when `/reset` is invoked by an authenticated user.

#### Scenario: Reset success
- **WHEN** `/reset` receives an authenticated POST and the default file exists
- **THEN** it saves default configuration with empty Wi-Fi credentials and starts AP onboarding services

#### Scenario: Reset missing default
- **WHEN** `/reset` receives POST and the default file is missing
- **THEN** it returns HTTP 500 with an error message