## Why
WiFi onboarding and AP setup flow currently lacks clear security controls and has high operational risk. We need explicit authentication, credential handling, and AP lifecycle controls to make setup safe and reliable.

## What Changes
- Add authentication and authorization requirements for config and WiFi setup endpoints.
- Define secure credential storage/handling requirements and secret redaction in logs.
- Define robust AP mode entry/exit lifecycle and recovery behavior.

## Capabilities

### New Capabilities
- `wifi-onboarding-security`: Secure WiFi onboarding and AP lifecycle controls.

### Modified Capabilities
- `web-config-control-plane`: Enforce auth and secure handling for setup endpoints.
- `provisioning-and-runtime-ops`: Define AP service lifecycle and startup security defaults.

## Impact
- Affected files include `python/web_config.py`, `python/wifi_manager.py`, and AP-related setup/systemd behavior.
- Potential operational impact on first-boot setup and support workflows.

## Implementation notes
- Any credential application flow that reconfigures WiFi must explicitly describe restart sequencing for `wpa_supplicant`, `hostapd`, `dnsmasq`, and `subway-sign`.
- Preserve least privilege; avoid broad sudo surfaces in web handlers.
- Verify lockout/recovery on actual Pi hardware and not only in dev environment.