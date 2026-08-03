## ADDED Requirements

### Requirement: Promoted Snapshots Include Compact Discovery Data
The system SHALL generate `discovery_catalog.json` in every promoted GTFS snapshot with route metadata and stop-to-route/direction data required by configuration discovery.

#### Scenario: Candidate promotion
- **WHEN** a candidate GTFS refresh passes validation
- **THEN** its snapshot SHALL contain a valid discovery catalog before `current.json` is updated

### Requirement: Promoted Snapshots Exclude Unused Large Source Files
The system SHALL not retain `stop_times.txt` or `shapes.txt` in a promoted GTFS snapshot.

#### Scenario: Successful refresh
- **WHEN** GTFS refresh promotes a snapshot
- **THEN** the snapshot SHALL retain runtime lookup files and its discovery catalog but SHALL not contain `stop_times.txt` or `shapes.txt`

## MODIFIED Requirements

### Requirement: Candidate Data Must Be Validated Before Activation
The system MUST validate dataset completeness, compact discovery integrity, and basic lookup-file integrity before replacing active data files.

#### Scenario: Validation success and promotion
- **WHEN** staged dataset passes validation
- **THEN** it is promoted atomically to active dataset path

#### Scenario: Validation failure
- **WHEN** staged dataset fails validation
- **THEN** active dataset remains unchanged and failure is logged