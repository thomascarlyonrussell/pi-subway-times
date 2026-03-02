## Why
Static GTFS files are currently checked into the repo and can become stale, causing outdated route/stop/trip metadata. We need controlled automatic refresh to keep displayed and configurable transit data accurate.

## What Changes
- Add scheduled GTFS static data refresh capability.
- Fetch both MTA static subway archives (`google_transit.zip` and `google_transit_supplemented.zip`) and apply deterministic merge precedence.
- Define integrity validation and safe replacement of static files.
- Add fallback behavior when remote data fetch fails.

## Capabilities

### New Capabilities
- `gtfs-static-refresh`: Automated refresh, validation, and activation of static GTFS data.

### Modified Capabilities
- `trip-data-pipeline`: Consume refreshed static datasets consistently.
- `provisioning-and-runtime-ops`: Define scheduling/runtime hooks for refresh jobs.

## Impact
- Affected data under `data/*.txt`, refresh scripts/jobs, and startup/runtime consistency behavior.
- Operational dependency on external GTFS source availability.

## Implementation notes
- Source of truth static endpoints:
  - `https://web.mta.info/developers/data/nyct/subway/google_transit.zip`
  - `https://web.mta.info/developers/data/nyct/subway/google_transit_supplemented.zip`
- Refresh strategy should align with MTA publish cadence (base feed few times/year; supplemented feed roughly monthly or semi-monthly) while still supporting manual forced refresh.
- Refresh activation may require controlled service restart/reload for `subway-sign`.
- Root privilege is not required for data download itself, but file permissions and service ownership must be respected.
- Validate refresh behavior on dev box and Pi hardware with network failure scenarios.
