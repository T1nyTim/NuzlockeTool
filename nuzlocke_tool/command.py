import copy
from abc import ABC, abstractmethod
from collections.abc import Callable

from nuzlocke_tool.container import Container
from nuzlocke_tool.models.models import GameState, Pokemon, PokemonStatus
from nuzlocke_tool.models.view_models import PokemonCardViewModel
from nuzlocke_tool.services.pokemon_service import PokemonService


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

    def execute(self) -> bool:
        success = self._pokemon_service.add_pokemon(self._pokemon)
        if success and self._on_success:
            self._on_success()
        return success

    def undo(self) -> None:
        self._pokemon_service.remove_pokemon(self._pokemon)
        if self._on_success:
            self._on_success()


class EditPokemonCommand(Command):
    def __init__(
        self,
        container: Container,
        game_state: GameState,
        pokemon: Pokemon,
        original_pokemon: Pokemon,
        pokemon_service: PokemonService,
        view_model: PokemonCardViewModel,
        on_success: Callable | None = None,
    ) -> None:
        self._container = container
        self._game_state = game_state
        self._on_success = on_success
        self._original_pokemon = original_pokemon
        self._pokemon = pokemon
        self._pokemon_service = pokemon_service
        self._save_service = self._container.save_service()
        self._view_model = view_model
        self._original_view_model_state = {
            "nickname": self._view_model.nickname,
            "species": self._view_model.species,
            "level": self._view_model.level,
            "moves": self._view_model.moves.copy(),
            "dvs": self._view_model.dvs.copy(),
            "encountered": self._view_model.encountered,
        }

    def execute(self) -> bool:
        success = self._pokemon_service.edit_pokemon(self._pokemon, self._original_pokemon.species)
        if success:
            self._view_model.nickname = self._pokemon.nickname
            self._view_model.species = self._pokemon.species
            self._view_model.level = self._pokemon.level
            self._view_model.moves = self._pokemon.moves.copy()
            self._view_model.dvs = self._pokemon.dvs.copy()
            if self._original_pokemon.species != self._pokemon.species:
                view_model_factory = self._container.view_model_factory()
                new_view_model = view_model_factory.create_pokemon_card_viewmodel(
                    self._pokemon,
                    self._view_model.card_type,
                )
                self._view_model.can_evolve = new_view_model.can_evolve
                self._view_model.evolution_options = new_view_model.evolution_options.copy()
                self._view_model.available_moves = new_view_model.available_moves.copy()
                self._view_model.image_path = new_view_model.image_path
        if success and self._on_success:
            self._on_success()
        return success

    def undo(self) -> None:
        self._pokemon.nickname = self._original_pokemon.nickname
        self._pokemon.species = self._original_pokemon.species
        self._pokemon.level = self._original_pokemon.level
        self._pokemon.moves = copy.deepcopy(self._original_pokemon.moves)
        self._pokemon.dvs = copy.deepcopy(self._original_pokemon.dvs)
        self._pokemon.encountered = self._original_pokemon.encountered
        self._view_model.nickname = self._original_view_model_state["nickname"]
        self._view_model.species = self._original_view_model_state["species"]
        self._view_model.level = self._original_view_model_state["level"]
        self._view_model.moves = self._original_view_model_state["moves"].copy()
        self._view_model.dvs = self._original_view_model_state["dvs"].copy()
        if self._pokemon.species != self._original_pokemon.species:
            view_model_factory = self._container.view_model_factory()
            original_view_model = view_model_factory.create_pokemon_card_viewmodel(
                self._original_pokemon,
                self._view_model.card_type,
            )
            self._view_model.can_evolve = original_view_model.can_evolve
            self._view_model.evolution_options = original_view_model.evolution_options.copy()
            self._view_model.available_moves = original_view_model.available_moves.copy()
            self._view_model.image_path = original_view_model.image_path
        self._save_service.save_session(self._game_state)
        if self._on_success:
            self._on_success()


class TransferPokemonCommand(Command):
    def __init__(
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

    def execute(self) -> bool:
        self._original_status = self._pokemon.status
        success = self._pokemon_service.transfer_pokemon(self._pokemon, self._target_status)
        if success and self._on_success:
            self._on_success()
        return success

    def undo(self) -> None:
        self._pokemon.status = self._original_status
        self._save_service.save_session(self._game_state)
        if self._on_success:
            self._on_success()


class UpdateMoveCommand(Command):
    def __init__(
        self,
        container: Container,
        game_state: GameState,
        pokemon: Pokemon,
        move_index: int,
        new_move: str,
        pokemon_service: PokemonService,
        view_model: PokemonCardViewModel,
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
        self._view_model = view_model

    def execute(self) -> bool:
        success = self._pokemon_service.learn_move(self._pokemon, self._move_index, self._new_move)
        if success:
            if self._move_index < len(self._view_model.moves):
                self._view_model.moves[self._move_index] = self._new_move
            else:
                while len(self._view_model.moves) <= self._move_index:
                    self._view_model.moves.append("")
                self._view_model.moves[self._move_index] = self._new_move
        if success and self._on_success:
            self._on_success()
        return success

    def undo(self) -> None:
        self._pokemon.moves[self._move_index] = self._old_move
        self._view_model.moves[self._move_index] = self._old_move
        self._save_service.save_session(self._game_state)
        if self._on_success:
            self._on_success()


class CommandManager:
    def __init__(self, max_history: int = 100) -> None:
        self._history = []
        self._max_history = max_history

    def execute(self, command: Command) -> bool:
        success = command.execute()
        if success:
            self._history.append(command)
            if len(self._history) > self._max_history:
                self._history = self._history[-self.max_history :]
        return success

    def undo(self) -> None:
        if not self._history:
            return
        command = self._history.pop()
        command.undo()

    def undo_all(self) -> None:
        while self.history:
            self.undo()
