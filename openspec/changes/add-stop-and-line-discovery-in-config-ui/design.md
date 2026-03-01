## Context
Current UI requires free-form route and stop text input. Existing GTFS files already contain needed metadata, but it is not exposed in a safe, user-guided flow.

## Goals / Non-Goals

**Goals:**
- Provide route list and filtered stop list to configuration users.
- Prevent invalid route/stop combinations from being saved.
- Keep data flow aligned with canonical config decisions.

**Non-Goals:**
- Replacing the entire web UI design.
- Real-time search across all MTA stations beyond selected routes.

## Decisions
- Add lightweight metadata endpoints for routes and stops consumed by the UI.
- Use existing GTFS static files as source of truth for discovery data.
- Validation occurs server-side before config persistence.

## Risks / Trade-offs
- [Risk] GTFS static data can be stale. → Mitigation: expose source timestamp and combine with static-refresh change.
- [Risk] Larger route/stop lists may impact low-power UI responsiveness. → Mitigation: filter stops by selected routes/direction.

## Migration Plan
1. Introduce discovery endpoints and schema.
2. Update web UI form controls for selectable values.
3. Add validation and settings apply behavior.

## Open Questions
- Whether stop display names should include borough/parent station context.