## Context
Current runtime reads `settings.toml`, while web config writes JSON and setup seeds `/etc` JSON defaults. This produces drift and user-visible confusion when settings changes do not propagate.

## Goals / Non-Goals

**Goals:**
- Establish one canonical configuration source and schema.
- Define compatibility and migration from current TOML/JSON assets.
- Ensure settings updates consistently apply to running services.

**Non-Goals:**
- Redesign of UI/UX forms.
- Feature additions beyond configuration flow.

## Decisions
- Canonical source: JSON at `/etc/matrix_config.json` (service-accessible and already used by setup defaults).
- Runtime modules consume canonical config via a shared loader adapter to avoid duplicated parsing logic.
- TOML retained temporarily as read-only compatibility input during migration window, then deprecated.
- Config writes from web UI are validated and atomically persisted before service apply actions.

## Risks / Trade-offs
- [Risk] Migration can break startup if config file missing/invalid. → Mitigation: fallback to default template + clear error logs.
- [Risk] Service restarts on every save may interrupt display. → Mitigation: minimize restart scope and document when full restart is required.

## Migration Plan
1. Introduce shared config schema/loader and canonical path.
2. Add TOML-to-canonical migration command/path.
3. Switch runtime readers to canonical config.
4. Remove TOML dependency after verification.

## Open Questions
- Whether non-critical settings can be applied without full `subway-sign` restart.