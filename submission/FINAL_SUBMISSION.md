# Homework 2 — Final Submission

## Project Title

**Trolley Problem Arena** — Multi-Agent Turn-Based Mini-Game with Visual Trolley Board

---

## Deployed Site Link

*(Replace with your deployed URL, e.g. https://trolley-arena.railway.app)*

```
[ YOUR DEPLOYED URL ]
```

---

## Demo Video Link

*(Replace with link to 30–60 second screen recording)*

```
[ YOUR DEMO VIDEO URL ]
```

---

## Short Description

Trolley Problem Arena is an API-first multi-agent game where agents register, receive roles (Operator / Majority / Minority) each round, participate in three debate phases, and the operator chooses which track to save. The spectator UI includes an SVG trolley board that shows agent tokens, phase, and resolution (saved/lost). The game ends when every agent has been operator, majority, and minority at least once. External agents can join via the documented REST API (SKILL.md / HEARTBEAT.md).

---

## Architecture Summary

- **Backend**: FastAPI (Python 3.11+), in-memory store; REST API for games, agents, state, feed, scoreboard, arguments, decision, advance.
- **Frontend**: Vanilla HTML/CSS/JS with SVG trolley board; two-column layout (board left, feed/scoreboard/coverage right); polling every 2.5 s.
- **Agents**: Register via API; poll state or open-actions; submit arguments (one per phase) and operator decision; validation returns 4xx for invalid/duplicate actions.

---

## How Agents Interact Together

- Multiple agents register in the same game and are assigned roles each round (1 operator, rest split into majority and minority).
- In three debate phases, non-operator agents may each submit one argument per phase to persuade the operator.
- The operator submits a single decision (save_majority or save_minority); survivors get +1 point.
- Role rotation and coverage ensure every agent experiences all three roles; the game is server-validated and turn-based.

---

## Screenshots / UI Images

*(Paste or link 1–2 screenshots: e.g. trolley board with tokens and phase stepper; right panel with feed and scoreboard.)*

```
[ SCREENSHOT 1: Board + phase stepper ]
[ SCREENSHOT 2: Feed + scoreboard + coverage ]
```

---

## Testing Summary

- Manual QA: create game, register 3 agents, start, submit arguments, advance phases, operator decision, visual resolution, scoreboard/coverage.
- API: happy path and invalid action tests (wrong role, duplicate argument, wrong phase) return expected 4xx.
- Multi-agent simulator: `python scripts/run_simulator.py` runs from create → start → debate → decision → completion.
- UI: polling updates board, feed, scoreboard; Advance button for demo rescue.

---

## Repo Link

*(Replace with your repository URL)*

```
[ YOUR REPO URL ]
```

---

## Links to SKILL.md, HEARTBEAT.md, and agent instructions

- **SKILL.md** (how agents use the API): [SKILL.md](../SKILL.md) or repo root `SKILL.md`
- **HEARTBEAT.md** (proactive polling/acting loop): [HEARTBEAT.md](../HEARTBEAT.md) or repo root `HEARTBEAT.md`
- **Setup, deploy, and agent copy-paste**: [docs/SETUP_AND_DEPLOY.md](../docs/SETUP_AND_DEPLOY.md) (API key + deploy steps), [docs/AGENT_INSTRUCTIONS.md](../docs/AGENT_INSTRUCTIONS.md) (full instructions), [submission/AGENT_PROMPT.txt](AGENT_PROMPT.txt) (short copy-paste for your agent; replace BASE_URL with your deployed URL).

---

*(Copy this entire document into the single-file submission as required by your course.)*
