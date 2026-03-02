## Context
The project currently bundles static GTFS snapshots. Over time these drift from active service patterns and can reduce correctness in both runtime trip interpretation and configuration workflows.

## Goals / Non-Goals

**Goals:**
- Automate periodic GTFS static fetch and validation.
- Ensure only valid datasets are promoted to active use.
- Preserve service continuity under source/network failures.

**Non-Goals:**
- Replacing GTFS-RT feed handling.
- Building a full historical GTFS archive platform.

## Decisions
- Use staged download directory and schema checks before promotion.
- Download and validate both MTA static archives (`google_transit.zip`, `google_transit_supplemented.zip`) and merge with explicit precedence rules (supplemented overrides base on key collisions).
- Activate refreshed data via atomic swap to avoid partial datasets.
- Keep last-known-good snapshot for rollback.
- Preserve prior static snapshot for at least one realtime trip replacement horizon during cutover to reduce static/realtime mismatch risk.

## Risks / Trade-offs
- [Risk] External source downtime causes refresh failure. → Mitigation: keep prior dataset and alert/log failure.
- [Risk] Large file operations can impact low-power device I/O. → Mitigation: off-peak scheduling and staged writes.
- [Risk] Static/realtime mismatch during schedule transitions can produce missing trip joins. → Mitigation: retain previous static snapshot and support dual-snapshot lookup window.

## Migration Plan
1. Add dual-archive fetch workflow and validation pipeline.
2. Add merge and atomic activation logic with previous-snapshot retention.
3. Add scheduler defaults aligned to MTA cadence plus manual refresh command.
4. Roll out with rollback and transition-window safeguards.

## Open Questions
- None.
