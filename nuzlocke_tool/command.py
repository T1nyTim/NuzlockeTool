import logging
from abc import ABC, abstractmethod
from collections.abc import Callable

from nuzlocke_tool.constants import TAB_BOXED_NAME, TAB_DEAD_NAME, TAB_PARTY_NAME
from nuzlocke_tool.container import Container
from nuzlocke_tool.models import GameState, Pokemon, PokemonStatus

LOGGER = logging.getLogger(__name__)


class Command(ABC):
    @abstractmethod
    def execute(self) -> None:
        pass

    @abstractmethod
    def undo(self) -> None:
        pass


class AddPokemonCommand(Command):
    def __init__(
        self,
        container: Container,
        game_state: GameState,
        pokemon: Pokemon,
        on_success: Callable | None = None,
    ) -> None:
        self._container = container
        self._game_state = game_state
        self._journal_service = self._container.journal_service_factory(self._game_state)
        self._on_success = on_success
        self._pokemon = pokemon
        self._save_service = self._container.save_service()

    def execute(self) -> None:
        self._game_state.pokemon.append(self._pokemon)
        self._game_state.encounters.append(self._pokemon.encountered)
        self._save_service.save_session(self._game_state)
        self._journal_service.add_capture_entry(self._pokemon)
        if self._on_success:
            self._on_success()

    def undo(self) -> None:
        self._game_state.pokemon.remove(self._pokemon)
        if not any(p.encountered == self._pokemon.encountered for p in self._game_state.pokemon):
            self._game_state.encounters.remove(self._pokemon.encountered)
        self._save_service.save_session(self._game_state)


class EditPokemonCommand(Command):
    def __init__(
        self,
        container: Container,
        game_state: GameState,
        pokemon: Pokemon,
        on_success: Callable | None = None,
    ) -> None:
        self._container = container
        self._game_state = game_state
        self._journal_service = self._container.journal_service_factory(self._game_state)
        self._on_success = on_success
        self._original_values = {
            "nickname": pokemon.nickname,
            "species": pokemon.species,
            "level": pokemon.level,
            "moves": pokemon.moves.copy(),
            "dvs": pokemon.dvs.copy(),
            "encountered": pokemon.encountered,
        }
        self._pokemon = pokemon
        self._pokemon_repository = self._container.pokemon_repository()
        self._save_service = self._container.save_service()

    def execute(self) -> None:
        current_species = self._original_values["species"]
        pokemon_data = self._pokemon_repository.get_by_id(current_species)
        if "evolve" in pokemon_data and self._pokemon.species in pokemon_data["evolve"]:
            self._journal_service.add_evolved_entry(self._pokemon, current_species)
        self._save_service.save_session(self._game_state)
        if self._on_success:
            self._on_success()

    def undo(self) -> None:
        self._pokemon.nickname = self._original_values["nickname"]
        self._pokemon.species = self._original_values["species"]
        self._pokemon.level = self._original_values["level"]
        self._pokemon.moves = self._original_values["moves"].copy()
        self._pokemon.dvs = self._original_values["dvs"].copy()
        self._pokemon.encountered = self._original_values["encountered"]
        self._save_service.save_session(self._game_state)


class TransferPokemonCommand(Command):
    def __init__(
        self,
        container: Container,
        game_state: GameState,
        pokemon: Pokemon,
        target_status: PokemonStatus,
        on_success: Callable | None = None,
    ) -> None:
        self._container = container
        self._game_state = game_state
        self._journal_service = self._container.journal_service_factory(self._game_state)
        self._on_success = on_success
        self._original_status = pokemon.status
        self._pokemon = pokemon
        self._save_service = self._container.save_service()
        self._target_status = target_status

    def execute(self) -> None:
        self._original_status = self._pokemon.status
        self._pokemon.status = self._target_status
        self._save_service.save_session(self._game_state)
        if self._target_status == PokemonStatus.DEAD:
            self._journal_service.add_dead_entry(self._pokemon)
        else:
            status_name = self._process_storage_status(self._target_status)
            self._journal_service.add_transfer_entry(self._pokemon, status_name)
        if self._on_success:
            self._on_success()

    @staticmethod
    def _process_storage_status(status: PokemonStatus) -> str:
        status_map = {
            PokemonStatus.ACTIVE: TAB_PARTY_NAME,
            PokemonStatus.BOXED: TAB_BOXED_NAME,
            PokemonStatus.DEAD: TAB_DEAD_NAME,
        }
        return status_map[status]

    def undo(self) -> None:
        self._pokemon.status = self._original_status
        self._save_service.save_session(self._game_state)


class UpdateMoveCommand(Command):
    def __init__(  # noqa: PLR0913
        self,
        container: Container,
        game_state: GameState,
        pokemon: Pokemon,
        move_index: int,
        new_move: str,
        on_success: Callable | None = None,
    ) -> None:
        self._container = container
        self._game_state = game_state
        self._journal_service = self._container.journal_service_factory(self._game_state)
        self._move_index = move_index
        self._new_move = new_move
        self._old_move = pokemon.moves[move_index] if move_index < len(pokemon.moves) else ""
        self._on_success = on_success
        self._pokemon = pokemon
        self._save_service = self._container.save_service()

    def execute(self) -> None:
        self._pokemon.moves[self._move_index] = self._new_move
        if self._old_move == "":
            self._journal_service.add_learn_move_entry(self._pokemon.nickname, self._new_move)
            LOGGER.info("Pokemon %s learned move: %s", self._pokemon.nickname, self._new_move)
        elif self._new_move == "":
            self._journal_service.add_delete_move_entry(self._pokemon.nickname, self._old_move)
            LOGGER.info("Pokemon %s deleted move: %s", self._pokemon.nickname, self._old_move)
        else:
            self._journal_service.add_learn_move_entry(self._pokemon.nickname, self._new_move, self._old_move)
            LOGGER.info(
                "Pokemon %s learned move: %s (was: %s)",
                self._pokemon.nickname,
                self._new_move,
                self._old_move,
            )
        self._save_service.save_session(self._game_state)
        if self._on_success:
            self._on_success()

    def undo(self) -> None:
        self._pokemon.moves[self._move_index] = self._old_move
        self._save_service.save_session(self._game_state)


class CommandManager:
    def __init__(self, max_history: int = 100) -> None:
        self._history = []
        self._max_history = max_history

    def execute(self, command: Command) -> None:
        command.execute()
        self._history.append(command)
        if len(self._history) > self._max_history:
            self._history = self._history[-self.max_history :]

    def undo(self) -> None:
        if not self._history:
            return
        command = self._history.pop()
        command.undo()

    def undo_all(self) -> None:
        while self.history:
            self.undo()
