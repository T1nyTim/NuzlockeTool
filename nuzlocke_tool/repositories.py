from nuzlocke_tool.data_loader import GameDataLoader
from nuzlocke_tool.models.models import MoveData, PokemonData


class LocationRepository:
    def __init__(self, game_data_loader: GameDataLoader) -> None:
        self._game_data_loader = game_data_loader

    def get_available(self, game: str, sub_region_clause: bool, encounters: list[str]) -> list[str]:
        all_locations = self.get_for_game(game, sub_region_clause)
        available_locations = [loc for loc in all_locations if loc not in encounters]
        available_locations.sort()
        return available_locations

    def get_for_game(self, game: str, sub_region_clause: bool) -> list[str]:
        region_type = "Partial" if sub_region_clause else "Full"
        return [
            location
            for location, info in self._game_data_loader.location_data.items()
            if (info.get("type") == region_type or info.get("type") is None) and game in info["games"]
        ]


class MoveRepository:
    def __init__(self, game_data_loader: GameDataLoader) -> None:
        self._game_data_loader = game_data_loader

    def get_by_id(self, move: str) -> MoveData:
        return self._game_data_loader.move_data[move]


class PokemonRepository:
    def __init__(self, game_data_loader: GameDataLoader) -> None:
        self._game_data_loader = game_data_loader

    def get_by_id(self, species: str) -> PokemonData:
        return self._game_data_loader.pokemon_data[species]

    def get_all_species(self) -> list[str]:
        return list(self._game_data_loader.pokemon_data.keys())

    def get_moves_for_species(self, species: str) -> list[str]:
        pokemon_data = self._game_data_loader.pokemon_data.get(species, {})
        return pokemon_data.get("moves", [])
