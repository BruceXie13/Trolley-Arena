# Demo Script (30–60 Second Screen Recording)

## Goal

Show multiple agents joining, role assignment, three debate phases, operator decision, visual resolution on the trolley board, and score/role coverage update.

## Steps

1. **Start the app**  
   - Run `uvicorn app.main:app --reload --port 8000`.  
   - Open http://localhost:8000.

2. **Create and load a demo game**  
   - Click **Create demo game**.  
   - Game ID appears; click **Load** (or leave as-is if it auto-loads).  
   - Spectator UI shows: status `ready_to_start`, three agents in scoreboard/coverage.

3. **Start the game**  
   - Either run in another terminal:  
     `python scripts/run_simulator.py --base http://localhost:8000`  
   - Or call `POST /api/games/{game_id}/start` (e.g. via /docs).  
   - UI updates: status `round_phase_1`, board shows operator + majority/minority tokens, phase stepper on Phase 1.

4. **Debate phases**  
   - Simulator (or agents) submit arguments; **Advance** to move to Phase 2, then Phase 3.  
   - Point out: phase stepper moving, argued markers on tokens, feed showing arguments.

5. **Operator decision**  
   - Phase becomes **Decision**.  
   - Simulator (or operator agent) submits `save_majority` or `save_minority`.  
   - Board updates: saved branch highlighted, lost side greyed/faded, resolution text.

6. **Score and coverage**  
   - Right panel: scoreboard and role coverage update.  
   - Advance to next round; new roles; repeat once if time allows.

7. **End**  
   - Optional: show game_completed when coverage is complete.

## Talking Points

- “Agents register via the API and get roles each round.”
- “Three debate phases; each non-operator can submit one argument per phase.”
- “The operator decides which track to save; the board shows who survived and who was lost.”
- “The game ends when every agent has been operator, majority, and minority at least once.”

## Fallback

If the simulator is slow, use the **Advance** button to move phases and **resolve_round** (via API docs) if the operator doesn’t act, so the demo still completes.
