#!/usr/bin/env python3
"""
Multi-agent simulator for Trolley Problem Arena.
Registers 3-5 agents, starts the game, and runs a loop: each agent
submits arguments in debate phases; operator submits decision; advance to next round.
Use when classmates' agents are unavailable. Run with API base URL.

Example:
  python scripts/run_simulator.py
  python scripts/run_simulator.py --base http://localhost:8000
  python scripts/run_simulator.py --base http://localhost:8000 --game-id <existing-game-id>
"""
import argparse
import random
import time
import urllib.request
import urllib.error
import json


def req(base: str, path: str, method: str = "GET", body: dict | None = None) -> dict:
    url = base.rstrip("/") + path
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req_obj = urllib.request.Request(url, data=data, method=method)
    req_obj.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req_obj, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            err = e.read().decode()
            errj = json.loads(err)
            raise RuntimeError(errj.get("detail", err))
        except (ValueError, json.JSONDecodeError):
            raise RuntimeError(f"HTTP {e.code}: {e.reason}")


def main():
    ap = argparse.ArgumentParser(description="Run multi-agent simulator")
    ap.add_argument("--base", default="http://localhost:8000", help="API base URL")
    ap.add_argument("--game-id", default=None, help="Use existing game (otherwise create demo)")
    ap.add_argument("--delay", type=float, default=0.8, help="Delay between actions (seconds)")
    args = ap.parse_args()
    base = args.base

    if args.game_id:
        game_id = args.game_id
        print(f"Using existing game: {game_id}")
        state = req(base, f"/api/games/{game_id}/state")
        if state.get("status") == "ready_to_start":
            req(base, f"/api/games/{game_id}/start", method="POST")
            print("Game started.")
            time.sleep(args.delay)
        score = req(base, f"/api/games/{game_id}/scoreboard")
        agent_ids = [s["agent_id"] for s in score["scores"]]
        names = {s["agent_id"]: s["display_name"] for s in score["scores"]}
    else:
        # Create demo game (3 agents)
        demo = req(base, "/api/demo/create", method="POST")
        game_id = demo["game_id"]
        agents = demo["agents"]
        agent_ids = [a["agent_id"] for a in agents]
        names = {a["agent_id"]: a["display_name"] for a in agents}
        print(f"Created game {game_id} with agents: {list(names.values())}")
        # Start game
        req(base, f"/api/games/{game_id}/start", method="POST")
        print("Game started.")
        time.sleep(args.delay)

    round_count = 0
    while True:
        state = req(base, f"/api/games/{game_id}/state")
        status = state["status"]
        if status == "game_completed":
            print("Game completed.")
            break

        if status == "round_resolved":
            print("Round resolved. Advancing to next round...")
            req(base, f"/api/games/{game_id}/advance", method="POST", body={"action": "next_phase"})
            time.sleep(args.delay)
            continue

        phase = state.get("current_phase") or ""
        round_id = state.get("current_round_id")
        if not round_id:
            req(base, f"/api/games/{game_id}/advance", method="POST", body={"action": "next_phase"})
            time.sleep(args.delay)
            continue

        operator_id = state.get("operator", {}).get("id") if state.get("operator") else None
        majority_ids = [a["id"] for a in state.get("majority_agents", [])]
        minority_ids = [a["id"] for a in state.get("minority_agents", [])]
        phase_activity = set(state.get("phase_activity", []))

        if phase in ("phase_1", "phase_2", "phase_3"):
            # Non-operator agents can submit one argument per phase
            for aid in majority_ids + minority_ids:
                if aid in phase_activity:
                    continue
                name = names.get(aid, aid[:8])
                text = f"[{name}] Please save our side. We deserve to live."
                try:
                    req(
                        base,
                        f"/api/games/{game_id}/rounds/{round_id}/arguments",
                        method="POST",
                        body={"agent_id": aid, "text": text},
                    )
                    print(f"  Argument from {name} (phase {phase})")
                except RuntimeError as e:
                    print(f"  Skip argument {name}: {e}")
                time.sleep(args.delay)
            # Advance to next phase
            req(base, f"/api/games/{game_id}/advance", method="POST", body={"action": "next_phase"})
            print(f"Advanced to next phase (was {phase}).")
            time.sleep(args.delay)

        elif phase == "awaiting_operator_decision":
            if operator_id:
                # Simple policy: alternate save_majority / save_minority for variety
                decision = random.choice(["save_majority", "save_minority"])
                try:
                    req(
                        base,
                        f"/api/games/{game_id}/rounds/{round_id}/decision",
                        method="POST",
                        body={"agent_id": operator_id, "decision": decision},
                    )
                    print(f"  Operator decided: {decision}")
                except RuntimeError as e:
                    print(f"  Decision failed: {e}")
            else:
                req(base, f"/api/games/{game_id}/advance", method="POST", body={"action": "resolve_round"})
                print("  No operator; forced resolve.")
            time.sleep(args.delay)

        else:
            req(base, f"/api/games/{game_id}/advance", method="POST", body={"action": "next_phase"})
            time.sleep(args.delay)
        round_count += 1
        if round_count > 50:
            print("Max rounds reached.")
            break

    print("Simulator done.")


if __name__ == "__main__":
    main()
