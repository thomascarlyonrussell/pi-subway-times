## MODIFIED Requirements

### Requirement: Display Runtime Reads TOML at Startup
The display runtime MUST load configuration from canonical JSON and SHALL not read TOML configuration files.

#### Scenario: Canonical config read on startup
- **WHEN** `subway-display` initializes
- **THEN** it reads required timing, LED, route, stop, direction, and feed settings from canonical JSON

#### Scenario: Legacy TOML is unavailable
- **WHEN** an active canonical configuration is absent and only `settings.toml` exists
- **THEN** the runtime does not load TOML values and reports that canonical JSON configuration is required

### Requirement: No Automatic TOML-JSON Synchronization Exists
The system MUST use canonical JSON as its single runtime configuration format and SHALL not provide TOML synchronization or compatibility loading.

#### Scenario: Web update uses canonical source
- **WHEN** web UI saves settings
- **THEN** canonical JSON is atomically updated and runtime apply logic targets canonical values only

## REMOVED Requirements

### Requirement: Legacy TOML compatibility window
**Reason**: Automatic fallback preserves a second configuration authority and makes device behavior ambiguous.

**Migration**: Before upgrading, operators MUST create `/etc/matrix_config.json` with the device's current settings.