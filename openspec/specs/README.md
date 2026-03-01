# OpenSpec Baseline Specs

This baseline documents the current, as-implemented behavior of the project as of 2026-03-01.

## Capabilities

- `config-contracts`: Defines active configuration sources and current TOML/JSON drift.
- `trip-data-pipeline`: Defines static GTFS + realtime feed parsing, filtering, and retry behavior.
- `display-runtime`: Defines polling cadence, render cadence, matrix layout, and fatal error behavior.
- `web-config-control-plane`: Defines Flask config UI behavior, persistence model, and service controls.
- `provisioning-and-runtime-ops`: Defines setup script behavior, systemd/runtime operations, and host prerequisites.

## Dependency Order

1. `config-contracts`
2. `trip-data-pipeline`
3. `display-runtime`
4. `web-config-control-plane`
5. `provisioning-and-runtime-ops`

## Follow-Up Change Candidates

- Unify configuration source of truth (`settings.toml` vs matrix JSON paths).
- Add authentication/authorization for web configuration endpoints.
- Add robust display fallback behavior when trip fetch returns `None`.
- Add test harnesses for parser and route/station selection behavior.
- Refresh static GTFS data dynamically instead of relying on checked-in snapshots.
