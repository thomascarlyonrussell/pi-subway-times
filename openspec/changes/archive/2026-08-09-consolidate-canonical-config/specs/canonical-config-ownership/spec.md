## ADDED Requirements

### Requirement: Canonical Configuration Ownership Is Explicit
The system SHALL treat `/etc/matrix_config.json` as the sole active device configuration and `/etc/matrix_config_default.json` as the factory-reset template. The repository SHALL not contain an active device configuration.

#### Scenario: Runtime reads active device state
- **WHEN** a sign service starts without a configuration-path override
- **THEN** it loads `/etc/matrix_config.json` and does not read a repository configuration file as active state

#### Scenario: Provisioning preserves configured device
- **WHEN** provisioning runs on a device with an existing `/etc/matrix_config.json`
- **THEN** it installs the default template without modifying the existing active configuration

### Requirement: Web Settings Have Defined Ownership
The web configuration control plane SHALL permit edits only to Wi-Fi credentials, brightness, routes, stop, and directions, and SHALL preserve all deployment-managed settings during save.

#### Scenario: Owner updates a selected station
- **WHEN** an authenticated owner saves Wi-Fi, brightness, route, stop, or direction values
- **THEN** the active configuration changes only those owner-editable values

#### Scenario: Managed settings survive web save
- **WHEN** the active configuration contains a deployment-managed hardware, timing, feed, rendering, or GTFS refresh value
- **THEN** a web save preserves that value unchanged