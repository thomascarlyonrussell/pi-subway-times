## ADDED Requirements

### Requirement: Sensitive Onboarding Endpoints Must Require Authentication
The system MUST require an authenticated setup session before allowing WiFi or system configuration mutations.

#### Scenario: Unauthenticated mutation request
- **WHEN** a client submits a settings or WiFi update without valid setup authentication
- **THEN** the request is denied

### Requirement: WiFi Credentials Must Be Protected
The system MUST protect WiFi credentials in storage and MUST NOT emit plaintext credentials in logs or API responses.

#### Scenario: Credential persistence and logging
- **WHEN** credentials are stored or applied
- **THEN** persisted values are protected and logs contain no plaintext secrets

### Requirement: AP Lifecycle Must Be Deterministic and Recoverable
The system MUST define AP mode entry, exit, timeout, and rollback behavior for failed onboarding transitions.

#### Scenario: Failed client-network transition
- **WHEN** WiFi apply fails during onboarding
- **THEN** AP mode is restored per recovery policy to preserve local setup access