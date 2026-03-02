## Why
Users currently enter route and stop values manually, which is error-prone and makes configuration difficult for non-technical setup. We need discoverable route/stop options driven from available transit data.

## What Changes
- Add route and stop discovery capability for configuration workflows.
- Define filtering and selection behavior for stops by selected routes and direction.
- Add data validation for selected stop/route values before persistence.

## Capabilities

### New Capabilities
- `route-stop-discovery`: Discoverable route and stop catalog for config workflows.

### Modified Capabilities
- `web-config-control-plane`: Add route/stop selection interfaces and validation flow.
- `trip-data-pipeline`: Expose route/stop metadata in a reusable form for UI consumers.

## Impact
- Affected web templates and web-config endpoints.
- Uses static GTFS data and/or derived metadata from current data files.

## Implementation notes
- Keep service restarts scoped: changing route/stop selections may require `subway-sign` restart.
- Preserve root/permission model; no privilege escalation in UI listing endpoints.
- Validate functionality both on dev box and Pi hardware with real settings apply.