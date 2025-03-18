import copy
from dataclasses import dataclass, field
from typing import Self

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
from nuzlocke_tool.data.repositories import PokemonRepository
from nuzlocke_tool.models.models import (
    FailedEncounter,
    GameState,
    Pokemon,
    PokemonCardType,
    PokemonStatus,
    PokemonTypeCoverage,
)
from nuzlocke_tool.services.pokemon_service import PokemonService
from nuzlocke_tool.utils.utils import get_image_filename


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
class DecisionViewModel:
    key: str
    display_name: str
    options: list[str]
    current_outcome: str | None

    @property
    def button_text(self) -> str:
        return f"Randomly pick {self.display_name}"

    @property
    def has_outcome(self) -> bool:
        return self.current_outcome is not None

    @property
    def outcome_text(self) -> str:
        return self.current_outcome if self.has_outcome else ""

    @classmethod
    def create_from_data(
        cls,
        key: str,
        display_name: str,
        options: list[str],
        current_outcome: str | None,
    ) -> Self:
        return cls(key, display_name, options, current_outcome)


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
    is_failed_encounter: bool = False

    @property
    def display_details(self) -> str:
        if not self.has_encounter and not self.is_failed_encounter:
            return "None"
        if self.is_failed_encounter:
            return f"FAILED: {self.species} (Lv{self.caught_level})"
        return f"{self.nickname} ({self.species}) - Caught Lv{self.caught_level}"

    @property
    def display_status(self) -> str:
        if self.is_failed_encounter:
            return "Failed"
        return self.status if self.has_encounter else "None"

    @property
    def has_encounter(self) -> bool:
        return self.pokemon is not None

    @classmethod
    def _create_from_location(cls, location: str, row_index: int) -> Self:
        return cls(location, row_index)

    @classmethod
    def create_view_models(
        cls,
        locations: list[str],
        pokemon: list[Pokemon],
        failed_encounters: list[FailedEncounter],
        location_row_map: dict[str, int],
    ) -> list[Self]:
        view_models = [cls._create_from_location(loc, location_row_map[loc]) for loc in locations]
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
        for failed in failed_encounters:
            location = failed.location
            if location in location_row_map:
                row = location_row_map[location]
                view_model = view_models[row]
                if not view_model.has_encounter:
                    view_model.is_failed_encounter = True
                    view_model.species = failed.species
                    view_model.caught_level = failed.level
                    view_model.status_color = QColor(TABLE_COLOR_DEAD)
        return view_models


@dataclass
class GameStateViewModel:
    is_game_active: bool
    game_name: str | None = None
    ruleset_name: str | None = None
    ruleset_description: list[str] | None = None
    can_add_to_party: bool = False

    @classmethod
    def from_game_state(cls, game_state: GameState, pokemon_service: PokemonService) -> Self:
        if not game_state:
            return cls(is_game_active=False)
        can_add = False
        if pokemon_service:
            test_state = copy.deepcopy(game_state)
            dummy_pokemon = Pokemon(
                nickname="A",
                species="Bulbasaur",
                level=5,
                caught_level=5,
                moves=["Tackle", "Growl"],
                dvs={"HP": 0, "Atk": 0, "Def": 0, "Spd": 0, "Spe": 0},
                encountered="Pallet Town",
                status=PokemonStatus.ACTIVE,
            )
            test_state.pokemon.append(dummy_pokemon)
            can_add = not pokemon_service.party_full and game_state.rule_strategy.validate_party(game_state)
        return cls(
            True,
            game_state.game,
            game_state.ruleset,
            game_state.rule_strategy.rules_description if game_state.rule_strategy else None,
            can_add,
        )


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

    @classmethod
    def create_pokemon_viewmodels(
        cls,
        game_state: GameState,
        pokemon_repository: PokemonRepository,
        status: PokemonStatus,
        card_type: PokemonCardType,
    ) -> list[tuple[Self, Pokemon]]:
        filtered_pokemon = [p for p in game_state.pokemon if p.status == status]
        return [
            (cls.from_pokemon(pokemon, pokemon_repository, card_type), pokemon)
            for pokemon in filtered_pokemon
        ]


@dataclass
class TeamBalanceViewModel:
    defensive_coverage: dict[str, float] = field(default_factory=dict)
    offensive_coverage: dict[str, dict[str, float]] = field(default_factory=dict)
    offensive_best_scores: dict[str, float] = field(default_factory=dict)
    pokemon_best_moves: dict[str, dict[str, float]] = field(default_factory=dict)
    pokemon_best_move_details: dict[str, dict[str, tuple[str, float]]] = field(default_factory=dict)
    pokemon_coverage: list[PokemonTypeCoverage] = field(default_factory=list)

    @property
    def defensive_categories(self) -> dict[float, list[str]]:
        categories = {}
        for type_name, multiplier in self.defensive_coverage.items():
            if multiplier not in categories:
                categories[multiplier] = []
            categories[multiplier].append(type_name)
        return dict(sorted(categories.items(), key=lambda x: x[0], reverse=True))

    @property
    def offensive_categories(self) -> dict[str, list[str]]:
        categories = {}
        for type_combo, score in self.offensive_best_scores.items():
            if score not in categories:
                categories[score] = []
            categories[score].append(type_combo)
        return dict(sorted(categories.items(), key=lambda x: x[0]))

    @property
    def sorted_defensive_types(self) -> list[tuple[str, float]]:
        return sorted(self.defensive_coverage.items(), key=lambda x: x[1], reverse=True)

    @classmethod
    def create_empty(cls) -> Self:
        return cls()
