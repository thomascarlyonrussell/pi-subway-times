## ADDED Requirements

### Requirement: Startup Conditionally Bootstraps GTFS Data
The system SHALL start the live display immediately when a valid active snapshot exists and SHALL complete visual GTFS bootstrap before starting the display when one does not.

#### Scenario: Normal boot with valid snapshot
- **WHEN** the device boots with a valid active snapshot
- **THEN** the live display service SHALL start without running bootstrap refresh

#### Scenario: Recovery boot without valid snapshot
- **WHEN** the device boots without a valid active snapshot
- **THEN** the bootstrap service SHALL refresh data before the live display service starts

### Requirement: Provisioning Enables Visual Initial Bootstrap
The setup process SHALL install the RGB matrix runtime before it starts the initial GTFS refresh.

#### Scenario: New device setup
- **WHEN** provisioning creates the first GTFS snapshot
- **THEN** the bootstrap process SHALL be able to render setup status on the LED matrix