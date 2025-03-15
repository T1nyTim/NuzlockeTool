from pathlib import Path

from nuzlocke_tool.config import PathConfig
from nuzlocke_tool.container import Container
from nuzlocke_tool.models import GameState
from nuzlocke_tool.utils import load_yaml_file


class GameService:
    def __init__(self, container: Container) -> None:
        self._container = container
        self._save_service = self._container.save_service()

    @staticmethod
    def _create_journal_file(game: str, ruleset: str) -> Path:
        folder = PathConfig.journal_folder()
        base_name = f"{game}_{ruleset}_"
        i = 1
        while True:
            journal_file = folder / f"{base_name}{i}.journal"
            if not journal_file.exists():
                break
            i += 1
        journal_file.touch(exist_ok=False)
        return journal_file

    def new_game(self, game: str, ruleset: str, generation: str, sub_region_clause: bool) -> GameState:
        game_data_loader = self._container.game_data_loader()
        game_data_loader.load_pokemon_data(generation)
        game_data_loader.load_move_data(generation)
        journal_file = self._create_journal_file(game, ruleset)
        save_file = self._save_service.create_save_file(game, ruleset)
        game_state = GameState(game, ruleset, sub_region_clause, journal_file, save_file, [], [], {})
        journal_service = self._container.journal_service_factory(game_state)
        journal_service.add_new_session_entry(game, ruleset)
        if sub_region_clause:
            journal_service.add_clause_entry("Sub-Region")
        return game_state

    def load_game(self, save_path: Path) -> GameState:
        game_state = self._save_service.load_session(save_path)
        versions = load_yaml_file(PathConfig.versions_file())
        version_info = versions[game_state.game]
        generation = version_info["generation"]
        game_data_loader = self._container.game_data_loader()
        game_data_loader.load_pokemon_data(generation)
        game_data_loader.load_move_data(generation)
        return game_state

    def save_game(self, game_state: GameState) -> None:
        self._save_service.save_session(game_state)
