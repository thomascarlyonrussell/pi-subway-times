## 1. Emulator Runtime

- [x] 1.1 Add a standalone console emulator entry point that loads runtime configuration and constructs the existing `Trips` pipeline without importing `rgbmatrix` or physical display modules.
- [x] 1.2 Implement terminal frame rendering for configuration context, three logical arrival rows, refresh interval/countdown, last successful fetch time, freshness state, and fetch errors.
- [x] 1.3 Implement initial fetch, adaptive next-fetch scheduling from `Trips.last_refresh_interval_sec`, third-row rotation from `rotate_trip_delay`, normalized no-data rows, and stale-data handling from `stale_data_grace_sec`.
- [x] 1.4 Support interactive in-place rendering and a non-interactive output fallback without adding third-party terminal UI dependencies.

## 2. Focused Validation

- [x] 2.1 Add focused tests for configuration-path selection, hardware-independent imports, logical row normalization, and rotating third-row selection.
- [x] 2.2 Add focused tests with a stubbed trip pipeline for adaptive scheduling, fetch failure retention, stale-data transition, and diagnostic state rendering.
- [x] 2.3 Run the focused emulator tests on a development machine without Raspberry Pi hardware and correct any regressions.

## 3. Developer Workflow Verification

- [x] 3.1 Document the local invocation, `MATRIX_CONFIG_PATH` alternate-config workflow, expected live-MTA dependency, and console-only fidelity boundary.
- [x] 3.2 Manually run the emulator with the repository development configuration to verify live logical output, countdown updates, and error visibility; do not start or restart systemd services.
- [x] 3.3 Confirm `python/main.py` and the physical display runtime remain unchanged and retain their existing Pi/root requirements.