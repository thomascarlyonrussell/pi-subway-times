## Why
Route-symbol coverage is incomplete (only a subset is currently confirmed), which causes inconsistent route rendering and blocks broader route support. We need a dedicated, phased glyph coverage plan with acceptance criteria.

## What Changes
- Define full target glyph set for required MTA routes.
- Add phased rollout and verification matrix for glyph support.
- Define fallback behavior for any missing glyphs during rollout.

## Capabilities

### New Capabilities
- `font-glyph-pack`: Managed glyph coverage lifecycle for MTA route symbols.

### Modified Capabilities
- `display-runtime`: Expanded glyph support and fallback behavior for uncovered symbols.

## Impact
- Affected assets include `fonts/mta.bdf` or successor symbol assets and display rendering paths.
- Provides route-by-route acceptance traceability.

## Implementation notes
- Glyph rollout must call out if service restart is required to reload font assets.
- Keep rendering compatibility with root-only LED runtime constraints.
- Verify glyph legibility on real matrix hardware due to low-resolution display limits.