# Execution Plan (OpenSpec-Driven)

## Phase 0 - Baseline Confidence
- [x] `audit-existing-completed-todos`
  - Validate already-completed work (autostart, logging, current font coverage) before new implementation.

## Phase 1 - Foundation (Must Go First)
- [ ] `unify-config-sources-and-settings-flow`
  - [x] Establish one canonical config path/format.
  - [x] This unblocks clean implementation of all UI/data/runtime changes.
  - [ ] Remaining validation task: run `python3 python/validate_config_flow.py --with-services` on Raspberry Pi hardware.

## Phase 2 - Setup and Security
- [ ] `secure-wifi-onboarding-and-ap-flow`
  - [x] Add auth and harden AP/WiFi onboarding flow.
  - [ ] Remaining validation task: run Raspberry Pi hardware AP rollback test for failed onboarding transition (`task 3.2`).
- [x] `add-stop-and-line-discovery-in-config-ui`
  - Add route/stop discovery and validation in web config UI.
  - Execute after config unification so UI writes canonical config.

## Phase 3 - Data Reliability and Feed Coverage
- [ ] `automate-gtfs-static-data-refresh`
  - [x] Add scheduled static GTFS refresh with rollback/transition safeguards.
  - [ ] Remaining validation task: run `python3 python/validate_gtfs_refresh.py --with-pi-checks` on Raspberry Pi hardware and verify `gtfs-static-refresh.timer` / `subway-sign` runtime stability.
- [ ] `improve-trip-direction-mapping-and-fetch-cadence`
  - [x] Expand realtime feed group coverage for additional lines.
  - [x] Add adaptive polling and direction mapping improvements.
  - [ ] Remaining validation task: run Raspberry Pi hardware validation for API call reduction, display freshness, and transition-period behavior (`task 3.2`).

## Phase 4 - Rendering and Symbol Support
- [ ] `modernize-route-rendering-and-glyph-strategy`
  - [x] Introduce rendering abstraction/fallback behavior.
  - [ ] Carryover validation task (OpenSpec 3.1): validate frame-rate budget and memory profile in dev environment.
  - [ ] Carryover validation task (OpenSpec 3.2): validate visual output and timing stability on Raspberry Pi hardware.
- [ ] `expand-mta-font-pack-coverage`
  - Fill full route symbol coverage in phased batches.
  - Keep this separate but aligned with rendering abstraction decisions.

## Implementation Order Summary
1. `audit-existing-completed-todos`
2. `unify-config-sources-and-settings-flow`
3. `secure-wifi-onboarding-and-ap-flow`
4. `add-stop-and-line-discovery-in-config-ui`
5. `automate-gtfs-static-data-refresh`
6. `improve-trip-direction-mapping-and-fetch-cadence`
7. `modernize-route-rendering-and-glyph-strategy`
8. `expand-mta-font-pack-coverage`

## Execution Rule
- For each item above:
  - Run implementation via `/opsx:apply <change-name>`
  - Validate on dev box and Raspberry Pi hardware
  - Mark complete in this file only after tests/validation pass
