## Context
Current setup flow exposes configuration endpoints without auth and performs privileged network operations from web handlers. WiFi credentials and AP transitions need hardened controls.

## Goals / Non-Goals

**Goals:**
- Require authenticated access for onboarding and config mutation endpoints.
- Protect WiFi credentials at rest/in transit/logging.
- Make AP lifecycle deterministic with safe recovery paths.

**Non-Goals:**
- Building a full enterprise identity system.
- Replacing all system networking primitives.

## Decisions
- Require setup-session authentication before sensitive operations.
- Store credentials encrypted or OS-protected; never log raw secrets.
- Separate privileged network operations behind controlled command boundary.
- Define AP timeout and fallback strategy to avoid permanent AP or lockout states.

## Risks / Trade-offs
- [Risk] Stronger auth may increase setup friction. → Mitigation: guided first-boot pairing flow.
- [Risk] Misconfigured network transitions can brick remote access. → Mitigation: rollback timer and AP recovery mode.

## Migration Plan
1. Introduce auth/session guardrails for sensitive endpoints.
2. Harden credential handling and logging policies.
3. Implement AP transition state machine and recovery paths.

## Open Questions
- Preferred first-boot auth mechanism (PIN, generated token, or local-only temporary password).