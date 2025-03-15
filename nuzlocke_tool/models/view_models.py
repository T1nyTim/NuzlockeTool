from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Self

from PyQt6.QtGui import QColor

from nuzlocke_tool.constants import (
    LABEL_NO_DEFENDING_POKEMON,
    LABEL_NO_MOVES,
    TAB_BOXED_NAME,
    TAB_DEAD_NAME,
    TAB_PARTY_NAME,
    TABLE_COLOR_BOXED,
    TABLE_COLOR_DEAD,
    TABLE_COLOR_PARTY,
)
from nuzlocke_tool.models.models import GameState, Pokemon, PokemonCardType, PokemonStatus
from nuzlocke_tool.repositories import PokemonRepository
from nuzlocke_tool.utils import get_image_filename

if TYPE_CHECKING:
    from nuzlocke_tool.container import Container


@dataclass
class BestMoveViewModel:
    defending_pokemon: str = ""
    defending_level: int = 1
    defending_hp: int = 0
    defense_stage: int = 0
    special_stage: int = 0
    reflect_active: bool = False
    light_screen_active: bool = False
    move_results: list[tuple[float, str, str, int, int]] = field(default_factory=list)
    attacker_stages: list[tuple[Pokemon, int, int, int]] = field(default_factory=list)

    @property
    def defender_display_text(self) -> str:
        if not self.has_valid_defender:
            return LABEL_NO_DEFENDING_POKEMON
        return (
            f"Defending {self.defending_pokemon} at level {self.defending_level} with {self.defending_hp} HP"
        )

    @property
    def formatted_results(self) -> list[str]:
        if not self.has_results:
            return [LABEL_NO_MOVES]
        results = []
        for i, (lta, nickname, move_name, dmg_min, dmg_max) in enumerate(self.move_results[:5]):
            results.append(
                f"{i + 1}. {nickname}'s {move_name}: Damage Range = {dmg_min} - {dmg_max} (Long-Term "
                f"Average = {lta:.1f})",
            )
        return results

    @property
    def has_valid_defender(self) -> bool:
        return bool(self.defending_pokemon)

    @property
    def has_results(self) -> bool:
        return bool(self.move_results)


@dataclass
class EncounterViewModel:
    location: str
    row_index: int
    pokemon: str | None = None
    nickname: str | None = None
    species: str | None = None
    caught_level: int | None = None
    status: str | None = None
    status_color: QColor | None = None

    @property
    def display_details(self) -> str:
        if not self.has_encounter:
            return "None"
        return f"{self.nickname} ({self.species}) - Caught Lv{self.caught_level}"

    @property
    def display_status(self) -> str:
        return self.status if self.has_encounter else "None"

    @property
    def has_encounter(self) -> bool:
        return self.pokemon is not None


class EncounterViewModelFactory:
    @staticmethod
    def create_view_models(
        locations: list[str],
        pokemon: list[Pokemon],
        location_row_map: dict[str, int],
    ) -> list[EncounterViewModel]:
        view_models = [EncounterViewModel(location=loc, row_index=location_row_map[loc]) for loc in locations]
        status_map = {
            PokemonStatus.ACTIVE: TAB_PARTY_NAME,
            PokemonStatus.BOXED: TAB_BOXED_NAME,
            PokemonStatus.DEAD: TAB_DEAD_NAME,
        }
        for mon in pokemon:
            location = mon.encountered
            if location in location_row_map:
                row = location_row_map[location]
                view_model = view_models[row]
                view_model.pokemon = str(mon)
                view_model.nickname = mon.nickname
                view_model.species = mon.species
                view_model.caught_level = mon.caught_level
                view_model.status = status_map[mon.status]
                if mon.status == PokemonStatus.ACTIVE:
                    view_model.status_color = QColor(TABLE_COLOR_PARTY)
                elif mon.status == PokemonStatus.BOXED:
                    view_model.status_color = QColor(TABLE_COLOR_BOXED)
                elif mon.status == PokemonStatus.DEAD:
                    view_model.status_color = QColor(TABLE_COLOR_DEAD)
        return view_models


@dataclass
class PokemonCardViewModel:
    nickname: str
    species: str
    level: int
    moves: list[str]
    image_path: str
    dvs: dict[str, int]
    can_evolve: bool
    card_type: PokemonCardType
    encountered: str
    evolution_options: list[str] = field(default_factory=list)
    available_moves: list[str] = field(default_factory=list)

    @classmethod
    def from_pokemon(
        cls,
        pokemon: Pokemon,
        pokemon_repository: PokemonRepository,
        card_type: PokemonCardType,
    ) -> Self:
        pokemon_data = pokemon_repository.get_by_id(pokemon.species)
        can_evolve = False
        evolution_options = []
        if "evolve" in pokemon_data:
            can_evolve = True
            evolution_options = pokemon_data["evolve"]
        image_path = f"{get_image_filename(pokemon.species)}.png"
        return cls(
            pokemon.nickname,
            pokemon.species,
            pokemon.level,
            pokemon.moves.copy(),
            image_path,
            pokemon.dvs.copy(),
            can_evolve,
            card_type,
            pokemon.encountered,
            evolution_options,
            pokemon_data["moves"],
        )


class PokemonCardViewModelFactory:
    def __init__(self, container: "Container", pokemon_repository: PokemonRepository) -> None:
        self._container = container
        self._pokemon_repository = pokemon_repository

    def create_pokemon_viewmodels(
        self,
        game_state: GameState,
        status: PokemonStatus,
        card_type: PokemonCardType,
    ) -> list[tuple[PokemonCardViewModel, Pokemon]]:
        filtered_pokemon = [p for p in game_state.pokemon if p.status == status]
        return [
            (self.create_pokemon_card_viewmodel(pokemon, card_type), pokemon) for pokemon in filtered_pokemon
        ]

    def create_pokemon_card_viewmodel(
        self,
        pokemon: Pokemon,
        card_type: PokemonCardType,
    ) -> PokemonCardViewModel:
        return PokemonCardViewModel.from_pokemon(pokemon, self._pokemon_repository, card_type)
