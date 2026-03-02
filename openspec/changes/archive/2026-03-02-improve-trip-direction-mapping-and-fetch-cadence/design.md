## Context
Current direction values come directly from static mapping and refresh happens at a fixed interval. This can be inefficient for long arrival horizons and inflexible for route-specific naming.

## Goals / Non-Goals

**Goals:**
- Support custom direction display mapping.
- Reduce unnecessary API calls while preserving display freshness.
- Keep behavior deterministic and observable.

**Non-Goals:**
- Replacing GTFS-RT parser architecture.
- Introducing external caching infrastructure.

## Decisions
- Add rule-based direction mapping with fallback to existing behavior.
- Calculate refresh interval from nearest-trip horizon using bounded min/max intervals.
- Keep fixed hard floor for rapid refresh near imminent arrivals.
- Treat MTA realtime feed cadence (~30-second updates) as an external bound and tune adaptive polling around that cadence.
- Maintain a feed-group resolver that maps selected routes to all required GTFS-RT subway feed endpoints and polls each selected feed group.
- During static schedule transitions, avoid strict trip-id joins that assume stable IDs across feeds; prefer stop-time and route-level matching safeguards.

## Risks / Trade-offs
- [Risk] Over-throttling can show stale results. → Mitigation: enforce strict max staleness interval.
- [Risk] Complex mapping rules can become hard to maintain. → Mitigation: deterministic priority order and validation.
- [Risk] Incomplete feed-group coverage can hide arrivals for some lines. → Mitigation: explicit feed-group map tests for all supported route families.
- [Risk] Static/realtime transition quirks can mislabel or drop trips. → Mitigation: transition-aware matching and fallback labeling.

## Migration Plan
1. Add mapping configuration model and fallback behavior.
2. Implement expanded feed-group resolver for all supported subway route families.
3. Implement adaptive interval algorithm with telemetry/log visibility.
4. Validate cadence transitions and feed coverage under multiple arrival scenarios.

## Open Questions
- Whether mapping should be route-wide or route+stop scoped initially.
