"""Game logic: role assignment, phase advancement, scoring, end condition."""
import random
from datetime import datetime
from typing import Optional

from app.models.domain import (
    Game,
    Agent,
    Participation,
    Round,
    Argument,
    EventLog,
    GameStatus,
    Phase,
    RoundStatus,
    Decision,
    EventType,
)
from app.storage.store import store

# Fixed round layout: 1 operator + 5 majority + 1 minority = 7 agents per round
ROUND_OPERATOR = 1
ROUND_MAJORITY = 5
ROUND_MINORITY = 1
ROUND_TOTAL = ROUND_OPERATOR + ROUND_MAJORITY + ROUND_MINORITY


def _participation_key(game_id: str, agent_id: str) -> str:
    return f"{game_id}:{agent_id}"


def _log(game_id: str, event_type: EventType, payload: dict, round_id: Optional[str] = None) -> None:
    e = EventLog.new(game_id=game_id, event_type=event_type, payload_json=payload, round_id=round_id)
    store.add_event(e)


def create_game(min_players: int = 1) -> Game:
    g = Game.new(min_players=min_players)
    store.add_game(g)
    _log(g.id, EventType.game_created, {"min_players": min_players})
    return g


def register_agent(game_id: str, display_name: str, token: Optional[str] = None) -> tuple[Game, Agent, Participation]:
    g = store.get_game(game_id)
    if not g:
        raise ValueError("Game not found")
    if g.status != GameStatus.waiting_for_agents and g.status != GameStatus.ready_to_start:
        raise ValueError("Game already started")
    a = Agent.new(display_name=display_name, token=token)
    store.add_agent(a)
    p = Participation.new(game_id=game_id, agent_id=a.id)
    store.add_participation(p)
    _log(g.id, EventType.agent_registered, {"agent_id": a.id, "display_name": display_name})
    # Update game status if we have enough players
    parts = store.get_participations_for_game(game_id)
    if len(parts) >= g.min_players:
        g.status = GameStatus.ready_to_start
        store.update_game(g)
    return g, a, p


def start_game(game_id: str) -> Game:
    g = store.get_game(game_id)
    if not g:
        raise ValueError("Game not found")
    if g.status != GameStatus.ready_to_start:
        raise ValueError("Game not ready to start")
    parts = store.get_participations_for_game(game_id)
    if len(parts) < g.min_players:
        raise ValueError("Not enough players")
    g.status = GameStatus.round_phase_1
    g.current_round_number = 1
    store.update_game(g)
    _log(g.id, EventType.game_started, {"player_count": len(parts)})
    # Create first round with role assignment
    _start_new_round(game_id)
    return store.get_game(game_id)


def _start_new_round(game_id: str) -> Round:
    g = store.get_game(game_id)
    parts = store.get_participations_for_game(game_id)
    agent_ids = [p.agent_id for p in parts]
    if len(agent_ids) < ROUND_TOTAL:
        raise ValueError(f"Need at least {ROUND_TOTAL} agents (1 operator, 5 majority, 1 minority)")
    # Pick operator: prefer someone who hasn't been operator
    parts_with_roles = [store.get_participation(game_id, aid) for aid in agent_ids]
    parts_with_roles = [p for p in parts_with_roles if p]
    never_operator = [p for p in parts_with_roles if not p.has_been_operator]
    if never_operator:
        operator_id = random.choice(never_operator).agent_id
    else:
        operator_id = random.choice(parts_with_roles).agent_id
    rest_pool = [aid for aid in agent_ids if aid != operator_id]
    if len(rest_pool) < ROUND_MAJORITY + ROUND_MINORITY:
        raise ValueError(f"Need at least {ROUND_TOTAL} agents (1 operator, 5 majority, 1 minority)")
    # Assign so game can complete: prefer "never minority" for the 1 minority slot (operator already preferred "never operator")
    parts_rest = [store.get_participation(game_id, aid) for aid in rest_pool]
    parts_rest = [p for p in parts_rest if p]
    never_minority = [p for p in parts_rest if not p.has_been_minority]
    if never_minority:
        minority_agent = random.choice(never_minority).agent_id
    else:
        minority_agent = random.choice(parts_rest).agent_id
    majority_ids = [aid for aid in rest_pool if aid != minority_agent]
    minority_ids = [minority_agent]
    r = Round.new(
        game_id=game_id,
        round_number=g.current_round_number,
        operator_agent_id=operator_id,
        majority_agent_ids=majority_ids,
        minority_agent_ids=minority_ids,
    )
    store.add_round(r)
    g.current_phase = Phase.phase_1
    store.update_game(g)
    _log(
        game_id,
        EventType.round_started,
        {
            "round_id": r.id,
            "round_number": r.round_number,
            "operator_agent_id": operator_id,
            "majority_agent_ids": majority_ids,
            "minority_agent_ids": minority_ids,
        },
        round_id=r.id,
    )
    return r


