## Context
Current setup flow exposes configuration endpoints without auth and performs privileged network operations from web handlers. WiFi credentials and AP transitions need hardened controls.

## Goals / Non-Goals

**Goals:**
- Require authenticated access for onboarding and config mutation endpoints.
- Protect WiFi credentials at rest/in transit/logging.
- Make AP lifecycle deterministic with safe recovery paths.

**Non-Goals:**
- Building a full enterprise identity system.
- Replacing all system networking primitives.

## Decisions
- Require setup-session authentication before sensitive operations.
- Store credentials encrypted or OS-protected; never log raw secrets.
- Separate privileged network operations behind controlled command boundary.
- Define AP timeout and fallback strategy to avoid permanent AP or lockout states.

## Auth and Endpoint Guard Coverage
- Session bootstrap endpoint: `POST /auth/login` with onboarding PIN.
- Session status/teardown: `GET /auth/status`, `POST /auth/logout`.
- Guarded endpoints:
  - `POST /` (settings mutation and WiFi apply)
  - `POST /reset` (factory reset)
- Session enforcement:
  - Session cookie with server-side auth marker and timestamp.
  - TTL expiration clears auth state and requires re-login.

## Credential and Logging Controls
- WiFi password handling:
  - Store encrypted credentials in canonical config (`enc:` prefix).
  - Decrypt only at apply time for writing `wpa_supplicant` data.
  - Preserve existing encrypted credential when password field is left blank.
- Redaction policy:
  - Mask keys containing `password`, `psk`, `pin`, `token`, `secret`.
  - Do not render WiFi password in setup UI responses.
- OS-level protections:
  - Key and generated secret/PIN files should be owner-read/write only (`0600`) where possible.

## AP Transition State Machine
- States:
  - `ap_active`
  - `transitioning_to_client`
  - `client_active`
  - `rollback_to_ap`
  - `failed`
- Success path:
  1. Backup current `wpa_supplicant` config.
  2. Write candidate config.
  3. Restart `wpa_supplicant`.
  4. Wait for WiFi association until timeout.
  5. Stop `hostapd` + `dnsmasq`.
  6. Restart `subway-sign` (and optionally `web-config`).
- Failure path:
  1. Restore backup config.
  2. Restart `wpa_supplicant`.
  3. Start `hostapd` + `dnsmasq`.
  4. Return onboarding failure reason for operator visibility.

## Privileged Operation Boundary
- All privileged service actions are routed through a single boundary in `wifi_manager.py`.
- Boundary enforces allowlists for:
  - actions: `start|stop|restart`
  - services: `wpa_supplicant`, `hostapd`, `dnsmasq`, `subway-sign`, `web-config`
- Web handlers do not directly invoke arbitrary `sudo` commands.

## Validation Approach
- Dev validation:
  - Confirm `401` on unauthenticated mutations.
  - Confirm password persistence is encrypted.
  - Confirm redaction utility masks secret-like fields.
- Pi hardware validation:
  - Confirm AP rollback after failed WiFi transition.
  - Confirm successful transition disables AP and restores display service behavior.

## Risks / Trade-offs
- [Risk] Stronger auth may increase setup friction. → Mitigation: guided first-boot pairing flow.
- [Risk] Misconfigured network transitions can brick remote access. → Mitigation: rollback timer and AP recovery mode.

## Migration Plan
1. Introduce auth/session guardrails for sensitive endpoints.
2. Harden credential handling and logging policies.
3. Implement AP transition state machine and recovery paths.

## Open Questions
- Preferred first-boot auth mechanism (PIN, generated token, or local-only temporary password).
