import datetime
import logging
from dataclasses import asdict
from pathlib import Path

import yaml

from nuzlocke_tool.config import PathConfig
from nuzlocke_tool.models.models import GameState, Pokemon, PokemonStatus

LOGGER = logging.getLogger(__name__)


class SaveService:
    def _append_entry(self, entry: str) -> None:
        with self._journal_file.open("a") as f:
            f.write(f"{entry}\n")

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

    def save_session(self, game_state: GameState) -> None:
        game_state_dict = asdict(game_state)
        del game_state_dict["rule_strategy"]
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
