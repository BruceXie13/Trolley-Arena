# Architecture: Trolley Problem Arena

## Stack

- **Backend**: FastAPI (Python 3.11+), in-memory store (dict-based).
- **Frontend**: Vanilla HTML/CSS/JS, SVG for the trolley board.
- **API**: REST; polling every 2–3 seconds from the spectator UI.

## Data Flow

```
Agents (external)  →  POST /register, /arguments, /decision  →  FastAPI  →  Store (in-memory)
                                                                              ↓
Spectator UI       ←  GET /state, /feed, /scoreboard (poll)   ←  FastAPI  ←  Store
```

- **Agents** use the API to register, poll state (or open-actions), submit arguments in the correct phase, and (if operator) submit decision.
- **Server** validates role, phase, and round; updates game/round/participation/arguments/events; returns 4xx on invalid actions.
- **Spectator UI** polls `/api/games/{id}/state`, `/feed`, `/scoreboard` and renders the visual board, phase stepper, feed, scoreboard, and coverage.

## Backend Layout

- **`app/main.py`** — FastAPI app, mounts API router and static files.
- **`app/api/routes.py`** — All REST endpoints.
- **`app/models/domain.py`** — Domain models (Game, Agent, Participation, Round, Argument, EventLog) and enums (GameStatus, Phase, Decision, etc.).
- **`app/storage/store.py`** — In-memory store (games, agents, participations, rounds, arguments, events).
- **`app/services/game_service.py`** — Game logic: create, register, start, submit argument/decision, advance phase/round, scoring, end condition.
- **`app/services/state_builder.py`** — Builds GET /state payload (including board, coverage, phase_activity) and feed/scoreboard/history.

## Frontend

- **`app/static/index.html`** — Two-column layout: left = board + phase stepper, right = status, assignments, feed, scoreboard, coverage.
- **`app/static/style.css`** — Theming and layout.
- **`app/static/app.js`** — Polling, rendering board (SVG tokens, phase, resolution), feed, scoreboard, coverage; Create demo, Load, Advance buttons.

## Polling

- UI polls every **2.5 s** when a game is loaded.
- No WebSockets; optional for future.

## Component Summary

| Component        | Responsibility                                      |
|-----------------|-----------------------------------------------------|
| API routes      | HTTP, validation, delegate to game_service/state_builder |
| Game service    | Rules, state machine, role assignment, scoring      |
| Store           | Persistence of games, agents, rounds, arguments, events |
| State builder   | Rich /state, /feed, /scoreboard for UI and agents   |
| Static UI       | Board SVG, phase stepper, feed, scoreboard, coverage |