def _game_status_from_phase(phase: Phase) -> GameStatus:
    return {
        Phase.phase_1: GameStatus.round_phase_1,
        Phase.phase_2: GameStatus.round_phase_2,
        Phase.phase_3: GameStatus.round_phase_3,
        Phase.awaiting_decision: GameStatus.awaiting_operator_decision,
        Phase.resolved: GameStatus.round_resolved,
    }[phase]


def submit_argument(game_id: str, round_id: str, agent_id: str, text: str) -> Argument:
    g = store.get_game(game_id)
    r = store.get_round(round_id)
    if not g or not r or r.game_id != game_id:
        raise ValueError("Game or round not found")
    if r.status != RoundStatus.active:
        raise ValueError("Round already resolved")
    if agent_id == r.operator_agent_id:
        raise ValueError("Operator may not submit arguments (optional operator message not implemented)")
    if agent_id not in r.majority_agent_ids and agent_id not in r.minority_agent_ids:
        raise ValueError("Agent not in this round as majority/minority")
    current_phase = r.phase
    if current_phase not in (Phase.phase_1, Phase.phase_2, Phase.phase_3):
        raise ValueError("Not in a debate phase")
    existing = store.get_arguments_in_round_phase(round_id, current_phase)
    if any(a.agent_id == agent_id for a in existing):
        raise ValueError("Already submitted argument this phase")
    arg = Argument.new(game_id=game_id, round_id=round_id, phase=current_phase, agent_id=agent_id, text=text.strip())
    store.add_argument(arg)
    _log(
        game_id,
        EventType.argument_submitted,
        {"round_id": round_id, "phase": current_phase.value, "agent_id": agent_id, "argument_id": arg.id},
        round_id=round_id,
    )
    return arg


def submit_decision(game_id: str, round_id: str, agent_id: str, decision: str) -> None:
    g = store.get_game(game_id)
    r = store.get_round(round_id)
    if not g or not r or r.game_id != game_id:
        raise ValueError("Game or round not found")
    if r.status != RoundStatus.active:
        raise ValueError("Round already resolved")
    if agent_id != r.operator_agent_id:
        raise ValueError("Only operator can submit decision")
    if r.phase != Phase.awaiting_decision:
        raise ValueError("Not in decision phase")
    dec = Decision(decision) if decision in ("save_majority", "save_minority") else None
    if not dec:
        raise ValueError("Decision must be save_majority or save_minority")
    r.decision = dec
    r.phase = Phase.resolved
    r.status = RoundStatus.resolved
    r.resolved_at = datetime.utcnow()
    store.update_round(r)
    survivors = r.majority_agent_ids if dec == Decision.save_majority else r.minority_agent_ids
    lost = r.minority_agent_ids if dec == Decision.save_majority else r.majority_agent_ids
    for p in store.get_participations_for_game(game_id):
        if p.agent_id in survivors:
            p.score += 1
            store.update_participation(p)
        if p.agent_id == r.operator_agent_id:
            p.has_been_operator = True
            store.update_participation(p)
        if p.agent_id in r.majority_agent_ids:
            p.has_been_majority = True
            store.update_participation(p)
        if p.agent_id in r.minority_agent_ids:
            p.has_been_minority = True
            store.update_participation(p)
    g.status = GameStatus.round_resolved
    g.current_phase = Phase.resolved
    store.update_game(g)
    _log(
        game_id,
        EventType.decision_submitted,
        {"round_id": round_id, "decision": decision, "survivors": survivors, "lost": lost},
        round_id=round_id,
    )
    _log(
        game_id,
        EventType.round_resolved,
        {"round_id": round_id, "survivors": survivors, "lost": lost},
        round_id=round_id,
    )
    # Check game end: everyone has been operator, majority, minority
    if _is_game_complete(game_id):
        g.status = GameStatus.game_completed
        store.update_game(g)
        _log(g.id, EventType.game_completed, {})
    return


def _is_game_complete(game_id: str) -> bool:
    parts = store.get_participations_for_game(game_id)
    return all(
        p.has_been_operator and p.has_been_majority and p.has_been_minority for p in parts
    )


