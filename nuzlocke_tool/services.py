import logging
from dataclasses import asdict
from pathlib import Path

import yaml

from nuzlocke_tool.config import PathConfig
from nuzlocke_tool.models import GameState, Pokemon, PokemonStatus

LOGGER = logging.getLogger(__name__)


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
