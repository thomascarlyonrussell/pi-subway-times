## ADDED Requirements

### Requirement: Missing GTFS Data Has a Visual Bootstrap State
The system SHALL render a setup status on the LED matrix when startup requires creation of an active GTFS snapshot.

#### Scenario: First startup without a snapshot
- **WHEN** no valid active GTFS snapshot exists during startup
- **THEN** the bootstrap process SHALL render setup phases and progress until refresh succeeds or fails

#### Scenario: Bootstrap failure
- **WHEN** initial GTFS refresh fails
- **THEN** the bootstrap process SHALL retain a failure status on the matrix and SHALL not start the live arrival display

### Requirement: Bootstrap and Live Display Have Exclusive Matrix Ownership
The system SHALL ensure that bootstrap status rendering and the live arrival display do not access the LED matrix concurrently.

#### Scenario: Bootstrap succeeds
- **WHEN** a bootstrap refresh promotes a valid snapshot
- **THEN** the bootstrap renderer SHALL release the matrix before the live display service starts

#### Scenario: Scheduled refresh with active display
- **WHEN** scheduled GTFS refresh runs while a valid snapshot exists
- **THEN** the refresh SHALL not render bootstrap status or take ownership of the LED matrix