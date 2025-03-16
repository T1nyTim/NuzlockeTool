import copy
import logging
from typing import TYPE_CHECKING

from nuzlocke_tool.constants import ACTIVE_PARTY_LIMIT, TAB_BOXED_NAME, TAB_DEAD_NAME, TAB_PARTY_NAME
from nuzlocke_tool.models.models import EventType, GameState, Pokemon, PokemonStatus

if TYPE_CHECKING:
    from nuzlocke_tool.container import Container

LOGGER = logging.getLogger(__name__)


class PokemonService:
    def __init__(self, container: "Container", game_state: GameState) -> None:
        self._container = container
        self._event_manager = self._container.event_manager()
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

    @staticmethod
    def _process_storage_status(status: PokemonStatus) -> str:
        status_map = {
            PokemonStatus.ACTIVE: TAB_PARTY_NAME,
            PokemonStatus.BOXED: TAB_BOXED_NAME,
            PokemonStatus.DEAD: TAB_DEAD_NAME,
        }
        return status_map[status]

    def add_pokemon(self, pokemon: Pokemon) -> bool:
        if pokemon.status == PokemonStatus.ACTIVE:
            test_state = copy.deepcopy(self._game_state)
            test_state.pokemon.append(pokemon)
            if not self._game_state.rule_strategy.validate_party(test_state):
                return False
        self._game_state.pokemon.append(pokemon)
        self._game_state.encounters.append(pokemon.encountered)
        self._save_service.save_session(self._game_state)
        self._journal_service.add_capture_entry(pokemon)
        self._event_manager.publish(EventType.POKEMON_ADDED, {"pokemon": pokemon})
        return True

    def edit_pokemon(self, pokemon: Pokemon, current_species: str) -> bool:
        pokemon_data = self._pokemon_repository.get_by_id(current_species)
        self._save_service.save_session(self._game_state)
        if "evolve" in pokemon_data and pokemon.species in pokemon_data["evolve"]:
            self._journal_service.add_evolved_entry(pokemon, current_species)
        self._event_manager.publish(EventType.POKEMON_EDITED, {"pokemon": pokemon})
        return True

    def learn_move(self, pokemon: Pokemon, index: int, new_move: str) -> bool:
        old_move = pokemon.moves[index] if index < len(pokemon.moves) else ""
        pokemon.moves[index] = new_move
        print(self._game_state)
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
        self._event_manager.publish(EventType.MOVE_UPDATED)
        return True

    def remove_pokemon(self, pokemon: Pokemon) -> bool:
        self._game_state.pokemon.remove(pokemon)
        if not any(p.encountered == pokemon.encountered for p in self._game_state.pokemon):
            self._game_state.encounters.remove(pokemon.encountered)
        self._save_service.save_session(self._game_state)
        self._event_manager.publish(EventType.POKEMON_REMOVED, {"pokemon": pokemon})
        return True

    def transfer_pokemon(self, pokemon: Pokemon, target_status: PokemonStatus) -> bool:
        if target_status == PokemonStatus.ACTIVE and len(self.active_pokemon) >= ACTIVE_PARTY_LIMIT:
            return False
        if target_status == PokemonStatus.ACTIVE:
            test_state = copy.deepcopy(self._game_state)
            for p in test_state.pokemon:
                if p.nickname == pokemon.nickname:
                    p.status = PokemonStatus.ACTIVE
                    break
            if not self._game_state.rule_strategy.validate_party(test_state):
                return False
        original_status = pokemon.status
        pokemon.status = target_status
        self._save_service.save_session(self._game_state)
        if target_status == PokemonStatus.DEAD:
            self._journal_service.add_dead_entry(pokemon)
        else:
            status_name = self._process_storage_status(target_status)
            self._journal_service.add_transfer_entry(pokemon, status_name)
        self._event_manager.publish(
            EventType.POKEMON_TRANSFERRED,
            {"previous_status": original_status, "new_status": target_status},
        )
        return True
