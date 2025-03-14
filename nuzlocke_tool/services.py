import logging
import random
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from nuzlocke_tool.config import PathConfig
from nuzlocke_tool.constants import ACTIVE_PARTY_LIMIT, TAB_BOXED_NAME, TAB_DEAD_NAME, TAB_PARTY_NAME
from nuzlocke_tool.models import GameState, Pokemon, PokemonStatus
from nuzlocke_tool.utils import load_yaml_file

if TYPE_CHECKING:
    from nuzlocke_tool.container import Container

LOGGER = logging.getLogger(__name__)


class GameService:
    def __init__(self, container: "Container") -> None:
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


class JournalService:
    def __init__(self, game_state: GameState) -> None:
        self._journal_file = game_state.journal_file

    def add_capture_entry(self, pokemon: Pokemon) -> None:
        status_map = {PokemonStatus.ACTIVE: "Party", PokemonStatus.BOXED: "Box"}
        entry = f"Caught {pokemon} in {pokemon.encountered}. Added to {status_map[pokemon.status]}."
        self._append_entry(entry)

    def add_clause_entry(self, clause: str) -> None:
        entry = f"New session is using the {clause} clause."
        self._append_entry(entry)

    def add_dead_entry(self, pokemon: Pokemon) -> None:
        entry = f"{pokemon} has Died."
        self._append_entry(entry)

    def add_decision_entry(self, decision: str, outcome: str) -> None:
        entry = f"Randomly pick {decision}: {outcome}"
        self._append_entry(entry)

    def add_delete_move_entry(self, nickname: str, move: str) -> None:
        entry = f"{nickname} deleted move: {move}"
        self._append_entry(entry)

    def add_evolved_entry(self, pokemon: Pokemon, old_species: str) -> None:
        entry = f"{pokemon.nickname} evolved from {old_species} to {pokemon.species}"
        self._append_entry(entry)

    def add_learn_move_entry(self, nickname: str, move: str, old_move: str | None = None) -> None:
        entry = f"{nickname} learned move: {move}"
        if old_move:
            entry += f" (replacing {old_move})"
        self._append_entry(entry)

    def add_new_session_entry(self, game: str, ruleset: str) -> None:
        entry = f"Started new session in {game}."
        self._append_entry(entry)
        entry = f"New session is utilising the {ruleset} ruleset."
        self._append_entry(entry)

    def add_transfer_entry(self, pokemon: Pokemon, target: str) -> None:
        entry = f"Transferred {pokemon} to {target}."
        self._append_entry(entry)

    def _append_entry(self, entry: str) -> None:
        with self._journal_file.open("a") as f:
            f.write(f"{entry}\n")


