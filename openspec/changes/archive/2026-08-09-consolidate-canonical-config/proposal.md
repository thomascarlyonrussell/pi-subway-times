## Why

The sign has one intended runtime configuration but maintains it through TOML compatibility, duplicate JSON templates, an inline provisioning payload, and an incomplete web editor. This causes drift, makes ownership unclear, and can overwrite device-specific settings during provisioning.

## What Changes

- **BREAKING** Remove `settings.toml`, automatic TOML compatibility loading, and the `toml` dependency. Runtime configuration is JSON only.
- Establish `/etc/matrix_config.json` as the sole active device configuration and `/etc/matrix_config_default.json` as its factory-reset template.
- Retain one version-controlled default template and remove the repository's simulated active configuration and setup-script JSON heredoc.
- Restrict the web UI to owner-controlled Wi-Fi, brightness, routes, stop, and directions; preserve deployment-managed settings on every web save.
- Make factory reset erase Wi-Fi credentials and return the device to access-point onboarding.
- Route Wi-Fi management through the shared validated configuration loader.
- Update tests, provisioning, documentation, and current OpenSpec contracts to describe the JSON-only model.

## Capabilities

### New Capabilities

- `canonical-config-ownership`: Defines active configuration ownership, template behavior, and the boundary between owner-editable and deployment-managed settings.

### Modified Capabilities

- `config-contracts`: Removes legacy TOML compatibility and requires canonical JSON loading.
- `web-config-control-plane`: Restricts owner-editable form fields and changes reset to full Wi-Fi onboarding reset.
- `provisioning-and-runtime-ops`: Installs a single default template without overwriting an existing active configuration.

## Impact

- Affected modules: `config.py`, `web_config.py`, `wifi_manager.py`, setup script, UI template, and configuration tests.
- Existing devices with only `settings.toml` must create `/etc/matrix_config.json` before upgrading.
- The web service continues to need write permission to the active configuration; the display service must restart after changes, while full reset must restart AP services.

## Implementation notes

Provisioning continues to create and own `/etc/matrix_config_default.json`, then seeds `/etc/matrix_config.json` only when it is absent. The active file remains writable by the `subwaysign` service account; secrets and the default template must not gain broad write permissions. Standard setting saves restart `subway-sign`; a factory reset returns Wi-Fi services to access-point mode.