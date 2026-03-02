## Why
Current route rendering relies on limited BDF glyph coverage and cannot easily support all route variants or richer visuals. We need a rendering strategy that supports image-based or abstracted symbol drawing while preserving performance on Pi hardware.

## What Changes
- Introduce a rendering abstraction layer for route symbols.
- Define strategy for image/glyph asset selection with fallback behavior.
- Standardize on `louh/mta-subway-bullets` as the upstream bullet asset source and preprocess into local runtime assets.
- Require all symbol assets to be vendored in-repo; no runtime or startup network retrieval of symbol assets is allowed.
- Preserve existing text and timing rendering while modernizing route symbol pipeline.

## Capabilities

### New Capabilities
- `route-symbol-rendering`: Abstraction for rendering route symbols from pluggable sources.

### Modified Capabilities
- `display-runtime`: Route symbol rendering path updated from direct font dependency to strategy-based rendering.

## Impact
- Affected modules: `python/main.py`, `python/display.py`, and font/image assets.
- Potential memory/performance impact on constrained hardware.

## Implementation notes
- Any rendering backend changes must preserve 2 Hz refresh and avoid requiring additional root privileges.
- Fallback rendering for unsupported symbols must be deterministic.
- Validate frame timing and visual quality on Pi hardware, not just desktop emulation.
- Route ID normalization MUST support feed variants (`5X`, `6X`, `7X`, `FS`, `FX`, `GS`, `SI`) via alias mapping before image lookup.
- Third-party asset provenance and license/attribution references MUST be stored in-repo alongside symbol assets.
