## 1. Direction Mapping Design

- [x] 1.1 Define mapping rule schema and fallback precedence for trip direction labels.
- [x] 1.2 Add validation and conflict-handling rules for overlapping direction mappings.

## 2. Adaptive Cadence Logic

- [x] 2.1 Define bounded adaptive interval algorithm tied to nearest arrival horizon and MTA realtime update cadence.
- [x] 2.2 Implement multi-feed resolver and polling for all selected subway feed groups, including URL-encoded feed paths.
- [x] 2.3 Integrate cadence changes with display refresh semantics and stale-data guardrails.

## 3. Verification

- [x] 3.1 Validate mapping correctness, feed-group coverage, and cadence transitions on dev environment scenarios.
- [ ] 3.2 Validate API call reduction, display freshness, and transition-period behavior on Raspberry Pi hardware.
