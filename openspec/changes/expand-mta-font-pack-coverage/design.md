## Context
TODO.md includes an extensive unchecked MTA route symbol list. Without a dedicated coverage process, symbol support remains ad hoc and hard to verify.

## Goals / Non-Goals

**Goals:**
- Define required glyph coverage matrix.
- Roll out in phases with clear pass/fail criteria.
- Preserve runtime stability when encountering uncovered symbols.

**Non-Goals:**
- Full rendering-engine redesign (covered by separate rendering strategy change).
- Reworking unrelated display text layout.

## Decisions
- Maintain a canonical glyph matrix document tied to route IDs.
- Ship glyph support in batches (e.g., numbered lines, lettered lines, shuttles/specials).
- Keep fallback for missing symbols until full coverage reached.

## Risks / Trade-offs
- [Risk] Large glyph updates can regress existing symbols. → Mitigation: regression matrix including already working symbols.
- [Risk] Low-resolution legibility differs by hardware brightness/config. → Mitigation: Pi hardware visual acceptance checks.

## Migration Plan
1. Define glyph matrix and baseline status.
2. Implement phased glyph batches with verification.
3. Remove temporary fallbacks only after full matrix pass.

## Open Questions
- Whether alternate stylistic glyph variants should be allowed or fixed to one official style.