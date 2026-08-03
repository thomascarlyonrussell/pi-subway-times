## ADDED Requirements

### Requirement: Configuration Discovery Uses Snapshot Catalog Data
The system SHALL serve discoverable routes and stops from the active snapshot's compact discovery catalog without loading static `stop_times.txt` at request time.

#### Scenario: Discover routes and stops after refresh
- **WHEN** the active snapshot contains a valid discovery catalog
- **THEN** configuration discovery SHALL return route, stop, route-filter, and direction-filter results from that catalog

#### Scenario: Missing catalog
- **WHEN** configuration discovery is requested from a snapshot without a discovery catalog
- **THEN** the system SHALL fail with a message directing the operator to run a GTFS refresh