## Context
Existing display rendering draws route symbols via a font with incomplete coverage. This constrains support for many routes and blocks richer visual fidelity.

## Goals / Non-Goals

**Goals:**
- Decouple route symbol rendering from single font dependency.
- Support image or alternate glyph sources with consistent API.
- Preserve current display layout and timing constraints.

**Non-Goals:**
- Full redesign of entire display screen layout.
- GPU-accelerated rendering stack.

## Decisions
- Introduce renderer interface with backends (font backend, image backend).
- Add explicit fallback order: preferred asset, alternate glyph, textual fallback.
- Keep frame budget constraints as first-class acceptance criteria.

## Risks / Trade-offs
- [Risk] Image assets increase memory and I/O overhead. → Mitigation: pre-load cache and small optimized assets.
- [Risk] Abstraction adds complexity. → Mitigation: narrow interface and backend conformance tests.

## Migration Plan
1. Add renderer interface and keep current font backend as baseline.
2. Add image backend and fallback policy.
3. Switch runtime to abstraction and validate performance.

## Open Questions
- Preferred image asset format and resolution strategy for 64x32 panel.