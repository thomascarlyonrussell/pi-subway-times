## ADDED Requirements

### Requirement: Completed TODOs Must Have Verifiable Evidence
The project MUST require explicit evidence before a completed TODO is considered fully closed in OpenSpec tracking.

#### Scenario: Completed item verification
- **WHEN** a TODO item is marked completed
- **THEN** evidence includes code path confirmation, runtime/system behavior confirmation, and validation notes

### Requirement: Audit Outcome Must Classify Gaps
The audit process MUST classify each completed TODO as verified or partially verified.

#### Scenario: Partial completion detected
- **WHEN** evidence is missing or behavior does not fully match intent
- **THEN** the outcome records a gap and links it to a follow-on change candidate