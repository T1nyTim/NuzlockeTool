from abc import ABC, abstractmethod
from typing import ClassVar

from nuzlocke_tool.models import GameState, PokemonStatus, RulesetData


class RuleStrategy(ABC):
    def __init__(self, ruleset_data: dict[str, RulesetData]) -> None:
        self._ruleset_data = ruleset_data

    @property
    def name(self) -> str:
        return self._ruleset_data.get("name", self.__class__.__name__)

    @property
    def rules_description(self) -> list[str]:
        return self._ruleset_data.get("rules")

    @abstractmethod
    def can_catch_pokemon(self, game_state: GameState, location: str) -> bool:
        pass

    @abstractmethod
    def validate_party(self, game_state: GameState) -> bool:
        pass


class Nuzlocke(RuleStrategy):
    def can_catch_pokemon(self, game_state: GameState, location: str) -> bool:
        return location not in game_state.encounters

    def validate_party(self, _: GameState) -> bool:
        return True


class Sololocke(RuleStrategy):
    def can_catch_pokemon(self, game_state: GameState, location: str) -> bool:
        return location not in game_state.encounters

    def validate_party(self, game_state: GameState) -> bool:
        active_pokemon = [p for p in game_state.pokemon if p.status == PokemonStatus.ACTIVE]
        return len(active_pokemon) <= 1


class RuleStrategyFactory:
    _strategies: ClassVar = {}
    _ruleset_data: ClassVar = {}

    @classmethod
    def initialize(cls, ruleset_data: dict[str, RulesetData]) -> None:
        cls._ruleset_data = ruleset_data
        strategy_classes = {
            cls_name: cls_obj
            for cls_name, cls_obj in globals().items()
            if isinstance(cls_obj, type) and issubclass(cls_obj, RuleStrategy) and cls_obj != RuleStrategy
        }
        for ruleset_name in ruleset_data:
            cls.register_strategy(ruleset_name, strategy_classes[ruleset_name])

    @classmethod
    def register_strategy(cls, name: str, strategy_class: RuleStrategy) -> None:
        cls._strategies[name] = strategy_class

    @classmethod
    def create_strategy(cls, name: str) -> RuleStrategy:
        if name not in cls._strategies:
            err_msg = f"Unknown ruleset: {name}"
            raise ValueError(err_msg)
        ruleset_data = cls._ruleset_data[name]
        return cls._strategies[name](ruleset_data)

    @classmethod
    def get_available_strategies(cls) -> dict[str, type[RuleStrategy]]:
        return cls._strategies.copy()
