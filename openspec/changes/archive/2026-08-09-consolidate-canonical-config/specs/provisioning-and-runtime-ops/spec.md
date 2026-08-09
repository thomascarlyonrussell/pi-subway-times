## MODIFIED Requirements

### Requirement: Setup Script Seeds Matrix Config Defaults
Provisioning SHALL install `/etc/matrix_config_default.json` from the version-controlled default template and copy it to `/etc/matrix_config.json` only when the active file does not exist.

#### Scenario: Default config bootstrap
- **WHEN** `/etc/matrix_config.json` is missing
- **THEN** setup installs the default template and copies it into place as active config

#### Scenario: Existing active config is preserved
- **WHEN** `/etc/matrix_config.json` exists
- **THEN** setup does not modify its contents