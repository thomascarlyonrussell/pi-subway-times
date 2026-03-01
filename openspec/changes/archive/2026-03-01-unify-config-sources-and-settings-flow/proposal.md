## Why
The project currently has split configuration sources (TOML and JSON with path drift), causing settings updates to be inconsistent and hard to reason about. We need one authoritative settings flow to reduce runtime and operational errors.

## What Changes
- Define a single canonical configuration model and file location.
- Introduce deterministic read/write/update flow for display runtime, trips pipeline, and web config UI.
- Define migration and compatibility behavior for existing TOML and JSON files.
- Add explicit runtime reload/service restart semantics after config updates.

## Capabilities

### New Capabilities
- `unified-settings-flow`: Canonical configuration source and synchronization semantics.

### Modified Capabilities
- `config-contracts`: Replace independent TOML/JSON stores with one source of truth.
- `web-config-control-plane`: Update persistence contract and post-save apply behavior.
- `provisioning-and-runtime-ops`: Align setup defaults and runtime config paths.

## Impact
- Affected files: `settings.toml`, `setup/matrix_config.json`, setup scripts, and config-loading code paths.
- Service behavior impact: `subway-sign`/`web-config` restart or reload behavior after writes.

## Implementation notes
- Any path migration affecting `/etc` or service-start assumptions must include explicit restart and rollback instructions.
- Display service root requirements remain unchanged and must be preserved.
- Validate config updates on dev box and actual Pi hardware before cutover.