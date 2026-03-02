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
- Use `louh/mta-subway-bullets` as canonical upstream assets, with checked-in, preprocessed PNG runtime assets under `assets/route_symbols`.
- Normalize route IDs before asset lookup using alias mapping, then fallback to raw normalized route ID.
- Enforce offline-first symbol rendering: no dynamic symbol downloads during runtime, startup, or scheduled jobs.

## Risks / Trade-offs
- [Risk] Image assets increase memory and I/O overhead. → Mitigation: pre-load cache and small optimized assets.
- [Risk] Abstraction adds complexity. → Mitigation: narrow interface and backend conformance tests.
- [Risk] Upstream asset naming differs from GTFS route IDs. → Mitigation: explicit alias map and automated validation report for missing symbols.

## Migration Plan
1. Add renderer interface and keep current font backend as baseline.
2. Add image backend and fallback policy.
3. Add asset preparation workflow that vendors selected upstream bullets into the repo and resizes to panel-friendly dimensions (<=10x10).
4. Switch runtime to abstraction and validate performance.
5. Add in-repo third-party attribution record for vendored symbol assets.

## Asset Normalization Strategy
- Preferred runtime format: monochrome-alpha PNG masks in `assets/route_symbols` with filenames matching normalized route IDs.
- Recommended runtime dimensions: 9x9 or 10x10 pixels to align with existing baseline render positions.
- Asset sourcing policy: vendored local copies only; runtime reads local files only.
- Default alias candidates:
  - `5X -> 5D`
  - `6X -> 6D`
  - `7X -> 7D`
  - `FS -> SF`
  - `FX -> FD`
  - `GS -> S`
  - `SI -> SIR`
- If alias target asset is missing, renderer MUST continue fallback chain (font then text).
