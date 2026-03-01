## Purpose
Define the current provisioning and runtime-operations behavior from the setup script and service-management flows, including known path and privilege mismatches.

## Requirements
### Requirement: Setup Script Provisions Host Dependencies and Project Checkout
Provisioning SHALL update apt packages, install required system packages, ensure project directory exists, and clone or pull repository content.

#### Scenario: First-time host setup
- **WHEN** `setup/setup_subway_sign.sh` runs on a new host
- **THEN** it installs packages, creates `/home/subwaysign/project`, and clones the project repository

#### Scenario: Existing host update
- **WHEN** repository already exists at project directory
- **THEN** setup script performs `git pull origin main`

### Requirement: Setup Script Creates and Enables Runtime Services
Provisioning SHALL create `subway-sign.service` and `web-config.service` systemd units and enable and start both services.

#### Scenario: Display service unit
- **WHEN** setup writes `subway-sign.service`
- **THEN** unit sets working directory to project dir, restart policy always, and runs the display entrypoint as configured in the unit

#### Scenario: Web config service unit
- **WHEN** setup writes `web-config.service`
- **THEN** unit runs `python/web_config.py` under `subwaysign` and is enabled and started

### Requirement: Setup Script Configures Logging and AP Services
Provisioning SHALL prepare shared log file and configure AP-mode host services.

#### Scenario: Log file setup
- **WHEN** setup executes
- **THEN** `/var/log/subway_sign.log` is created if absent and set to mode `666`

#### Scenario: AP mode setup
- **WHEN** setup executes
- **THEN** `/etc/hostapd/hostapd.conf` is written and `hostapd` plus `dnsmasq` are enabled

### Requirement: Setup Script Seeds Matrix Config Defaults
Provisioning SHALL write `/etc/matrix_config_default.json` and copy it to `/etc/matrix_config.json` when active file does not exist.

#### Scenario: Default config bootstrap
- **WHEN** `/etc/matrix_config.json` is missing
- **THEN** setup copies `/etc/matrix_config_default.json` into place as active config

### Requirement: Runtime Operations Include Service Restarts and AP Teardown
Runtime operations SHALL use service restart and stop control for display and network mode transitions.

#### Scenario: Web save operation runtime control
- **WHEN** config UI saves updates
- **THEN** runtime operations include `systemctl restart subway-sign` and AP service stop calls

### Requirement: Known Operational Deviations Are Preserved in Baseline
Baseline ops behavior SHALL preserve existing mismatches for explicit future remediation.

#### Scenario: Service naming and path mismatch
- **WHEN** setup and runtime files are compared
- **THEN** baseline records that setup uses `/etc/matrix_config*.json` while web runtime currently uses `setup/matrix_config*.json`
