## Why
Completed TODO items are marked done but are not formally verified against current OpenSpec baselines and runtime behavior. We need an auditable closure pass before additional feature work expands scope.

## What Changes
- Add an audit workflow for completed TODOs (auto-start behavior, logging setup, and currently completed font symbols).
- Define evidence requirements for closing items (code path, runtime/service behavior, and manual validation notes).
- Produce a gap list for any completed TODOs that are only partially satisfied.

## Capabilities

### New Capabilities
- `baseline-audit`: Audit and acceptance workflow for previously completed TODO items.

### Modified Capabilities
- `display-runtime`: Record verified status for completed route-symbol support assumptions.
- `provisioning-and-runtime-ops`: Record verified status for autostart and logging setup behavior.

## Impact
- Affected docs/spec artifacts in `openspec/changes/audit-existing-completed-todos`.
- Affects implementation sequencing by reducing uncertainty before new changes.

## Implementation notes
- Verification must explicitly call out any service restart assumptions (`subway-sign`, `web-config`).
- Root privilege assumptions for LED runtime must be confirmed in acceptance evidence.
- Validation must distinguish dev-box checks from actual Raspberry Pi hardware checks.