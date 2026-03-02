# route-stop-discovery Specification

## Purpose
TBD - created by archiving change add-stop-and-line-discovery-in-config-ui. Update Purpose after archive.
## Requirements
### Requirement: Configuration Flow Must Provide Discoverable Route Options
The system MUST provide a route discovery interface that lists selectable routes supported by current transit data.

#### Scenario: Route list retrieval
- **WHEN** the config UI requests available routes
- **THEN** the system returns a normalized route list usable for user selection

### Requirement: Stop Options Must Be Filtered by Selected Context
The system MUST provide stop options filtered by selected route and direction context.

#### Scenario: Filtered stops retrieval
- **WHEN** a user selects route and direction
- **THEN** only compatible stops are returned for selection

### Requirement: Invalid Route or Stop Inputs Must Be Rejected
The system MUST reject persistence attempts for unsupported or mismatched route and stop combinations.

#### Scenario: Invalid route and stop combination
- **WHEN** a save request includes a stop not compatible with selected route or direction
- **THEN** the save is rejected with validation error details

