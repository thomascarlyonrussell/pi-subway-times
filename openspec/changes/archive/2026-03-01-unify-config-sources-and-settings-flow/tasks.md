## 1. Canonical Config Contract

- [x] 1.1 Define canonical JSON schema and mapping from existing TOML/JSON keys.
- [x] 1.2 Add migration rules and compatibility window definition, including rollback behavior.

## 2. Runtime and Web Integration

- [x] 2.1 Update runtime/web config loaders to use canonical source and shared validation.
- [x] 2.2 Implement save/apply sequence with explicit service restart requirements (`subway-sign`, optional `web-config`).

## 3. Provisioning and Validation

- [x] 3.1 Align setup defaults and file paths with canonical source under `/etc`.
- [ ] 3.2 Validate on dev box and Raspberry Pi hardware, including restart behavior and recovery from invalid config.
  Local validation complete via `python/validate_config_flow.py`; Raspberry Pi validation pending via `python/validate_config_flow.py --with-services`.
