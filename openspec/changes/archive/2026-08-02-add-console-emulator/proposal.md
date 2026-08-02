## Why

Developers currently need Raspberry Pi LED hardware and root-accessible `rgbmatrix` bindings to observe the display runtime. A local console emulator will make it possible to validate a selected configuration against live MTA data, inspect the logical sign output, and observe refresh behavior from a development machine.

## What Changes

- Add a local terminal-based emulator that loads the normal runtime configuration, or an alternate configuration selected through the existing configuration-path mechanism.
- Reuse the production trip-data pipeline to make real MTA feed requests and use its calculated refresh interval.
- Present the logical three-row sign state: the first two arrivals, the rotating third arrival, route, direction, and minutes until arrival.
- Show operational state including selected station/routes/directions, last successful fetch, next-fetch countdown, adaptive interval, stale-data state, and fetch errors.
- Keep the emulator independent of `rgbmatrix`, GPIO access, root permissions, route-symbol graphics, and pixel-perfect LED rendering.
- Preserve the existing physical display entry point and service behavior unchanged.

## Capabilities

### New Capabilities
- `console-emulator`: Run and observe the sign's logical trip display locally in a terminal without LED hardware.

### Modified Capabilities

- None.

## Impact

- Adds a Python development entry point alongside `python/main.py`.
- Reuses `python/config.py` and `python/trips.py`; the emulator must honor the same runtime configuration and adaptive feed cadence as the sign.
- Does not alter the `subway-sign` or `web-config` systemd services, MTA feed API, stored configuration format, or production LED rendering.

## Implementation notes

The emulator is a developer-operated local process and must not require root privileges, GPIO permissions, or a systemd service restart. It must not import or initialize `rgbmatrix`; the existing root-required production display service remains unchanged.