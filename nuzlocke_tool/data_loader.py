from typing import TYPE_CHECKING

from nuzlocke_tool.config import PathConfig
from nuzlocke_tool.utils import load_yaml_file

if TYPE_CHECKING:
    from nuzlocke_tool.models import LocationData, MoveData, PokemonData


class GameDataLoader:
    def __init__(self) -> None:
        self.location_data: dict[str, LocationData] = {}
        self.move_data: dict[str, MoveData] = {}
        self.pokemon_data: dict[str, PokemonData] = {}

    def load_location_data(self) -> None:
        self.location_data = load_yaml_file(PathConfig.locations_file())

    def load_move_data(self, generation: str) -> None:
        move_data_file = f"gen{generation}_moves.yaml"
        move_yaml_path = PathConfig.resources_folder() / move_data_file
        if not move_yaml_path.exists():
            err_msg = f"Move data file not found: {move_yaml_path}"
            raise FileNotFoundError(err_msg)
        self.move_data = load_yaml_file(move_yaml_path)

    def load_pokemon_data(self, generation: str) -> None:
        pokemon_data_file = f"gen{generation}_pokemon.yaml"
        pokemon_yaml_path = PathConfig.resources_folder() / pokemon_data_file
        if not pokemon_yaml_path.exists():
            err_msg = f"Pokemon data file not found: {pokemon_yaml_path}"
            raise FileNotFoundError(err_msg)
        self.pokemon_data = load_yaml_file(pokemon_yaml_path)
