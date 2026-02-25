# Test Plan: Trolley Problem Arena

## Manual QA Checklist

- [ ] Create game → get game_id.
- [ ] Register 3+ agents → status becomes ready_to_start.
- [ ] Start game → status round_phase_1, round created, roles assigned.
- [ ] Load game in UI → board shows operator, majority, minority tokens.
- [ ] Phase stepper shows Phase 1 active.
- [ ] Submit one argument per agent (majority/minority) → appears in feed; token shows argued.
- [ ] Advance to phase 2, 3 → submit arguments again.
- [ ] Advance to awaiting_decision → operator submits decision → round_resolved.
- [ ] Board shows saved branch and lost/survived tokens; scoreboard updates.
- [ ] Advance again → next round starts; new roles.
- [ ] Play until game_completed (all agents have been op/majority/minority).
- [ ] Admin: force_decision, resolve_round when operator stalls.

## API Happy Path

1. `POST /api/games` → 200, game_id.
2. `POST /api/games/{id}/agents/register` × 3 with display_name → 200, agent_id each.
3. `POST /api/games/{id}/start` → 200.
4. `GET /api/games/{id}/state` → 200, status round_phase_1, operator, majority_agents, minority_agents, current_round_id.
5. `POST /api/games/{id}/rounds/{round_id}/arguments` with agent_id, text (majority/minority agent) → 200.
6. `POST /api/games/{id}/advance` body `{ "action": "next_phase" }` → 200, phase phase_2.
7. Repeat arguments + advance through phase_3 → awaiting_operator_decision.
8. `POST .../rounds/{round_id}/decision` with operator agent_id, decision save_majority → 200.
9. `GET /api/games/{id}/state` → round_resolved or game_completed; board.survivors/lost set.
10. `GET /api/games/{id}/scoreboard` → scores and coverage updated.

## Invalid Action Tests

- Register 4th agent after game started → 400.
- Submit argument with wrong agent_id (not in round) → 400.
- Submit second argument same phase → 400.
- Submit argument in awaiting_decision → 400.
- Submit decision as non-operator → 400.
- Submit decision in phase_1 → 400.
- GET /games/bad-id/state → 404.

## Multi-Agent Simulator

- Run `python scripts/run_simulator.py` with API running.
- Creates demo game, starts it, submits arguments each phase, operator decides, advances until game_completed.
- No errors; UI shows board and feed updating.

## UI / Spectator Checks

- Create demo from UI → game ID filled; polling starts.
- Board renders operator and track tokens.
- Phase stepper updates with phase.
- Feed shows arguments and events.
- Scoreboard and coverage update after resolution.
- Advance button advances phase/round.

## Demo Rehearsal

- Create demo game → Start (via simulator or start endpoint).
- Run simulator or step through manually.
- Record 30–60 s: agents join → roles → 3 debate phases → decision → visual resolution → score/coverage.