class PokemonService:
    def __init__(self, container: "Container", game_state: GameState) -> None:
        self._container = container
        self._game_state = game_state
        self._journal_service = self._container.journal_service_factory(self._game_state)
        self._pokemon_repository = self._container.pokemon_repository()
        self._save_service = self._container.save_service()

    @property
    def active_pokemon(self) -> list[Pokemon]:
        return [p for p in self._game_state.pokemon if p.status == PokemonStatus.ACTIVE]

    @property
    def boxed_pokemon(self) -> list[Pokemon]:
        return [p for p in self._game_state.pokemon if p.status == PokemonStatus.BOXED]

    @property
    def dead_pokemon(self) -> list[Pokemon]:
        return [p for p in self._game_state.pokemon if p.status == PokemonStatus.DEAD]

    @property
    def party_full(self) -> bool:
        return len(self.active_pokemon) >= ACTIVE_PARTY_LIMIT

    def add_pokemon(self, pokemon: Pokemon) -> None:
        self._game_state.pokemon.append(pokemon)
        self._game_state.encounters.append(pokemon.encountered)
        self._save_service.save_session(self._game_state)
        self._journal_service.add_capture_entry(pokemon)

    def edit_pokemon(self, pokemon: Pokemon, current_species: str) -> None:
        pokemon_data = self._pokemon_repository.get_by_id(current_species)
        self._save_service.save_session(self._game_state)
        if "evolve" in pokemon_data and pokemon.species in pokemon_data["evolve"]:
            self._journal_service.add_evolved_entry(pokemon, current_species)

    def learn_move(self, pokemon: Pokemon, index: int, new_move: str) -> None:
        old_move = pokemon.moves[index] if index < len(pokemon.moves) else ""
        pokemon.moves[index] = new_move
        self._save_service.save_session(self._game_state)
        if old_move == "":
            self._journal_service.add_learn_move_entry(pokemon.nickname, new_move)
            LOGGER.info("Pokemon %s learned move: %s", pokemon.nickname, new_move)
        elif new_move == "":
            self._journal_service.add_delete_move_entry(pokemon.nickname, old_move)
            LOGGER.info("Pokemon %s deleted move: %s", pokemon.nickname, old_move)
        else:
            self._journal_service.add_learn_move_entry(pokemon.nickname, new_move, old_move)
            LOGGER.info("Pokemon %s learned move: %s (was: %s)", pokemon.nickname, new_move, old_move)

    @staticmethod
    def _process_storage_status(status: PokemonStatus) -> str:
        status_map = {
            PokemonStatus.ACTIVE: TAB_PARTY_NAME,
            PokemonStatus.BOXED: TAB_BOXED_NAME,
            PokemonStatus.DEAD: TAB_DEAD_NAME,
        }
        return status_map[status]

    def remove_pokemon(self, pokemon: Pokemon) -> None:
        self._game_state.pokemon.remove(pokemon)
        if not any(p.encountered == pokemon.encountered for p in self._game_state.pokemon):
            self._game_state.encounters.remove(pokemon.encountered)
        self._save_service.save_session(self._game_state)

    def transfer_pokemon(self, pokemon: Pokemon, target_status: PokemonStatus) -> None:
        pokemon.status = target_status
        self._save_service.save_session(self._game_state)
        if target_status == PokemonStatus.DEAD:
            self._journal_service.add_dead_entry(pokemon)
        else:
            status_name = self._process_storage_status(target_status)
            self._journal_service.add_transfer_entry(pokemon, status_name)


class RandomDecisionService:
    def __init__(self, container: "Container", game_state: GameState) -> None:
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


class SaveService:
    @staticmethod
    def create_save_file(game: str, ruleset: str) -> Path:
        folder = PathConfig.save_folder()
        base_name = f"{game}_{ruleset}_"
        i = 1
        while True:
            save_file = folder / f"{base_name}{i}.sav"
            if not save_file.exists():
                break
            i += 1
        save_file.touch(exist_ok=False)
        LOGGER.info("Created new save file: %s", save_file)
        return save_file

    @staticmethod
    def load_session(filepath: Path) -> GameState:
        with filepath.open("r") as f:
            data = yaml.safe_load(f)
        data["journal_file"] = Path(data["journal_file"])
        data["save_file"] = Path(data["save_file"])
        pokemon_list = []
        for pokemon_dict in data["pokemon"]:
            status_str = pokemon_dict.pop("status")
            pokemon = Pokemon(**pokemon_dict, status=PokemonStatus[status_str])
            pokemon_list.append(pokemon)
        data["pokemon"] = pokemon_list
        LOGGER.info("Game loaded from %s", filepath)
        return GameState(**data)

    @staticmethod
    def save_session(game_state: GameState) -> None:
        game_state_dict = asdict(game_state)
        game_state_dict["journal_file"] = str(game_state_dict["journal_file"])
        game_state_dict["save_file"] = str(game_state_dict["save_file"])
        pokemon_list = []
        for pokemon in game_state_dict["pokemon"]:
            pokemon_dict = {k: v for k, v in pokemon.items() if k != "status"}
            pokemon_dict["status"] = pokemon["status"].name
            pokemon_list.append(pokemon_dict)
        game_state_dict["pokemon"] = pokemon_list
        with game_state.save_file.open("w") as f:
            yaml.dump(game_state_dict, f)
        LOGGER.info("Game saved to %s", game_state.save_file)

    def _append_entry(self, entry: str) -> None:
        with self._journal_file.open("a") as f:
            f.write(f"{entry}\n")
