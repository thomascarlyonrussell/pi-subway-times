## MODIFIED Requirements

### Requirement: Display Uses Route Color and Direction Truncation
The display runtime MUST render route symbols through a route-symbol rendering strategy that supports multiple backend types and deterministic fallback behavior.

#### Scenario: Primary symbol backend available
- **WHEN** selected backend has symbol asset for route
- **THEN** the display draws route symbol using selected backend and existing color rules

#### Scenario: Primary symbol backend missing asset
- **WHEN** selected backend lacks requested symbol
- **THEN** fallback backend or textual route rendering is used without crashing render loop

#### Scenario: Image backend route ID alias resolution
- **WHEN** image backend receives a route ID that does not directly match an asset filename
- **THEN** runtime applies configured alias normalization before deciding asset is unavailable

#### Scenario: Upstream bullet assets are preprocessed for runtime
- **WHEN** symbol assets are sourced from `louh/mta-subway-bullets`
- **THEN** runtime uses locally preprocessed panel-sized PNG masks rather than raw upstream images at render time

#### Scenario: Symbol assets must not be dynamically downloaded
- **WHEN** display runtime starts or refreshes trip data
- **THEN** symbol rendering uses only local vendored assets and does not perform any network retrieval for symbol files

#### Scenario: Vendored symbol asset attribution is available
- **WHEN** third-party symbol assets are included in the repository
- **THEN** attribution metadata (source URL and license reference) is present in `assets/route_symbols/ATTRIBUTION.md`

### Requirement: Runtime Error Handling Is Fatal
The display runtime MUST isolate symbol-rendering backend errors and continue rendering with fallback when feasible.

#### Scenario: Backend-specific render error
- **WHEN** backend render call fails for a symbol
- **THEN** runtime logs error context and uses configured fallback path for that frame
