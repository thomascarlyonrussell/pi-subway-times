## Context
TODO.md contains completed items that currently rely on implicit trust rather than explicit acceptance criteria. This change introduces a formal audit layer without changing runtime code.

## Goals / Non-Goals

**Goals:**
- Define repeatable audit criteria for completed TODO items.
- Capture evidence expectations and closure status in OpenSpec artifacts.
- Surface partial-completion risks before dependent changes begin.

**Non-Goals:**
- Implementing new runtime features.
- Refactoring display, web, or setup scripts.

## Decisions
- Create a dedicated `baseline-audit` capability instead of folding checks into unrelated changes.
- Treat completed TODOs as "verified" only when code-path, service/runtime effect, and manual check evidence all exist.
- Keep audit output lightweight: requirement scenarios plus checklist tasks.

## Risks / Trade-offs
- [Risk] Audit may expose regressions and expand scope. → Mitigation: classify findings as follow-on changes, do not block unrelated work unless high severity.
- [Risk] Dev-box-only validation can misrepresent Pi behavior. → Mitigation: require explicit hardware verification notes in tasks.

## Migration Plan
1. Audit completed TODO items using baseline specs.
2. Mark verified vs partially verified outcomes.
3. Convert gaps into new or existing change backlogs.

## Open Questions
- None. Current change is documentation/process scoped.