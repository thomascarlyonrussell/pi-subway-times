## ADDED Requirements

### Requirement: Glyph Coverage Matrix Must Be Explicit
The project MUST maintain an explicit route-symbol coverage matrix for all targeted MTA route IDs.

#### Scenario: Coverage matrix review
- **WHEN** a glyph update is proposed
- **THEN** matrix shows supported, pending, and verified status per route ID

### Requirement: Missing Glyphs Must Have Runtime Fallback
The display system MUST provide fallback rendering when a requested route glyph is not yet supported.

#### Scenario: Unsupported route glyph request
- **WHEN** display requests a glyph not marked supported
- **THEN** system renders fallback symbol or text without render failure

### Requirement: Phased Glyph Rollouts Must Be Verifiable
Each glyph rollout phase MUST include explicit visual verification outcomes for targeted routes.

#### Scenario: Phase completion check
- **WHEN** a glyph batch is marked complete
- **THEN** all batch route IDs have recorded visual verification results on target hardware