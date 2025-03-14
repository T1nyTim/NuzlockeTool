import copy
from abc import ABC, abstractmethod
from collections.abc import Callable

from nuzlocke_tool.container import Container
from nuzlocke_tool.models import GameState, Pokemon, PokemonStatus
from nuzlocke_tool.services import PokemonService


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
        pokemon: Pokemon,
        pokemon_service: PokemonService,
        on_success: Callable | None = None,
    ) -> None:
        self._container = container
        self._on_success = on_success
        self._pokemon = pokemon
        self._pokemon_service = pokemon_service

    def execute(self) -> None:
        self._pokemon_service.add_pokemon(self._pokemon)
        if self._on_success:
            self._on_success()

    def undo(self) -> None:
        self._pokemon_service.remove_pokemon(self._pokemon)
        if self._on_success:
            self._on_success()


class EditPokemonCommand(Command):
    def __init__(  # noqa: PLR0913
        self,
        container: Container,
        game_state: GameState,
        pokemon: Pokemon,
        original_pokemon: Pokemon,
        pokemon_service: PokemonService,
        on_success: Callable | None = None,
    ) -> None:
        self._container = container
        self._game_state = game_state
        self._on_success = on_success
        self._original_pokemon = original_pokemon
        self._pokemon = pokemon
        self._pokemon_service = pokemon_service
        self._save_service = self._container.save_service()

    def execute(self) -> None:
        self._pokemon_service.edit_pokemon(self._pokemon, self._original_pokemon.species)
        if self._on_success:
            self._on_success()

    def undo(self) -> None:
        self._pokemon.nickname = self._original_pokemon.nickname
        self._pokemon.species = self._original_pokemon.species
        self._pokemon.level = self._original_pokemon.level
        self._pokemon.moves = copy.deepcopy(self._original_pokemon.moves)
        self._pokemon.dvs = copy.deepcopy(self._original_pokemon.dvs)
        self._pokemon.encountered = self._original_pokemon.encountered
        self._save_service.save_session(self._game_state)
        if self._on_success:
            self._on_success()


class TransferPokemonCommand(Command):
    def __init__(  # noqa: PLR0913
        self,
        container: Container,
        game_state: GameState,
        pokemon: Pokemon,
        target_status: PokemonStatus,
        pokemon_service: PokemonService,
        on_success: Callable | None = None,
    ) -> None:
        self._container = container
        self._game_state = game_state
        self._on_success = on_success
        self._original_status = pokemon.status
        self._pokemon = pokemon
        self._pokemon_service = pokemon_service
        self._save_service = self._container.save_service()
        self._target_status = target_status

    def execute(self) -> None:
        self._original_status = self._pokemon.status
        self._pokemon_service.transfer_pokemon(self._pokemon, self._target_status)
        if self._on_success:
            self._on_success()

    def undo(self) -> None:
        self._pokemon.status = self._original_status
        self._save_service.save_session(self._game_state)
        if self._on_success:
            self._on_success()


class UpdateMoveCommand(Command):
    def __init__(  # noqa: PLR0913
        self,
        container: Container,
        game_state: GameState,
        pokemon: Pokemon,
        move_index: int,
        new_move: str,
        pokemon_service: PokemonService,
        on_success: Callable | None = None,
    ) -> None:
        self._container = container
        self._game_state = game_state
        self._move_index = move_index
        self._new_move = new_move
        self._old_move = pokemon.moves[move_index] if move_index < len(pokemon.moves) else ""
        self._on_success = on_success
        self._pokemon = pokemon
        self._pokemon_service = pokemon_service
        self._save_service = self._container.save_service()

    def execute(self) -> None:
        self._pokemon_service.learn_move(self._pokemon, self._move_index, self._new_move)
        if self._on_success:
            self._on_success()

    def undo(self) -> None:
        self._pokemon.moves[self._move_index] = self._old_move
        self._save_service.save_session(self._game_state)
        if self._on_success:
            self._on_success()


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
