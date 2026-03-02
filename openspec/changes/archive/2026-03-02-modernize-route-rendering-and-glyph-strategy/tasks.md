## 1. Rendering Abstraction

- [x] 1.1 Define route-symbol renderer interface and fallback ordering semantics.
- [x] 1.2 Define asset format constraints and caching strategy for low-power hardware.
- [ ] 1.3 Add route ID alias mapping contract for image asset lookup (`5X/6X/7X`, `FS/FX/GS/SI`).

## 2. Runtime Integration

- [x] 2.1 Integrate renderer abstraction into existing display loop without layout regression.
- [x] 2.2 Add backend failure handling and deterministic textual fallback behavior.
- [ ] 2.3 Add/verify image lookup normalization path that applies alias mapping prior to backend resolution.

## 3. Performance and Hardware Validation

- [ ] 3.1 Validate frame-rate budget and memory profile in dev environment.
- [ ] 3.2 Validate visual output and timing stability on Raspberry Pi hardware.

## 4. Upstream Asset Adoption (`louh/mta-subway-bullets`)

- [ ] 4.1 Add documented vendor/process workflow for upstream assets into `assets/route_symbols` (manual/import-time only).
- [ ] 4.2 Resize/quantize selected bullet assets to <=10x10 runtime masks and verify legibility.
- [ ] 4.3 Produce coverage report for all configured feed route IDs and list unresolved symbols.
- [ ] 4.4 Add and maintain `assets/route_symbols/ATTRIBUTION.md` with source repository URL, license, and retrieval date.

## 5. Non-Dynamic Asset Policy

- [ ] 5.1 Ensure no runtime/startup/scheduled code path attempts to download or sync route symbol assets.
