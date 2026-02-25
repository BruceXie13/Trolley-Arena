# Visual System: Trolley Board and UI

## Board Layout (ASCII)

```
     [Operator]
          |
    ======*======  ← lever / switch
         / \
        /   \
   MAJORITY  MINORITY
   (track)   (track)
   [A] [B]   [C]      ← agent tokens
```

- **Left**: Incoming track; operator token to the left of the lever.
- **Center**: Lever area (circle); track splits into two branches.
- **Top branch**: Majority track; tokens above.
- **Bottom branch**: Minority track; tokens below.
- **Right**: Labels MAJORITY / MINORITY.

## Rendering

- **SVG** (`app/static/index.html` + `app.js`). ViewBox 520×340.
- Tracks: paths with stroke; default grey, highlight green (saved) or grey (lost) at resolution.
- **Trolley cart**: Simple rectangle + wheels; can stay static or move along chosen branch (current: static).
- **Tokens**: Circles with initials; role-based fill; optional speech bubble when `argued_this_phase`.

## Role Color Mapping

| Role | Fill (hex) | Usage |
|------|------------|--------|
| Operator | `#7c3aed` | Token left of lever. |
| Majority | `#22c55e` | Tokens on top track. |
| Minority | `#ef4444` | Tokens on bottom track. |
| Lost (this round) | `#475569` / grey | Faded token. |
| Argued this phase | Stroke `#fbbf24` or small bubble | Marker on token. |

## Token States

- **Active**: Normal fill and stroke.
- **Argued**: Extra stroke or small circle (speech marker).
- **Survived**: Optional highlight/glow (e.g. green drop-shadow).
- **Lost**: Grey fill, reduced opacity.

## Phase Stepper

- Five steps: Phase 1, Phase 2, Phase 3, Decision, Resolved.
- **Active** step highlighted (e.g. purple).
- **Done** steps dimmed (grey).
- Updates from `state.current_phase`.

## Resolution Behavior

- When `state.decision` is set and `board.selected_branch` is present:
  - Saved branch stroke turns green (majority) or red (minority); other branch grey.
  - Tokens on lost side get `.lost` (grey, faded).
  - Tokens on saved side can get `.survived` (optional glow).
- Resolution text: e.g. "Saved: Majority" near center.
- No heavy animation; CSS transition on opacity/stroke is enough.

## Why This Improves Demo Clarity

- **At a glance**: Viewers see who is on which track and who the operator is.
- **Phase**: Stepper makes it obvious which debate phase or decision is current.
- **Who argued**: Speech marker on tokens shows participation without reading the feed.
- **Outcome**: Saved vs lost is visible on the board and in token state, so the result of each round is clear in 30–60 seconds.
