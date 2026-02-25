"""In-memory store for games, agents, rounds, arguments, events."""
from typing import Optional
from app.models.domain import (
    Game,
    Agent,
    Participation,
    Round,
    Argument,
    EventLog,
    Phase,
)


class Store:
    def __init__(self) -> None:
        self.games: dict[str, Game] = {}
        self.agents: dict[str, Agent] = {}
        self.participations: dict[str, Participation] = {}  # key: f"{game_id}:{agent_id}"
        self.rounds: dict[str, Round] = {}
        self.rounds_by_game: dict[str, list[str]] = {}  # game_id -> [round_id, ...]
        self.arguments: dict[str, Argument] = {}
        self.arguments_by_round: dict[str, list[str]] = {}  # round_id -> [arg_id, ...]
        self.events: list[EventLog] = []
        # GPT filler: set of agent_id that are AI-controlled
        self.filler_agent_ids: set[str] = set()

    def add_game(self, g: Game) -> None:
        self.games[g.id] = g
        self.rounds_by_game[g.id] = []

    def get_game(self, game_id: str) -> Optional[Game]:
        return self.games.get(game_id)

    def update_game(self, g: Game) -> None:
        self.games[g.id] = g

    def add_agent(self, a: Agent) -> None:
        self.agents[a.id] = a

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self.agents.get(agent_id)

    def add_participation(self, p: Participation) -> None:
        self.participations[f"{p.game_id}:{p.agent_id}"] = p

    def get_participation(self, game_id: str, agent_id: str) -> Optional[Participation]:
        return self.participations.get(f"{game_id}:{agent_id}")

    def get_participations_for_game(self, game_id: str) -> list[Participation]:
        return [p for k, p in self.participations.items() if k.startswith(f"{game_id}:")]

    def update_participation(self, p: Participation) -> None:
        self.participations[f"{p.game_id}:{p.agent_id}"] = p

    def add_round(self, r: Round) -> None:
        self.rounds[r.id] = r
        self.rounds_by_game.setdefault(r.game_id, []).append(r.id)
        self.arguments_by_round[r.id] = []

    def get_round(self, round_id: str) -> Optional[Round]:
        return self.rounds.get(round_id)

    def get_current_round(self, game_id: str) -> Optional[Round]:
        ids = self.rounds_by_game.get(game_id, [])
        if not ids:
            return None
        return self.rounds.get(ids[-1])

    def get_rounds_for_game(self, game_id: str) -> list[Round]:
        ids = self.rounds_by_game.get(game_id, [])
        return [self.rounds[rid] for rid in ids if rid in self.rounds]

    def update_round(self, r: Round) -> None:
        self.rounds[r.id] = r

    def add_argument(self, a: Argument) -> None:
        self.arguments[a.id] = a
        self.arguments_by_round.setdefault(a.round_id, []).append(a.id)

    def get_arguments_for_round(self, round_id: str) -> list[Argument]:
        ids = self.arguments_by_round.get(round_id, [])
        return [self.arguments[aid] for aid in ids if aid in self.arguments]

    def get_arguments_in_round_phase(self, round_id: str, phase: Phase) -> list[Argument]:
        args = self.get_arguments_for_round(round_id)
        return [a for a in args if a.phase == phase]

    def add_event(self, e: EventLog) -> None:
        self.events.append(e)

    def get_events_for_game(
        self,
        game_id: str,
        round_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[EventLog]:
        out = [e for e in self.events if e.game_id == game_id]
        if round_id is not None:
            out = [e for e in out if e.round_id == round_id]
        out.sort(key=lambda x: x.created_at, reverse=True)
        return out[:limit]

    def list_games(self, status: Optional[str] = None) -> list[Game]:
        games = list(self.games.values())
        if status:
            games = [g for g in games if g.status.value == status]
        return sorted(games, key=lambda g: g.created_at, reverse=True)

    def mark_filler(self, agent_id: str) -> None:
        self.filler_agent_ids.add(agent_id)

    def is_filler(self, agent_id: str) -> bool:
        return agent_id in self.filler_agent_ids


# Singleton
store = Store()
