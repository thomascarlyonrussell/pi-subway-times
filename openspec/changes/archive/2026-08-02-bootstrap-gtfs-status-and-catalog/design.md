## Context

The initial GTFS refresh takes roughly 284 seconds on a Pi Zero 2 W. The largest cost is merging and retaining `stop_times.txt`, although the live arrival display only reads `stops.txt`, `trips.txt`, and `routes.txt`. First provisioning performs this work before the display service starts, leaving the physical matrix blank. A scheduled refresh runs while the display already owns the matrix and must not contend for GPIO access.

## Goals / Non-Goals

**Goals:**
- Give a local installer progress and failure feedback on the LED matrix when a usable snapshot is absent.
- Reduce promoted snapshot size and initial refresh work by generating compact discovery data instead of retaining unused source files.
- Make startup conditional: valid snapshots start arrivals immediately; missing snapshots visibly bootstrap first.
- Preserve supplement precedence, atomic promotion, rollback, and transition-safe trip lookup.

**Non-Goals:**
- Show static-refresh progress during regular scheduled refreshes.
- Redesign the live arrival display or its layout.
- Retain full GTFS geometry or stop-time schedules for offline itinerary planning.

## Decisions

### A compact JSON catalog replaces runtime `stop_times.txt` discovery

Each promoted snapshot will include `discovery_catalog.json` containing the route metadata and station records the Flask UI returns. Refresh streams trips and both source stop-time files to create stop-to-route mappings, then combines them with merged stops and routes. This removes the runtime full-file load and permits `stop_times.txt` plus `shapes.txt` to be excluded from snapshots.

The catalog is generated before `current.json` moves, so old snapshots stay complete and failed candidates cannot affect discovery. A refresh is required once after deployment to migrate an existing device. Retaining the original full files was rejected because it costs more than three minutes on this Pi for data that the application does not use after setup.

### Bootstrap owns the matrix only before the sign starts

`gtfs-bootstrap.service` runs a refresh in board-status mode only when no valid `current.json` points to a snapshot that contains required lookup files and the discovery catalog. The status renderer receives phase/progress events and renders a compact screen using existing matrix settings and font assets. It owns the matrix for the duration, then releases it in `finally`.

`subway-sign.service` orders after and requires the bootstrap service. A condition skips bootstrap when a valid snapshot exists, allowing normal boots to start arrivals immediately. Scheduled refresh stays headless and continues to restart the sign only after a successful promotion. A concurrent renderer or a status overlay inside `main.py` was rejected because two processes would contend for the LED hardware and a scheduled refresh must not hide arrivals.

### Status is phase-oriented and bounded

The screen reports `SETUP`, `DOWNLOAD`, `UNPACK`, `STATIONS`, and `FINALIZE`; archive bytes drive determinate progress where totals are available, while catalog processing uses record counts. On failure, it displays `SETUP FAILED` and a short terminal/log recovery hint. It does not promise an ETA because network and SD-card behavior vary widely on the Pi Zero.

### Provisioning installs matrix support before bootstrap

The RGB Matrix installer moves before the first snapshot refresh. The setup script delegates bootstrap to systemd after units are written, avoiding a hidden inline refresh and giving the status renderer a working driver. A controlled upgrade documents how to install the units and trigger bootstrap without running the full provisioning script.

## Risks / Trade-offs

- [Existing snapshots lack a catalog] -> Bootstrap treats them as invalid only when explicitly invoked; deployment instructions run one refresh before enabling the new dependency.
- [Catalog generation still scans source stop times] -> It eliminates expensive merged output, append, hashing, retention, and future UI reloads; streaming keeps memory bounded.
- [Matrix initialization fails during bootstrap] -> Refresh continues with console/journal output and reports failure through systemd; a valid existing snapshot still bypasses bootstrap.
- [User powers off mid-bootstrap] -> `current.json` remains untouched until candidate validation succeeds, so the next boot retries safely.
- [Status text is constrained by 64x32 pixels] -> Use terse phase labels and a progress bar instead of detailed diagnostics.

## Migration Plan

1. Deploy code and systemd unit changes while retaining the current snapshot.
2. Run a headless forced refresh once to create `discovery_catalog.json`.
3. Enable the bootstrap dependency and reboot; it skips because the new snapshot is valid.
4. For rollback, disable the bootstrap unit dependency and restore the prior code. Existing snapshots remain untouched; refresh can recreate the catalog when code is restored.

## Open Questions

- None for the first implementation. Hardware brightness and exact status wording will be verified on the Pi.