## Why
Trip direction labeling and polling cadence are currently rigid, which can produce unclear destination labels and unnecessary API calls when arrivals are far away. We need configurable mapping and adaptive fetch behavior.

## What Changes
- Add custom direction mapping rules for displayed trip directions.
- Introduce adaptive polling cadence tied to nearest upcoming arrivals.
- Expand realtime feed selection coverage to support additional line groups beyond current default rider selection.
- Define safeguards to prevent stale display data while reducing network load.

## Capabilities

### New Capabilities
- `adaptive-trip-fetch`: Dynamic trip refresh intervals based on arrival horizon.

### Modified Capabilities
- `trip-data-pipeline`: Direction mapping behavior and fetch cadence logic are updated.
- `display-runtime`: Refresh bar and timing display behavior must remain coherent with adaptive cadence.

## Impact
- Affected modules: `python/trips.py`, `python/main.py`, and config contract keys for mapping/cadence.
- Potentially lower MTA API request volume with bounded freshness guarantees.
- Realtime endpoint handling must support URL-encoded feed paths (for example `nyct%2Fgtfs-ace`) and multi-feed polling.

## Implementation notes
- Adaptive cadence must not violate user expectation for timely updates; define max stale window.
- Base realtime polling assumptions on MTA feed characteristics (approximately 30-second feed updates) and avoid throttling beyond safe freshness windows.
- Expand feed-group map to cover all configured route groups (`gtfs`, `gtfs-ace`, `gtfs-bdfm`, `gtfs-g`, `gtfs-jz`, `gtfs-l`, `gtfs-nqrw`, `gtfs-si`) when those routes are selected.
- Any cadence-related service behavior changes should not require additional privilege escalation.
- Validate low-frequency/high-frequency transitions on both dev box and Pi hardware.
