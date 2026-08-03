## 1. Compact Discovery Snapshot

- [x] 1.1 Generate and validate `discovery_catalog.json` during GTFS refresh while excluding `stop_times.txt` and `shapes.txt` from promoted snapshots.
- [x] 1.2 Load configuration route/stop discovery from the compact catalog and provide a clear migration error for legacy snapshots.
- [x] 1.3 Extend refresh and discovery validation for catalog content, supplement precedence, rollback, and omitted large files.

## 2. Visual Bootstrap Status

- [x] 2.1 Add a bootstrap-only LED matrix status renderer with phase, determinate progress, failure display, and guaranteed resource release.
- [x] 2.2 Publish refresh progress events to the optional bootstrap renderer without changing scheduled-refresh matrix ownership.
- [x] 2.3 Add hardware-independent validation for status phase rendering and matrix release behavior.

## 3. Conditional Startup Operations

- [x] 3.1 Add `gtfs-bootstrap.service` and order `subway-sign.service` to require bootstrap only when no valid snapshot exists.
- [x] 3.2 Reorder provisioning so RGB matrix support is installed before initial bootstrap, and configure service units without conflicting matrix ownership.
- [x] 3.3 Update README and Pi upgrade runbook with first-start phases, recovery behavior, and Pi hardware validation steps.

## 4. End-to-End Verification

- [x] 4.1 Run focused local validations for refresh, discovery, and bootstrap status rendering.
- [ ] 4.2 Run Pi hardware checks: forced missing-snapshot bootstrap, normal boot skip, and scheduled refresh while live arrivals remain visible.