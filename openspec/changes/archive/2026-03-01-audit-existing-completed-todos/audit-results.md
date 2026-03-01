## Completed TODO Audit Results

Date: 2026-03-01

## Scope
This audit covers previously completed TODO items referenced by this change:
- Auto-start behavior
- Logging setup
- Font support for `F` and `G`

## Capability Mapping
- Auto-start behavior -> `provisioning-and-runtime-ops`
- Logging setup -> `provisioning-and-runtime-ops`
- `F` and `G` font support -> `display-runtime`

## Evidence Checklist Format
Each audited item must include all of the following:
1. Code path evidence
2. Runtime/system behavior evidence
3. Manual verification evidence (dev-box and Raspberry Pi hardware status)
4. Classification (`verified` or `partially verified`)
5. Follow-on change linkage when partial

## Verification Pass

### Item: Auto-start behavior
- Code path evidence:
  - `setup/setup_subway_sign.sh:56` enables `subway-sign`
  - `setup/setup_subway_sign.sh:57` starts `subway-sign`
  - `setup/setup_subway_sign.sh:76` enables `web-config`
  - `setup/setup_subway_sign.sh:77` starts `web-config`
- Runtime/system behavior evidence:
  - Service units are authored in setup script and include restart policy (`Restart=always`) for both services.
  - Web save path restarts `subway-sign` (`python/web_config.py:89`).
  - Service restart implication: config save impacts display runtime via restart; `web-config` is not restarted by the save path.
- Manual verification evidence:
  - Dev-box: Not executed (no systemd + hardware parity).
  - Raspberry Pi: Not executed in this session.
- Classification: `partially verified`
- Rationale: Static/script evidence exists, but no live service verification output is attached.

### Item: Logging setup
- Code path evidence:
  - Setup creates `/var/log/subway_sign.log` and sets mode `666` (`setup/setup_subway_sign.sh:30-34`).
  - Display runtime logs to file (`python/main.py:8-10`, fatal error logging at `python/main.py:115`).
  - Web config logs to same file (`python/web_config.py:14-19`, `python/web_config.py:22`).
- Runtime/system behavior evidence:
  - Both long-running processes are configured to write to shared log path.
- Manual verification evidence:
  - Dev-box: Not executed.
  - Raspberry Pi: Not executed in this session.
- Classification: `partially verified`
- Rationale: Code confirms intended logging path, but no journal/file runtime evidence captured.

### Item: Font support for `F` and `G`
- Code path evidence:
  - Route font loads from `fonts/mta.bdf` (`python/main.py:64-65`).
  - Route text is rendered from `trip["line"]` using route font (`python/main.py:87`, `python/main.py:94`, `python/main.py:101`).
  - `fonts/mta.bdf` currently declares glyphs `G` and `F` only (`STARTCHAR G`, `STARTCHAR F`).
- Runtime/system behavior evidence:
  - Trip route IDs include `F` and `G` feeds (`python/trips.py:15-16`), so both can flow into route rendering.
  - Limit noted: `mta.bdf` has only two glyphs; unsupported symbols depend on renderer fallback behavior and are out of this completed-item scope.
- Manual verification evidence:
  - Dev-box: No LED matrix rendering validation.
  - Raspberry Pi: Not executed in this session.
- Classification: `partially verified`
- Rationale: Code confirms intended glyph path for `F`/`G`, but no hardware render proof captured.

## Follow-on Changes For Partial Items
- Auto-start + logging operational proof: follow-on candidate `verify-runtime-service-health-and-log-permissions`.
- Config path/service behavior mismatches: covered by existing change `unify-config-sources-and-settings-flow`.
- Route glyph coverage beyond `F`/`G`: covered by existing changes:
  - `modernize-route-rendering-and-glyph-strategy`
  - `expand-mta-font-pack-coverage`

## Test Status Summary
- Dev-box validation: static code/spec audit only; no runtime/service execution.
- Raspberry Pi validation: not performed in this session.
