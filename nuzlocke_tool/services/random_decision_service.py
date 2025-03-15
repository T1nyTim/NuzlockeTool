import random

from nuzlocke_tool.container import Container
from nuzlocke_tool.models.models import GameState


class RandomDecisionService:
    def __init__(self, container: Container, game_state: GameState) -> None:
        self._container = container
        self._game_state = game_state
        self._journal_service = self._container.journal_service_factory(game_state)
        self._save_service = self._container.save_service()

    def make_decision(self, decision_key: str, decision_options: list[str], display_name: str) -> str:
        outcome = random.choice(decision_options)
        self._game_state.decisions[decision_key] = outcome
        self._save_service.save_session(self._game_state)
        self._journal_service.add_decision_entry(display_name, outcome)
        return outcome
