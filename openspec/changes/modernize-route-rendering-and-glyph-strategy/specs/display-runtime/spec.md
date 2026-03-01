## MODIFIED Requirements

### Requirement: Display Uses Route Color and Direction Truncation
The display runtime MUST render route symbols through a route-symbol rendering strategy that supports multiple backend types and deterministic fallback behavior.

#### Scenario: Primary symbol backend available
- **WHEN** selected backend has symbol asset for route
- **THEN** the display draws route symbol using selected backend and existing color rules

#### Scenario: Primary symbol backend missing asset
- **WHEN** selected backend lacks requested symbol
- **THEN** fallback backend or textual route rendering is used without crashing render loop

### Requirement: Runtime Error Handling Is Fatal
The display runtime MUST isolate symbol-rendering backend errors and continue rendering with fallback when feasible.

#### Scenario: Backend-specific render error
- **WHEN** backend render call fails for a symbol
- **THEN** runtime logs error context and uses configured fallback path for that frame