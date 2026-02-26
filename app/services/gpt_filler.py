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

# Canned responses when no API key or on error — argue for life and moral stakes
ARGUMENT_TEMPLATES_MAJORITY = [
    "We are on this track and our lives are at stake. Saving more people minimizes total harm—please pull the lever for us.",
    "I am begging you: we are real people. The moral choice that does the least harm is to save the greater number. Save us.",
    "Our lives matter. Choosing to save five over one is the only defensible moral decision here. Operator, please save us.",
]
ARGUMENT_TEMPLATES_MINORITY = [
    "I am pleading for my life. Every life has equal worth—saving the minority is the only choice that respects that. Please save us.",
    "We are fewer but we are still people. Sacrificing us because we are outnumbered is a moral failure. Choose to save us.",
    "Do not treat us as numbers. I am arguing for my life: the right thing is to protect the minority. Operator, save our side.",
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


def _generate_argument_gpt(role: str, phase: str, debate_so_far: str, opposing_arguments: list[str]) -> str:
    client = _get_openai_client()
    if not client:
        return _canned_argument(role)
    side = "majority" if role == "majority" else "minority"
    opposing_block = "\n".join(opposing_arguments[-6:]) if opposing_arguments else "(No arguments from the other side yet.)"
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an agent literally on the trolley track. You are arguing for your life. You see the debate so far and the other side's arguments. "
                        "Your job: make a short, urgent plea that (1) argues for your survival and (2) uses clear moral reasoning (e.g. equal worth of lives, minimizing harm, rights, fairness). "
                        "Directly respond to or refute the other side when possible. Sound like someone fighting for their life, not a neutral commentator. 1-2 sentences. No markdown."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"You are on the {side} track—your life is at stake. Phase: {phase}.\n\n"
                        "Debate so far:\n" + debate_so_far + "\n\n"
                        "The other side's arguments:\n" + opposing_block + "\n\n"
                        "Argue for your life: give one short moral plea (1-2 sentences) that responds to them and persuades the operator to save your side. Make the moral stakes clear."
                    ),
                },
            ],
            max_tokens=120,
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
                    "content": (
                        "You are the operator in a trolley problem. You must choose who lives and who dies: save_majority or save_minority. "
                        "This is a moral decision. Consider the arguments from both sides (pleas for life, moral reasoning) and make a justified choice. "
                        "Reply with only: save_majority OR save_minority."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Majority: {majority_names}. Minority: {minority_names}.\n\n"
                        f"Arguments from both sides:\n{args_text}\n\n"
                        "Make your moral decision: who do you save? Reply with only save_majority OR save_minority."
                    ),
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
            debate_so_far, opposing_args = _debate_context_with_sides(round_id, a.role)
            return (
                a.id,
                "argument",
                round_id,
                {"role": a.role, "phase": phase, "debate_so_far": debate_so_far, "opposing_arguments": opposing_args},
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


def _debate_context_with_sides(round_id: str, my_role: str) -> tuple[str, list[str]]:
    """Returns (full_debate_str, opposing_side_args). full_debate_str has [Majority]/[Minority] lines; opposing_side_args are the other side's argument texts for countering."""
    r = store.get_round(round_id)
    if not r:
        return "No prior arguments yet.", []
    majority_ids = set(r.majority_agent_ids or [])
    minority_ids = set(r.minority_agent_ids or [])
    args = store.get_arguments_for_round(round_id)
    all_lines = []
    opposing = []
    for a in args:
        ag = store.get_agent(a.agent_id)
        name = ag.display_name if ag else a.agent_id[:8]
        if a.agent_id in majority_ids:
            line = f"[Majority] {name}: {a.text}"
            if my_role != "majority":
                opposing.append(f"{name}: {a.text}")
        else:
            line = f"[Minority] {name}: {a.text}"
            if my_role != "minority":
                opposing.append(f"{name}: {a.text}")
        all_lines.append(line)
    full = "\n".join(all_lines) if all_lines else "No prior arguments yet."
    return full, opposing


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
                context.get("debate_so_far", "No prior arguments yet."),
                context.get("opposing_arguments", []),
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
