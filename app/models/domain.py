"""Domain models for Trolley Problem Arena (Pydantic + plain dataclass-style)."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


class GameStatus(str, Enum):
    waiting_for_agents = "waiting_for_agents"
    ready_to_start = "ready_to_start"
    round_phase_1 = "round_phase_1"
    round_phase_2 = "round_phase_2"
    round_phase_3 = "round_phase_3"
    awaiting_operator_decision = "awaiting_operator_decision"
    round_resolved = "round_resolved"
    game_completed = "game_completed"


class Phase(str, Enum):
    phase_1 = "phase_1"
    phase_2 = "phase_2"
    phase_3 = "phase_3"
    awaiting_decision = "awaiting_decision"
    resolved = "resolved"


class RoundStatus(str, Enum):
    active = "active"
    resolved = "resolved"


class Decision(str, Enum):
    save_majority = "save_majority"
    save_minority = "save_minority"


class EventType(str, Enum):
    game_created = "game_created"
    agent_registered = "agent_registered"
    game_started = "game_started"
    round_started = "round_started"
    argument_submitted = "argument_submitted"
    phase_advanced = "phase_advanced"
    decision_submitted = "decision_submitted"
    round_resolved = "round_resolved"
    game_completed = "game_completed"


@dataclass
class Game:
    id: str
    status: GameStatus
    created_at: datetime
    current_round_number: int
    current_phase: Optional[Phase]
    min_players: int
    config: dict = field(default_factory=dict)

    @staticmethod
    def new(min_players: int = 3) -> "Game":
        return Game(
            id=str(uuid4()),
            status=GameStatus.waiting_for_agents,
            created_at=datetime.utcnow(),
            current_round_number=0,
            current_phase=None,
            min_players=min_players,
        )


@dataclass
class Agent:
    id: str
    display_name: str
    token: Optional[str] = None
    created_at: Optional[datetime] = None

    @staticmethod
    def new(display_name: str, token: Optional[str] = None) -> "Agent":
        return Agent(
            id=str(uuid4()),
            display_name=display_name,
            token=token,
            created_at=datetime.utcnow(),
        )


@dataclass
class Participation:
    game_id: str
    agent_id: str
    score: int
    has_been_operator: bool
    has_been_majority: bool
    has_been_minority: bool
    joined_at: datetime

    @staticmethod
    def new(game_id: str, agent_id: str) -> "Participation":
        return Participation(
            game_id=game_id,
            agent_id=agent_id,
            score=0,
            has_been_operator=False,
            has_been_majority=False,
            has_been_minority=False,
            joined_at=datetime.utcnow(),
        )


@dataclass
class Round:
    id: str
    game_id: str
    round_number: int
    status: RoundStatus
    phase: Phase
    operator_agent_id: str
    majority_agent_ids: list[str]
    minority_agent_ids: list[str]
    decision: Optional[Decision] = None
    resolved_at: Optional[datetime] = None

    @staticmethod
    def new(
        game_id: str,
        round_number: int,
        operator_agent_id: str,
        majority_agent_ids: list[str],
        minority_agent_ids: list[str],
    ) -> "Round":
        return Round(
            id=str(uuid4()),
            game_id=game_id,
            round_number=round_number,
            status=RoundStatus.active,
            phase=Phase.phase_1,
            operator_agent_id=operator_agent_id,
            majority_agent_ids=majority_agent_ids,
            minority_agent_ids=minority_agent_ids,
        )


@dataclass
class Argument:
    id: str
    game_id: str
    round_id: str
    phase: Phase
    agent_id: str
    text: str
    created_at: datetime

    @staticmethod
    def new(game_id: str, round_id: str, phase: Phase, agent_id: str, text: str) -> "Argument":
        return Argument(
            id=str(uuid4()),
            game_id=game_id,
            round_id=round_id,
            phase=phase,
            agent_id=agent_id,
            text=text,
            created_at=datetime.utcnow(),
        )


@dataclass
class EventLog:
    id: str
    game_id: str
    round_id: Optional[str]
    event_type: EventType
    payload_json: dict
    created_at: datetime

    @staticmethod
    def new(
        game_id: str,
        event_type: EventType,
        payload_json: dict,
        round_id: Optional[str] = None,
    ) -> "EventLog":
        return EventLog(
            id=str(uuid4()),
            game_id=game_id,
            round_id=round_id,
            event_type=event_type,
            payload_json=payload_json,
            created_at=datetime.utcnow(),
        )
