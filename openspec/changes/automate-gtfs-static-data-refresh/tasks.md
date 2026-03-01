## 1. Refresh Pipeline Definition

- [ ] 1.1 Implement dual-source static fetch from `google_transit.zip` and `google_transit_supplemented.zip` with staging and checksum/integrity checks.
- [ ] 1.2 Define merge precedence, atomic activation, and previous-snapshot retention policy for transition windows.

## 2. Operational Integration

- [ ] 2.1 Add scheduled refresh trigger aligned to MTA static feed cadence, plus manual forced refresh and logging/alert behavior.
- [ ] 2.2 Define service restart/reload requirements after dataset promotion.

## 3. Verification

- [ ] 3.1 Validate success/failure/rollback and transition-window behavior on dev environment.
- [ ] 3.2 Validate refresh timing, file permissions, and runtime stability on Raspberry Pi hardware.