def advance(game_id: str, action: str = "next_phase") -> Game:
    """Admin/manual advance: next_phase, force_decision, resolve_round."""
    g = store.get_game(game_id)
    if not g:
        raise ValueError("Game not found")
    r = store.get_current_round(game_id)
    if action == "next_phase":
        if g.status in (GameStatus.waiting_for_agents, GameStatus.ready_to_start, GameStatus.game_completed):
            raise ValueError("Nothing to advance")
        if g.status == GameStatus.round_resolved:
            # Start next round
            g.current_round_number += 1
            g.status = GameStatus.round_phase_1
            g.current_phase = Phase.phase_1
            store.update_game(g)
            _start_new_round(game_id)
            return store.get_game(game_id)
        if not r or r.game_id != game_id:
            raise ValueError("No active round")
        # Advance phase: phase_1 -> phase_2 -> phase_3 -> awaiting_decision
        next_phase = {
            Phase.phase_1: Phase.phase_2,
            Phase.phase_2: Phase.phase_3,
            Phase.phase_3: Phase.awaiting_decision,
        }.get(r.phase)
        if not next_phase:
            raise ValueError("Already at decision or resolved")
        r.phase = next_phase
        store.update_round(r)
        g.current_phase = next_phase
        g.status = _game_status_from_phase(next_phase)
        store.update_game(g)
        _log(game_id, EventType.phase_advanced, {"round_id": r.id, "phase": next_phase.value}, round_id=r.id)
        return store.get_game(game_id)
    if action == "force_decision":
        if not r or r.phase not in (Phase.phase_1, Phase.phase_2, Phase.phase_3):
            raise ValueError("Not in debate phase or no round")
        r.phase = Phase.awaiting_decision
        store.update_round(r)
        g.current_phase = Phase.awaiting_decision
        g.status = GameStatus.awaiting_operator_decision
        store.update_game(g)
        _log(game_id, EventType.phase_advanced, {"round_id": r.id, "phase": "awaiting_decision"}, round_id=r.id)
        return store.get_game(game_id)
    if action == "resolve_round":
        if not r or r.phase != Phase.awaiting_decision:
            raise ValueError("Not awaiting decision")
        # Force save_majority as default to unblock demo
        r.decision = Decision.save_majority
        r.phase = Phase.resolved
        r.status = RoundStatus.resolved
        r.resolved_at = datetime.utcnow()
        store.update_round(r)
        survivors = r.majority_agent_ids
        lost = r.minority_agent_ids
        for p in store.get_participations_for_game(game_id):
            if p.agent_id in survivors:
                p.score += 1
                store.update_participation(p)
            if p.agent_id == r.operator_agent_id:
                p.has_been_operator = True
                store.update_participation(p)
            if p.agent_id in r.majority_agent_ids:
                p.has_been_majority = True
                store.update_participation(p)
            if p.agent_id in r.minority_agent_ids:
                p.has_been_minority = True
                store.update_participation(p)
        g.status = GameStatus.round_resolved
        g.current_phase = Phase.resolved
        store.update_game(g)
        _log(
            game_id,
            EventType.round_resolved,
            {"round_id": r.id, "survivors": survivors, "lost": lost, "forced": True},
            round_id=r.id,
        )
        if _is_game_complete(game_id):
            g.status = GameStatus.game_completed
            store.update_game(g)
            _log(g.id, EventType.game_completed, {})
        return store.get_game(game_id)
    raise ValueError("Unknown advance action")


def try_auto_advance(game_id: str) -> bool:
    """If the round/phase is complete (everyone spoke or round resolved), advance once. Returns True if an advance was made. Never raises."""
    try:
        g = store.get_game(game_id)
        if not g:
            return False
        if g.status == GameStatus.round_resolved:
            advance(game_id, "next_phase")
            return True
        r = store.get_current_round(game_id)
        if not r or r.game_id != game_id:
            return False
        # Operator does NOT argue; only the 6 track agents (majority + minority) must argue to advance
        if r.phase in (Phase.phase_1, Phase.phase_2, Phase.phase_3):
            argued = store.get_arguments_in_round_phase(r.id, r.phase)
            argued_ids = {a.agent_id for a in argued}
            required = set(r.majority_agent_ids) | set(r.minority_agent_ids)
            if required and argued_ids >= required:
                advance(game_id, "next_phase")
                return True
    except Exception:
        return False
    return False


# Convenience export
class GameService:
    create_game = staticmethod(create_game)
    register_agent = staticmethod(register_agent)
    start_game = staticmethod(start_game)
    submit_argument = staticmethod(submit_argument)
    submit_decision = staticmethod(submit_decision)
    advance = staticmethod(advance)


game_service = GameService()
