## ADDED Requirements

### Requirement: Completed TODOs Must Have Verifiable Evidence
The project MUST require explicit evidence before a completed TODO is considered fully closed in OpenSpec tracking.

#### Scenario: Completed item verification
- **WHEN** a TODO item is marked completed
- **THEN** evidence includes code path confirmation, runtime/system behavior confirmation, and validation notes

### Requirement: Audit Checklist Format Must Be Standardized
The audit process MUST use a consistent checklist format for each completed TODO item.

#### Scenario: Checklist fields are required
- **WHEN** a completed TODO is audited
- **THEN** the record includes code path evidence, runtime/system behavior evidence, manual verification evidence, and outcome classification

### Requirement: Audit Outcome Must Classify Gaps
The audit process MUST classify each completed TODO as verified or partially verified.

#### Scenario: Partial completion detected
- **WHEN** evidence is missing or behavior does not fully match intent
- **THEN** the outcome records a gap and links it to a follow-on change candidate

### Requirement: Audit Must Record Dev-Box and Pi Hardware Status
The audit process MUST explicitly report whether validation was performed on a development box and on Raspberry Pi hardware.

#### Scenario: Environment validation status recorded
- **WHEN** audit evidence is captured
- **THEN** the outcome includes separate status for dev-box checks and Raspberry Pi hardware checks
