## MODIFIED Requirements

### Requirement: Display Runtime Reads TOML at Startup
The display runtime MUST load configuration from a canonical JSON source and SHALL support a temporary compatibility read path for legacy TOML during migration.

#### Scenario: Canonical config read on startup
- **WHEN** `python/main.py` initializes after migration
- **THEN** it reads required timing, LED, route, stop, direction, and feed settings from canonical JSON

#### Scenario: Legacy TOML compatibility window
- **WHEN** legacy TOML exists and canonical JSON is absent during migration window
- **THEN** runtime loads compatibility values and logs migration-required warning

### Requirement: No Automatic TOML-JSON Synchronization Exists
The system MUST provide explicit migration and synchronization behavior so configuration state is no longer split across independent TOML and JSON files.

#### Scenario: Web update uses canonical source
- **WHEN** web UI saves settings
- **THEN** canonical config is updated and runtime apply logic targets canonical values only
