## 1. Canonical JSON Foundation

- [x] 1.1 Make the shared loader JSON-only, centralize path resolution and editable-field ownership, and remove TOML dependency support.
- [x] 1.2 Update focused configuration tests for JSON-only loading, overrides, template fallback, and template validation.

## 2. Configuration Consumers and Onboarding Reset

- [x] 2.1 Refactor web configuration and Wi-Fi management to use shared path/config APIs and preserve deployment-managed values.
- [x] 2.2 Implement authenticated factory reset that clears credentials and restores AP onboarding with mocked regression coverage.
- [x] 2.3 Reduce the web form to owner-editable settings and validate its save behavior on a development machine.

## 3. Provisioning and Repository Cleanup

- [x] 3.1 Remove the repository active config and TOML files, install the default template from setup, and preserve existing device config during provisioning.
- [x] 3.2 Remove the TOML package dependency and update documentation and current OpenSpec contracts for JSON-only operations.

## 4. Validation

- [x] 4.1 Run focused configuration, web, Wi-Fi, and emulator tests.
- [x] 4.2 Run the full pytest suite and record Pi deployment/restart verification requirements.

Pi deployment verification: before upgrading an existing device, create `/etc/matrix_config.json` from its current live settings. On a Pi, rerun provisioning with a customized active config and verify it remains unchanged; then test factory reset to confirm credentials clear, `hostapd` and `dnsmasq` start, and the onboarding UI is reachable.