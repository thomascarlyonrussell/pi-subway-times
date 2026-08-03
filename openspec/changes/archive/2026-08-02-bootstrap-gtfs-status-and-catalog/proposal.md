## Why

On a Pi Zero 2 W, initial GTFS bootstrap took about 4 minutes 44 seconds, with more than three minutes spent materializing `stop_times.txt` that the live sign never reads. During that first setup, the physical display is blank, leaving a local user unable to tell whether the sign is working or stalled.

## What Changes

- Add a bootstrap-only LED matrix status renderer that communicates initial data setup phases, progress, completion, and actionable failure status.
- Add a conditional systemd bootstrap dependency so the live sign starts immediately when a valid snapshot exists, but waits for visual bootstrap when one is absent.
- Generate a compact discovery catalog for the web configuration UI while refreshing GTFS data.
- Stop storing `stop_times.txt` and `shapes.txt` in promoted snapshots because the live display does not use them.
- Preserve rollback, transition-safe lookup behavior, and headless scheduled refreshes.

## Capabilities

### New Capabilities
- `visual-gtfs-bootstrap`: Board-level feedback and conditional startup orchestration when a GTFS snapshot is unavailable.

### Modified Capabilities
- `gtfs-static-refresh`: Produce a compact discovery artifact and exclude unused large GTFS files from promoted snapshots.
- `route-stop-discovery`: Read route and stop discovery data from the generated compact catalog.
- `provisioning-and-runtime-ops`: Install matrix support before bootstrap and order startup services around conditional GTFS initialization.

## Impact

- Affects `python/gtfs_refresh.py`, `python/trips.py`, new bootstrap renderer code, setup services, README, and the Pi upgrade runbook.
- The bootstrap renderer and display service require root because only one process may own the LED matrix at a time.
- `subway-sign.service` will wait for bootstrap only when no valid active snapshot exists; scheduled refreshes remain headless and restart the display only after promotion.

## Implementation Notes

The RGB-matrix installation must happen before the initial refresh, not afterward. The setup-only renderer must release hardware in all paths before `subway-sign` starts. Existing device configurations retain their snapshot history setting unless explicitly updated; new defaults retain only current and rollback snapshots.