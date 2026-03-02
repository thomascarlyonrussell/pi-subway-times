## 1. Security Controls

- [x] 1.1 Define onboarding auth/session requirements and endpoint guard coverage.
- [x] 1.2 Define credential protection and log-redaction rules for WiFi setup paths.

## 2. AP Lifecycle and Privileged Operations

- [x] 2.1 Design AP transition state machine including timeout and rollback behavior.
- [x] 2.2 Isolate privileged network operations and document required service restart sequencing.

## 3. Validation and Recovery Testing

- [x] 3.1 Validate unauthorized access denial and secret redaction in dev environment.
  Executed locally in `.venv`: `python -m unittest python/validate_wifi_onboarding_security.py` (3 tests passing).
- [ ] 3.2 Validate AP recovery and onboarding rollback on Raspberry Pi hardware.
  Added `python/validate_wifi_onboarding_security.py` for dev validation; Raspberry Pi hardware validation still pending.
