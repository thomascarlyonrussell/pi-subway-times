## MODIFIED Requirements

### Requirement: Realtime Trips Are Filtered and Normalized
The trip data pipeline MUST support configurable direction mapping overrides before emitting display direction values.

#### Scenario: Direction override match
- **WHEN** an incoming trip matches a configured direction mapping rule
- **THEN** emitted `direction` uses mapped value instead of default parsed value

#### Scenario: Direction override fallback
- **WHEN** no mapping rule matches
- **THEN** emitted `direction` uses current default mapping behavior

### Requirement: Fetch Retries Use Refresh Delay Backoff
The trip data pipeline MUST support adaptive polling intervals bounded by minimum and maximum refresh constraints.

#### Scenario: Long-horizon arrivals
- **WHEN** nearest arrival exceeds configured long-horizon threshold
- **THEN** next refresh interval increases within configured max bound

#### Scenario: Imminent arrivals
- **WHEN** nearest arrival is within imminent threshold
- **THEN** refresh interval decreases to configured minimum bound

#### Scenario: External realtime cadence bound
- **WHEN** adaptive polling computes next fetch interval
- **THEN** interval respects configured bounds derived from known realtime feed update cadence

### Requirement: Selected Routes Must Resolve to Complete Realtime Feed Groups
The trip data pipeline MUST resolve configured route selections to all required MTA subway GTFS-RT feed groups and poll each selected group.

#### Scenario: Multi-group route selection
- **WHEN** selected routes span multiple feed groups
- **THEN** the pipeline issues feed requests for each corresponding group endpoint
