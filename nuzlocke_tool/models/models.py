from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from nuzlocke_tool.rules import RuleStrategy


class LocationData(TypedDict):
    games: list[str]


class MoveData(TypedDict):
    power: int
    move_type: str
    accuracy: int


class PokemonData(TypedDict):
    atk: int
    df: int
    evolve: list[str]
    hp: int
    moves: list[str]
    spd: int
    spe: int
    pokemon_type: list[str]


class RulesetData(TypedDict):
    earliest_gen: int
    rules: list[str]


class PokemonCardType(Enum):
    ACTIVE = "active"
    BOXED = "boxed"
    DEAD = "dead"


class PokemonStatus(Enum):
    ACTIVE = auto()
    BOXED = auto()
    DEAD = auto()


@dataclass
class Pokemon:
    nickname: str
    species: str
    level: int
    caught_level: int
    moves: list[str]
    dvs: dict[str, int]
    encountered: str
    status: PokemonStatus

    def __str__(self) -> str:
        return f"{self.nickname} ({self.species}) - Lv {self.level}"


@dataclass
class GameState:
    game: str
    ruleset: str
    sub_region_clause: bool
    journal_file: Path | None
    save_file: Path | None
    pokemon: list[Pokemon]
    encounters: list[str]
    decisions: dict[str, str]
    rule_strategy: "RuleStrategy" = None
