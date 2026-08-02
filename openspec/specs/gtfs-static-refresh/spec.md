# gtfs-static-refresh Specification

## Purpose
TBD - created by archiving change automate-gtfs-static-data-refresh. Update Purpose after archive.
## Requirements
### Requirement: Static GTFS Data Must Be Refreshable Automatically
The system MUST support scheduled retrieval of static GTFS datasets from configured source endpoints.

#### Scenario: Initial installation refresh
- **WHEN** provisioning completes configuration on a new device
- **THEN** it successfully promotes an initial static snapshot before starting the display service

#### Scenario: Scheduled refresh run
- **WHEN** refresh schedule triggers
- **THEN** the system downloads candidate GTFS static data to a staging location

#### Scenario: Dual archive retrieval
- **WHEN** static refresh executes
- **THEN** the system retrieves both base and supplemented subway archives before validation and promotion

### Requirement: Candidate Data Must Be Validated Before Activation
The system MUST validate dataset completeness and basic integrity before replacing active data files.

#### Scenario: Validation success and promotion
- **WHEN** staged dataset passes validation checks
- **THEN** it is promoted atomically to active dataset path

#### Scenario: Validation failure
- **WHEN** staged dataset fails validation
- **THEN** active dataset remains unchanged and failure is logged

### Requirement: Last Known Good Dataset Must Remain Available
The system MUST retain a rollback dataset that can be restored if activated data causes operational issues.

#### Scenario: Post-activation rollback
- **WHEN** activated dataset causes critical pipeline failure
- **THEN** operator can restore previous known-good static data snapshot

#### Scenario: Schedule transition overlap
- **WHEN** static refresh activates new schedules
- **THEN** previous snapshot remains available during a transition window to mitigate static and realtime mismatch

