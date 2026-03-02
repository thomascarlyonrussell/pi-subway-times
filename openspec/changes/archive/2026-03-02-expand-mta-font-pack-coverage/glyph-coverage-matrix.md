# Glyph Coverage Matrix

This matrix is canonical for `expand-mta-font-pack-coverage` and tracks route-symbol coverage for all route IDs currently emitted by `Trips.MTA_FEEDS`.

Baseline date: `2026-03-02`

| Route ID | Canonical Symbol Key | Batch | Baseline Status | Target Render Path | Notes |
|---|---|---|---|---|---|
| 1 | 1 | Batch 1: Numbered Trunks | Pending | image -> font -> text |  |
| 2 | 2 | Batch 1: Numbered Trunks | Pending | image -> font -> text |  |
| 3 | 3 | Batch 1: Numbered Trunks | Pending | image -> font -> text |  |
| 4 | 4 | Batch 1: Numbered Trunks | Pending | image -> font -> text |  |
| 5 | 5 | Batch 1: Numbered Trunks | Pending | image -> font -> text |  |
| 5X | 5D | Batch 1: Numbered Trunks | Pending | image -> font -> text | Express variant alias |
| 6 | 6 | Batch 1: Numbered Trunks | Pending | image -> font -> text |  |
| 6X | 6D | Batch 1: Numbered Trunks | Pending | image -> font -> text | Express variant alias |
| 7 | 7 | Batch 1: Numbered Trunks | Pending | image -> font -> text |  |
| 7X | 7D | Batch 1: Numbered Trunks | Pending | image -> font -> text | Express variant alias |
| A | A | Batch 2: Core Lettered | Pending | image -> font -> text |  |
| B | B | Batch 2: Core Lettered | Pending | image -> font -> text |  |
| C | C | Batch 2: Core Lettered | Pending | image -> font -> text |  |
| D | D | Batch 2: Core Lettered | Pending | image -> font -> text |  |
| E | E | Batch 2: Core Lettered | Pending | image -> font -> text |  |
| F | F | Batch 2: Core Lettered | Supported (font) | image -> font -> text | Present in `fonts/mta.bdf` |
| G | G | Batch 2: Core Lettered | Supported (font) | image -> font -> text | Present in `fonts/mta.bdf` |
| J | J | Batch 3: Remaining Lettered | Pending | image -> font -> text |  |
| L | L | Batch 3: Remaining Lettered | Pending | image -> font -> text |  |
| M | M | Batch 3: Remaining Lettered | Pending | image -> font -> text |  |
| N | N | Batch 3: Remaining Lettered | Pending | image -> font -> text |  |
| Q | Q | Batch 3: Remaining Lettered | Pending | image -> font -> text |  |
| R | R | Batch 3: Remaining Lettered | Pending | image -> font -> text |  |
| W | W | Batch 3: Remaining Lettered | Pending | image -> font -> text |  |
| Z | Z | Batch 3: Remaining Lettered | Pending | image -> font -> text |  |
| FS | SF | Batch 4: Shuttle and Special | Pending | image -> font -> text | Franklin Shuttle alias |
| FX | FD | Batch 4: Shuttle and Special | Pending | image -> font -> text | F-express alias |
| GS | S | Batch 4: Shuttle and Special | Pending | image -> font -> text | 42nd St shuttle alias |
| SI | SIR | Batch 4: Shuttle and Special | Pending | image -> font -> text | Staten Island Railway alias |

## Batch Acceptance Rule

A batch is complete only when:
- Every route ID in the batch resolves to a supported symbol key.
- Renderer output is visually verified on target hardware.
- Regression checks pass for already-supported routes.
