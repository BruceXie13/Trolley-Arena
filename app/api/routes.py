"""FastAPI route handlers for Trolley Problem Arena."""
from fastapi import APIRouter, HTTPException, Query

from app.services import game_service
from app.services.state_builder import (
    build_game_state,
    build_feed,
    build_scoreboard,
    build_history,
)
from app.storage.store import store
from app.schemas.api import (
    CreateGameRequest,
    CreateGameResponse,
    RegisterAgentRequest,
    RegisterAgentResponse,
    GameStateResponse,
    SubmitArgumentRequest,
    SubmitDecisionRequest,
    AdvanceRequest,
    OpenActionsResponse,
    AddFillerRequest,
)

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/games", response_model=CreateGameResponse)
def create_game(body: CreateGameRequest | None = None):
    body = body or CreateGameRequest()
    g = game_service.create_game(min_players=body.min_players)
    return CreateGameResponse(game_id=g.id)


@router.get("/games")
def list_games(status: str | None = Query(None)):
    games = store.list_games(status=status)
    return [{"id": g.id, "status": g.status.value, "created_at": g.created_at.isoformat()} for g in games]


@router.get("/games/{game_id}")
def get_game(game_id: str):
    g = store.get_game(game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    return {
        "id": g.id,
        "status": g.status.value,
        "created_at": g.created_at.isoformat(),
        "current_round_number": g.current_round_number,
        "current_phase": g.current_phase.value if g.current_phase else None,
        "min_players": g.min_players,
    }


@router.post("/games/{game_id}/agents/register", response_model=RegisterAgentResponse)
def register_agent(game_id: str, body: RegisterAgentRequest):
    try:
        g, a, p = game_service.register_agent(game_id, body.display_name, body.token)
        return RegisterAgentResponse(agent_id=a.id, game_id=g.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/games/{game_id}/start")
def start_game(game_id: str):
    try:
        # Ensure at least 7 agents (1 operator, 5 majority, 1 minority) by adding fillers if needed
        from app.services.game_service import ROUND_TOTAL
        parts = store.get_participations_for_game(game_id)
        need = ROUND_TOTAL - len(parts)
        if need > 0:
            from app.services.gpt_filler import add_filler_agents
            add_filler_agents(game_id, need)
        g = game_service.start_game(game_id)
        return {"status": g.status.value, "message": "Game started"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/games/{game_id}/state", response_model=GameStateResponse)
def get_state(game_id: str, version: int = Query(0, ge=0)):
    state = build_game_state(game_id, version=version)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    return state


@router.get("/games/{game_id}/feed")
def get_feed(game_id: str, limit: int = Query(50, ge=1, le=200)):
    g = store.get_game(game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    items = build_feed(game_id, limit=limit)
    return {"game_id": game_id, "items": [i.model_dump() for i in items]}


@router.get("/games/{game_id}/scoreboard")
def get_scoreboard(game_id: str):
    data = build_scoreboard(game_id)
    if not data:
        raise HTTPException(status_code=404, detail="Game not found")
    return data


@router.get("/games/{game_id}/history")
def get_history(game_id: str):
    g = store.get_game(game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    return {"game_id": game_id, "rounds": build_history(game_id)}


@router.post("/games/{game_id}/rounds/{round_id}/arguments")
def submit_argument(game_id: str, round_id: str, body: SubmitArgumentRequest):
    try:
        arg = game_service.submit_argument(game_id, round_id, body.agent_id, body.text)
        return {"argument_id": arg.id, "phase": arg.phase.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/games/{game_id}/rounds/{round_id}/decision")
def submit_decision(game_id: str, round_id: str, body: SubmitDecisionRequest):
    try:
        game_service.submit_decision(game_id, round_id, body.agent_id, body.decision)
        return {"status": "ok", "decision": body.decision}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/games/{game_id}/advance")
def advance_game(game_id: str, body: AdvanceRequest | None = None):
    body = body or AdvanceRequest()
    try:
        g = game_service.advance(game_id, body.action)
        return {"status": g.status.value, "current_phase": g.current_phase.value if g.current_phase else None}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/games/{game_id}/open-actions", response_model=OpenActionsResponse)
def get_open_actions(game_id: str, agent_id: str = Query(...)):
    state = build_game_state(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    can_act = False
    allowed_action = None
    role = None
    if state.operator and state.operator.id == agent_id:
        role = "operator"
        if state.current_phase == "awaiting_decision":
            can_act = True
            allowed_action = "decision"
    for a in state.majority_agents + state.minority_agents:
        if a.id == agent_id:
            role = a.role
            if state.current_phase in ("phase_1", "phase_2", "phase_3"):
                if not a.argued_this_phase:
                    can_act = True
                    allowed_action = "argument"
            break
    return OpenActionsResponse(
        agent_id=agent_id,
        can_act=can_act,
        allowed_action=allowed_action,
        current_phase=state.current_phase,
        role=role,
    )


@router.post("/demo/create")
def demo_create():
    """Create a game and register 1 demo agent. Start adds fillers to reach 7 (1 operator, 5 majority, 1 minority)."""
    g = game_service.create_game(min_players=1)
    _, a, _ = game_service.register_agent(g.id, "Alice")
    return {
        "game_id": g.id,
        "agents": [{"agent_id": a.id, "display_name": "Alice"}],
        "message": "Call POST /api/games/{game_id}/start to start (fillers added automatically if needed)",
    }


@router.post("/games/{game_id}/add-filler")
def add_filler(game_id: str, body: AddFillerRequest | None = None):
    """Add GPT-backed filler agents when players are lacking."""
    body = body or AddFillerRequest()
    g = store.get_game(game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    if g.status.value not in ("waiting_for_agents", "ready_to_start"):
        raise HTTPException(status_code=400, detail="Can only add fillers before game starts")
    from app.services.gpt_filler import add_filler_agents
    added = add_filler_agents(game_id, body.count)
    return {"game_id": game_id, "added": added, "count": len(added)}


@router.post("/games/{game_id}/tick-filler")
def tick_filler(
    game_id: str,
    drain: bool = Query(True, description="Run filler ticks until no action and no advance (default true). Set ?drain=false for a single tick only."),
):
    """Let filler agents act and auto-advance when done. Always returns 200 so runners can keep polling; errors are in the body."""
    g = store.get_game(game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    from app.services.gpt_filler import execute_one_filler_action
    try:
        result = execute_one_filler_action(game_id)
        game_service.try_auto_advance(game_id)
        if not drain:
            return {"game_id": game_id, "action": result}
        actions = [result] if result else []
        for _ in range(24):
            r2 = execute_one_filler_action(game_id)
            advanced = game_service.try_auto_advance(game_id)
            if r2:
                actions.append(r2)
            if not r2 and not advanced:
                break
        return {"game_id": game_id, "action": result, "drained": True, "actions_count": len(actions)}
    except Exception as e:
        return {"game_id": game_id, "action": None, "error": str(e), "drained": False}


