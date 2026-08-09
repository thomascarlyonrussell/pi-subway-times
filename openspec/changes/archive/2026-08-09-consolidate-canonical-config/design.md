## Context

The runtime already centralizes most reads through `load_runtime_config()`, but schema values are duplicated across code, two checked-in JSON files, and an inline shell heredoc. The Flask UI independently resolves paths and exposes an incomplete subset of operational settings. `settings.toml` remains an automatic fallback even though JSON has been documented as canonical.

## Goals / Non-Goals

**Goals:**
- Use canonical JSON for every runtime configuration read and write.
- Establish unambiguous ownership: active config is device state; the template is package/provisioning input.
- Limit web mutation to settings a device owner can safely manage.
- Make factory reset return the device to Wi-Fi onboarding.
- Detect schema/template drift in automated tests.

**Non-Goals:**
- Change display rendering, GTFS behavior, discovery APIs, or hardware driver options.
- Rotate encrypted Wi-Fi keys, setup PINs, or Flask secrets during a factory reset.
- Provide automatic migration for devices that only have TOML.

## Decisions

### JSON-only loader
`config.py` remains the shared source for paths, defaults, normalization, validation, and atomic persistence. TOML parsing and its dependency are removed. An explicit `MATRIX_CONFIG_PATH` is treated as a test/developer override and fails if missing; standard startup may use the installed default template only when the active file is absent.

Automatic TOML fallback was rejected because it leaves an invisible second authority. A migration command was rejected by the product decision to make this a breaking release.

### Template versus active configuration
The repository retains `setup/matrix_config_default.json` as a reviewed provisioning/factory-reset template. It removes `setup/matrix_config.json`; an active configuration belongs only in `/etc` on a provisioned Pi. Setup installs the template and creates active config only when absent, without mutating existing values.

Generating the template dynamically was rejected for now because an inspectable JSON asset is useful to Pi operators. A parity test will enforce that the template validates through the schema.

### Owner-editable web surface
The web form and `_apply_form()` operate only on Wi-Fi credentials, brightness, routes, stop, and directions. Timing, hardware, GTFS refresh, endpoint, and rendering tuning remain preserved values managed through deployment/admin workflows. The field list is exported from `config.py` to avoid separate policy copies.

### Reset transition
Reset loads the default template, clears Wi-Fi credentials, atomically saves active config, clears the client WPA entry, starts AP services, and stops the display as necessary. The behavior belongs in a named `wifi_manager` operation so Flask does not duplicate privileged service calls.

## Risks / Trade-offs

- [Risk] TOML-only installations will fail to load. → Mitigation: document the required `/etc/matrix_config.json` upgrade step prominently.
- [Risk] The web service needs active-config write access. → Mitigation: keep write access scoped to the `subwaysign` account and do not grant it to templates or secrets.
- [Risk] Reset can temporarily make the sign unavailable. → Mitigation: make AP transition explicit, test mocked service order, and return a clear success/failure response.
- [Risk] Code defaults and template can drift. → Mitigation: validate the shipped template in tests.

## Migration Plan

1. Before deploying, create `/etc/matrix_config.json` on every existing device from its current live settings.
2. Deploy the JSON-only release and rerun setup only after confirming it will preserve the active file.
3. Roll back by redeploying the prior release; the canonical JSON file remains usable by its compatibility loader.