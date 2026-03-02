## Purpose
Define secure WiFi onboarding behavior, including setup authentication, credential protection, and AP lifecycle recovery semantics.

## Requirements
### Requirement: Sensitive Onboarding Endpoints Must Require Authentication
The system MUST require an authenticated setup session before allowing WiFi or system configuration mutations.

#### Scenario: Unauthenticated mutation request
- **WHEN** a client submits a settings or WiFi update without valid setup authentication
- **THEN** the request is denied

#### Scenario: Endpoint guard coverage
- **WHEN** a client calls `POST /` or `POST /reset` without a valid setup session
- **THEN** the server returns `401` and does not persist config or execute privileged network/service operations
- **AND** authentication state is established only by `POST /auth/login` with a valid onboarding PIN
- **AND** sessions expire after a configured TTL

### Requirement: WiFi Credentials Must Be Protected
The system MUST protect WiFi credentials in storage and MUST NOT emit plaintext credentials in logs or API responses.

#### Scenario: Credential persistence and logging
- **WHEN** credentials are stored or applied
- **THEN** persisted values are protected and logs contain no plaintext secrets

#### Scenario: Redaction and response safety
- **WHEN** form payloads or structured request data are logged
- **THEN** fields containing `password`, `psk`, `pin`, `token`, or `secret` are redacted
- **AND** rendered configuration views do not expose stored WiFi password values

### Requirement: AP Lifecycle Must Be Deterministic and Recoverable
The system MUST define AP mode entry, exit, timeout, and rollback behavior for failed onboarding transitions.

#### Scenario: Failed client-network transition
- **WHEN** WiFi apply fails during onboarding
- **THEN** AP mode is restored per recovery policy to preserve local setup access

#### Scenario: Service sequencing during onboarding transition
- **WHEN** onboarding WiFi settings are applied
- **THEN** privileged operations execute through a constrained command boundary with an allowlist of managed services
- **AND** transition sequence is: write candidate WiFi config, restart `wpa_supplicant`, wait for association timeout, stop `hostapd`/`dnsmasq` only on success, then restart `subway-sign` (and optionally `web-config`)
- **AND** on timeout/failure, previous WiFi config is restored and AP services are started
