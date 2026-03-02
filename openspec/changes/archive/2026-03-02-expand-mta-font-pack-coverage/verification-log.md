# Verification Log

## Fallback Behavior and Acceptance Criteria

Fallback behavior for unsupported symbols:
- Primary: image backend (when matching symbol asset exists).
- Secondary: font backend.
- Final fallback: textual rendering.

Acceptance criteria for unsupported glyph requests:
- Render loop does not crash.
- Route row remains visible with deterministic fallback output.
- Error context is logged when a backend fails.

## Service Restart Requirement

Symbol updates require service restart after any symbol asset change because:
- Image backend builds its asset index at renderer construction time.
- Loaded image masks are cached in-process.
- Font changes (`fonts/mta.bdf`) are loaded at process startup.

Operational requirement:
- Restart `subway-sign` service after asset/font updates before marking batch complete.

## Regression Checks (Task 3.1)

Date: `2026-03-02`

1. Baseline BDF glyph presence
- Command result: `BDF_CHARS=G,F`
- Outcome: pass (existing supported routes remain available in font fallback).

2. Runtime image asset inventory
- Command result: `PNG_COUNT=0`
- Outcome: expected baseline (no vendored runtime symbol set yet; fallback path required).

3. Canonical route universe from feed mapping
- Command result: `ROUTE_COUNT=29`
- Route IDs: `1,2,3,4,5,5X,6,6X,7,7X,A,B,C,D,E,F,FS,FX,G,GS,J,L,M,N,Q,R,SI,W,Z`
- Outcome: pass (matrix route set matches current runtime feed mapping).

## Raspberry Pi Hardware Validation (Task 3.2)

Pending hardware-only checks:
- Verify legibility for each completed batch on real 64x32 panel at deployment brightness.
- Verify unsupported route IDs render deterministic fallback and do not stall frame refresh.
- Verify no visible timing regression after symbol updates and service restart.

Execution note:
- This task remains pending until validation is run on Raspberry Pi hardware.
