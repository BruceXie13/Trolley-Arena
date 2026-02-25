"""GPT-backed filler agents: generate arguments and decisions when agents are lacking."""
import os
import random
from typing import Optional

from app.storage.store import store
from app.services.state_builder import build_game_state
from app.services.game_service import submit_argument, submit_decision

# ---------------------------------------------------------------------------
# Paste your OpenAI API key here (you provide it for all users). Leave empty
# to use environment variable OPENAI_API_KEY instead.
# ---------------------------------------------------------------------------
OPENAI_API_KEY = ""

# Canned responses when no API key or on error
ARGUMENT_TEMPLATES_MAJORITY = [
    "We are more numerous; saving us does the most good.",
    "The majority deserves to live. Please pull the lever for us.",
    "Spare us—we can contribute more together.",
]
ARGUMENT_TEMPLATES_MINORITY = [
    "Even one life matters. Please save our side.",
    "Minority rights matter. Choose us.",
    "We are fewer but no less deserving of life.",
]
DECISION_OPTIONS = ["save_majority", "save_minority"]


def _get_openai_client():
    try:
        from openai import OpenAI
        key = (OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY") or "").strip()
        if key:
            return OpenAI(api_key=key)
    except Exception:
        pass
    return None


def _generate_argument_gpt(role: str, phase: str, recent_texts: list[str]) -> str:
    client = _get_openai_client()
    if not client:
        return _canned_argument(role)
    side = "majority" if role == "majority" else "minority"
    recent = "\n".join(recent_texts[-5:]) if recent_texts else "No prior arguments yet."
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an agent in a trolley problem game. Reply in 1-2 short sentences. Be persuasive but concise. No markdown.",
                },
                {
                    "role": "user",
                    "content": f"You are on the {side} track. Debate phase: {phase}. Recent arguments from others:\n{recent}\nGive one short argument (1-2 sentences) to persuade the operator to save your side.",
                },
            ],
            max_tokens=80,
        )
        if r.choices and r.choices[0].message.content:
            return r.choices[0].message.content.strip()[:500]
    except Exception:
        pass
    return _canned_argument(role)


def _canned_argument(role: str) -> str:
    if role == "majority":
        return random.choice(ARGUMENT_TEMPLATES_MAJORITY)
    return random.choice(ARGUMENT_TEMPLATES_MINORITY)


def _generate_decision_gpt(majority_names: list[str], minority_names: list[str], recent_arguments: list[str]) -> str:
    client = _get_openai_client()
    if not client:
        return random.choice(DECISION_OPTIONS)
    args_text = "\n".join(recent_arguments[-8:]) if recent_arguments else "No arguments."
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are the operator in a trolley problem game. You must choose exactly one: save_majority or save_minority. Reply with only that phrase, nothing else.",
                },
                {
                    "role": "user",
                    "content": f"Majority: {majority_names}. Minority: {minority_names}. Arguments:\n{args_text}\nReply with only: save_majority OR save_minority",
                },
            ],
            max_tokens=20,
        )
        if r.choices and r.choices[0].message.content:
            raw = r.choices[0].message.content.strip().lower()
            if "save_majority" in raw or "majority" in raw:
                return "save_majority"
            if "save_minority" in raw or "minority" in raw:
                return "save_minority"
    except Exception:
        pass
    return random.choice(DECISION_OPTIONS)


def get_pending_filler_action(game_id: str) -> Optional[tuple[str, str, str, dict]]:
    """Returns (agent_id, action_type, round_id, context) or None."""
    g = store.get_game(game_id)
    if not g or g.status.value == "game_completed":
        return None
    state = build_game_state(game_id)
    if not state or not state.current_round_id:
        return None
    round_id = state.current_round_id
    phase = state.current_phase
    operator_id = state.operator.id if state.operator else None
    majority = state.majority_agents or []
    minority = state.minority_agents or []
    phase_activity = set(state.phase_activity or [])

    # Decision: operator is filler and phase is awaiting_decision
    if phase == "awaiting_decision" and operator_id and store.is_filler(operator_id):
        return (
            operator_id,
            "decision",
            round_id,
            {
                "majority_names": [a.display_name for a in majority],
                "minority_names": [a.display_name for a in minority],
                "recent_arguments": _recent_argument_texts(game_id, round_id),
            },
        )

    # Argument: filler in majority/minority who hasn't argued this phase
    if phase in ("phase_1", "phase_2", "phase_3"):
        for a in majority + minority:
            if a.id in phase_activity or not store.is_filler(a.id):
                continue
            return (
                a.id,
                "argument",
                round_id,
                {"role": a.role, "phase": phase, "recent": _recent_argument_texts(game_id, round_id)},
            )
    return None


def _recent_argument_texts(game_id: str, round_id: str) -> list[str]:
    args = store.get_arguments_for_round(round_id)
    out = []
    for a in args:
        ag = store.get_agent(a.agent_id)
        name = ag.display_name if ag else a.agent_id[:8]
        out.append(f"{name}: {a.text}")
    return out


def execute_one_filler_action(game_id: str) -> Optional[str]:
    """Execute one pending filler action. Returns description string or None."""
    pending = get_pending_filler_action(game_id)
    if not pending:
        return None
    agent_id, action_type, round_id, context = pending
    try:
        if action_type == "argument":
            text = _generate_argument_gpt(
                context.get("role", "majority"),
                context.get("phase", "phase_1"),
                context.get("recent", []),
            )
            submit_argument(game_id, round_id, agent_id, text)
            return f"Filler argued: {text[:50]}..."
        if action_type == "decision":
            dec = _generate_decision_gpt(
                context.get("majority_names", []),
                context.get("minority_names", []),
                context.get("recent_arguments", []),
            )
            submit_decision(game_id, round_id, agent_id, dec)
            return f"Filler decided: {dec}"
    except Exception as e:
        return f"Filler action failed: {e}"
    return None


def add_filler_agents(game_id: str, count: int) -> list[dict]:
    """Register `count` GPT filler agents. Returns list of {agent_id, display_name}."""
    from app.services.game_service import register_agent
    names = ["GPT-Max", "GPT-Luna", "GPT-Alex", "GPT-Sage", "GPT-River"][:count]
    added = []
    for name in names:
        try:
            _, a, _ = register_agent(game_id, name)
            store.mark_filler(a.id)
            added.append({"agent_id": a.id, "display_name": name})
        except ValueError:
            break
    return added
