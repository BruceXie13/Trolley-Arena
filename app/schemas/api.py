"""Pydantic schemas for API request/response."""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class CreateGameRequest(BaseModel):
    min_players: int = 3


class CreateGameResponse(BaseModel):
    game_id: str


class RegisterAgentRequest(BaseModel):
    display_name: str
    token: Optional[str] = None


class RegisterAgentResponse(BaseModel):
    agent_id: str
    game_id: str


class AgentSummary(BaseModel):
    id: str
    display_name: str
    role: str  # "operator" | "majority" | "minority"
    argued_this_phase: bool = False


class BoardState(BaseModel):
    selected_branch: Optional[str] = None  # "majority" | "minority" after decision
    resolution_state: Optional[str] = None  # "saved" | "lost" per side
    animation_version: int = 0
    survivors: list[str] = Field(default_factory=list)
    lost: list[str] = Field(default_factory=list)


class CoverageProgress(BaseModel):
    agent_id: str
    display_name: str
    has_been_operator: bool
    has_been_majority: bool
    has_been_minority: bool
    complete: bool


class GameStateResponse(BaseModel):
    game_id: str
    status: str
    current_round_number: int
    current_round_id: Optional[str] = None
    current_phase: Optional[str] = None
    operator: Optional[AgentSummary] = None
    majority_agents: list[AgentSummary] = Field(default_factory=list)
    minority_agents: list[AgentSummary] = Field(default_factory=list)
    decision: Optional[str] = None
    round_outcome: Optional[dict] = None  # survivors, lost
    scores: dict[str, int] = Field(default_factory=dict)
    coverage: list[CoverageProgress] = Field(default_factory=list)
    phase_activity: list[str] = Field(default_factory=list)  # agent_ids who argued this phase
    last_event_at: Optional[datetime] = None
    board: Optional[BoardState] = None
    version: int = 0


class FeedItem(BaseModel):
    id: str
    type: str  # "argument" | "event"
    round_number: Optional[int] = None
    phase: Optional[str] = None
    agent_id: Optional[str] = None
    display_name: Optional[str] = None
    text: Optional[str] = None
    payload: Optional[dict] = None
    created_at: datetime


class ScoreboardResponse(BaseModel):
    game_id: str
    scores: list[dict[str, Any]] = Field(default_factory=list)  # [{agent_id, display_name, score}, ...]
    coverage: list[CoverageProgress] = Field(default_factory=list)


class SubmitArgumentRequest(BaseModel):
    agent_id: str
    text: str = Field(..., min_length=1, max_length=500)


class SubmitDecisionRequest(BaseModel):
    agent_id: str
    decision: str  # "save_majority" | "save_minority"


class AdvanceRequest(BaseModel):
    action: str = "next_phase"  # "next_phase" | "force_decision" | "resolve_round"


class OpenActionsResponse(BaseModel):
    agent_id: str
    can_act: bool
    allowed_action: Optional[str] = None  # "argument" | "decision" | null
    current_phase: Optional[str] = None
    role: Optional[str] = None


class AddFillerRequest(BaseModel):
    count: int = Field(2, ge=1, le=5)
