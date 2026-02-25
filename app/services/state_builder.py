"""Build GET /state response with full visual payload for UI and agents."""
from datetime import datetime
from typing import Optional

from app.models.domain import Phase, RoundStatus
from app.storage.store import store
from app.schemas.api import (
    GameStateResponse,
    AgentSummary,
    BoardState,
    CoverageProgress,
)


def get_phase_activity(game_id: str, round_id: str, phase: Phase) -> list[str]:
    args = store.get_arguments_in_round_phase(round_id, phase)
    return [a.agent_id for a in args]


def build_game_state(game_id: str, version: int = 0) -> Optional[GameStateResponse]:
    g = store.get_game(game_id)
    if not g:
        return None
    parts = store.get_participations_for_game(game_id)
    scores = {p.agent_id: p.score for p in parts}
    coverage = []
    for p in parts:
        agent = store.get_agent(p.agent_id)
        name = agent.display_name if agent else p.agent_id[:8]
        coverage.append(
            CoverageProgress(
                agent_id=p.agent_id,
                display_name=name,
                has_been_operator=p.has_been_operator,
                has_been_majority=p.has_been_majority,
                has_been_minority=p.has_been_minority,
                complete=p.has_been_operator and p.has_been_majority and p.has_been_minority,
            )
        )
    operator = None
    majority_agents = []
    minority_agents = []
    current_round_id = None
    round_outcome = None
    phase_activity = []
    board = BoardState(animation_version=0)
    last_event_at = None
    events = store.get_events_for_game(game_id, limit=1)
    if events:
        last_event_at = events[0].created_at

    r = store.get_current_round(game_id)
    if r:
        current_round_id = r.id
        op_agent = store.get_agent(r.operator_agent_id)
        operator = AgentSummary(
            id=r.operator_agent_id,
            display_name=op_agent.display_name if op_agent else r.operator_agent_id[:8],
            role="operator",
            argued_this_phase=False,
        )
        for aid in r.majority_agent_ids:
            ag = store.get_agent(aid)
            argued = aid in get_phase_activity(game_id, r.id, r.phase) if r.phase in (
                Phase.phase_1, Phase.phase_2, Phase.phase_3
            ) else False
            majority_agents.append(
                AgentSummary(
                    id=aid,
                    display_name=ag.display_name if ag else aid[:8],
                    role="majority",
                    argued_this_phase=argued,
                )
            )
        for aid in r.minority_agent_ids:
            ag = store.get_agent(aid)
            argued = aid in get_phase_activity(game_id, r.id, r.phase) if r.phase in (
                Phase.phase_1, Phase.phase_2, Phase.phase_3
            ) else False
            minority_agents.append(
                AgentSummary(
                    id=aid,
                    display_name=ag.display_name if ag else aid[:8],
                    role="minority",
                    argued_this_phase=argued,
                )
            )
        if r.phase == Phase.awaiting_decision or r.phase == Phase.resolved:
            phase_activity = get_phase_activity(game_id, r.id, Phase.phase_3)
        elif r.phase == Phase.phase_3:
            phase_activity = get_phase_activity(game_id, r.id, Phase.phase_3)
        elif r.phase == Phase.phase_2:
            phase_activity = get_phase_activity(game_id, r.id, Phase.phase_2)
        else:
            phase_activity = get_phase_activity(game_id, r.id, Phase.phase_1)

        if r.decision:
            board.selected_branch = r.decision.value
            survivors = r.majority_agent_ids if r.decision.value == "save_majority" else r.minority_agent_ids
            lost = r.minority_agent_ids if r.decision.value == "save_majority" else r.majority_agent_ids
            board.survivors = survivors
            board.lost = lost
            board.resolution_state = "resolved"
            board.animation_version = 1
            round_outcome = {"survivors": survivors, "lost": lost}

    return GameStateResponse(
        game_id=g.id,
        status=g.status.value,
        current_round_number=g.current_round_number,
        current_round_id=current_round_id,
        current_phase=g.current_phase.value if g.current_phase else None,
        operator=operator,
        majority_agents=majority_agents,
        minority_agents=minority_agents,
        decision=r.decision.value if r and r.decision else None,
        round_outcome=round_outcome,
        scores=scores,
        coverage=coverage,
        phase_activity=phase_activity,
        last_event_at=last_event_at,
        board=board,
        version=version,
    )


def build_feed(game_id: str, limit: int = 50) -> list:
    """Build feed items from arguments + events for spectator."""
    from app.schemas.api import FeedItem
    items = []
    args_by_round = {}
    for rid in store.rounds_by_game.get(game_id, []):
        for a in store.get_arguments_for_round(rid):
            items.append((a.created_at, "argument", a))
    for e in store.get_events_for_game(game_id, limit=limit * 2):
        items.append((e.created_at, "event", e))
    items.sort(key=lambda x: x[0], reverse=True)
    out = []
    seen = set()
    for ts, typ, obj in items[:limit]:
        if typ == "argument":
            a = obj
            r = store.get_round(a.round_id)
            ag = store.get_agent(a.agent_id)
            key = ("arg", a.id)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                FeedItem(
                    id=a.id,
                    type="argument",
                    round_number=r.round_number if r else None,
                    phase=a.phase.value,
                    agent_id=a.agent_id,
                    display_name=ag.display_name if ag else a.agent_id[:8],
                    text=a.text,
                    created_at=a.created_at,
                )
            )
        else:
            e = obj
            key = ("ev", e.id)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                FeedItem(
                    id=e.id,
                    type="event",
                    payload=e.payload_json,
                    created_at=e.created_at,
                )
            )
    out.sort(key=lambda x: x.created_at, reverse=True)
    return out[:limit]


def build_scoreboard(game_id: str) -> Optional[dict]:
    g = store.get_game(game_id)
    if not g:
        return None
    parts = store.get_participations_for_game(game_id)
    scores = []
    coverage = []
    for p in parts:
        agent = store.get_agent(p.agent_id)
        name = agent.display_name if agent else p.agent_id[:8]
        scores.append({"agent_id": p.agent_id, "display_name": name, "score": p.score})
        coverage.append(
            CoverageProgress(
                agent_id=p.agent_id,
                display_name=name,
                has_been_operator=p.has_been_operator,
                has_been_majority=p.has_been_majority,
                has_been_minority=p.has_been_minority,
                complete=p.has_been_operator and p.has_been_majority and p.has_been_minority,
            )
        )
    return {"game_id": game_id, "scores": scores, "coverage": [c.model_dump() for c in coverage]}


def build_history(game_id: str) -> list:
    rounds = store.get_rounds_for_game(game_id)
    history = []
    for r in rounds:
        if r.status != RoundStatus.resolved or not r.decision:
            continue
        survivors = r.majority_agent_ids if r.decision.value == "save_majority" else r.minority_agent_ids
        lost = r.minority_agent_ids if r.decision.value == "save_majority" else r.majority_agent_ids
        op = store.get_agent(r.operator_agent_id)
        history.append({
            "round_id": r.id,
            "round_number": r.round_number,
            "operator_agent_id": r.operator_agent_id,
            "operator_display_name": op.display_name if op else r.operator_agent_id[:8],
            "decision": r.decision.value,
            "survivors": survivors,
            "lost": lost,
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        })
    return history
