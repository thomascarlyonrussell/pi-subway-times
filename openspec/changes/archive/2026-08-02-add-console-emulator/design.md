## Context

`python/main.py` combines the Raspberry Pi matrix setup, trip-data scheduling, and low-level drawing loop. Its module-level `rgbmatrix` import and matrix initialization prevent developers from exercising the runtime against live MTA feeds on a normal machine. `Trips.fetch_trip_data()` already supplies the display-ready trip fields and calculates `last_refresh_interval_sec`, including adaptive cadence behavior.

The emulator is a development observation tool. It needs to reveal what the sign logically presents, including the selected arrivals and timing state, without claiming to reproduce LED pixels, fonts, symbols, or colors.

## Goals / Non-Goals

**Goals:**
- Provide a local, continuous terminal dashboard using the existing runtime configuration resolution, including `MATRIX_CONFIG_PATH`.
- Invoke `Trips.fetch_trip_data()` and schedule subsequent requests according to its calculated `last_refresh_interval_sec`.
- Preserve the logical row-selection behavior of the production loop: first and second arrival fixed, third arrival rotating through remaining rows on `rotate_trip_delay`.
- Make configuration context, fetch time, remaining interval, freshness, and fetch failures visible.
- Run without `rgbmatrix`, GPIO access, root privileges, or a systemd unit.

**Non-Goals:**
- Emulate the 64x32 pixel buffer, BDF fonts, route-symbol assets, LED colors, brightness, or refresh synchronization.
- Modify `python/main.py`, the physical display service, web configuration UI, stored configuration schema, or MTA API behavior.
- Persist, replay, or expose raw GTFS-Realtime protobuf responses.
- Create a web-based dashboard or configuration editor.

## Decisions

### Standalone console entry point

Add a dedicated Python command beside `main.py` rather than adding an emulator mode to the production entry point. This prevents local execution from reaching the physical driver import path and keeps the hardware runtime free of development-only terminal behavior.

Alternatives considered:
- Add `--emulator` to `main.py`: still requires restructuring module-level driver initialization and combines incompatible runtime concerns.
- Mock `rgbmatrix`: would couple the emulator to drawing implementation details while failing to provide clear logical output.
- Create a Flask dashboard: adds server/UI lifecycle and a dependency surface before the core development feedback loop is proven useful.

### Share the trip pipeline, not the drawing stack

The emulator will load configuration with `load_runtime_config()`, construct `Trips` from the selected feed/display values, and render the returned trip dictionaries as terminal text. It will not import `main.py`, `display.py`, or `route_symbols.py`, because those modules reach `rgbmatrix` directly or are concerned with physical rendering.

This preserves parity with the production data filtering, route selection, direction mapping, and adaptive refresh computation while keeping the tool hardware-independent.

### Reproduce logical scheduling state

The emulator will retain the latest successful result, track the last successful fetch, countdown to the next request, and rotate the third displayed row at the configured `rotate_trip_delay`. It will use the same placeholder-row normalization rule as the runtime when no usable rows are available, and mark retained data as stale when it exceeds `stale_data_grace_sec`.

The terminal UI may redraw more frequently than the production screen loop solely to keep its countdown legible; the frequency of MTA fetches and rotation timing remain governed by production configuration.

### In-place dashboard with durable diagnostics

The command will render a concise frame in place so the current logical sign state is immediately scannable. Fetch failures will remain visible in the frame and be written to standard error so that a shell user can retain diagnostics when redirecting output. This avoids an append-only stream that obscures the current sign state.

Alternatives considered:
- Append-only event log: simple, but makes the current display hard to inspect over time.
- Full terminal UI dependency: richer layout but unnecessary for the initial local tool and potentially awkward on Pi-compatible Python environments.

## Risks / Trade-offs

- [Live feed or static data is unavailable locally] -> Present a visible error/stale state, preserve the last successful logical rows during the configured grace window, and let `Trips` retain its current retry behavior.
- [Terminal dimensions differ] -> Use plain fixed-width text with graceful line wrapping; do not treat layout as a fidelity guarantee.
- [Scheduler logic diverges from `main.py`] -> Keep the emulator scheduler intentionally small, use the same config fields and `Trips.last_refresh_interval_sec`, and cover timing/row selection with focused tests.
- [Console refresh escapes behave poorly in redirected output] -> Detect non-interactive output or offer a non-clearing fallback so process diagnostics remain usable.
- [Users assume it represents physical pixels] -> Label the output as a logical sign preview and omit claims of graphics or color equivalence.

## Migration Plan

1. Add the emulator as an opt-in developer command; no service configuration, deployment step, or production configuration migration is required.
2. Document the local invocation and alternate-config workflow.
3. Rollback consists of removing the new command and its focused tests; no persisted state or running systemd service needs cleanup.

## Open Questions

- None for the initial console-only scope. Raw feed inspection, a web UI, and pixel-level simulation can be proposed separately after local workflow use validates the need.