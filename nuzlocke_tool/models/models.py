from dataclasses import dataclass, field
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


class EventType(Enum):
    POKEMON_ADDED = auto()
    POKEMON_EDITED = auto()
    POKEMON_TRANSFERRED = auto()
    POKEMON_REMOVED = auto()
    MOVE_UPDATED = auto()
    SESSION_LOADED = auto()
    SESSION_CREATED = auto()
    DECISION_MADE = auto()
    FAILED_ENCOUNTER_ADDED = auto()


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
class FailedEncounter:
    location: str
    species: str
    level: int


@dataclass
class GameState:
    game: str
    ruleset: str
    sub_region_clause: bool
    journal_file: Path | None
    save_file: Path | None
    pokemon: list[Pokemon]
    encounters: list[str]
    failed_encounters: list[FailedEncounter]
    decisions: dict[str, str]
    rule_strategy: "RuleStrategy" = None


@dataclass
class PokemonTypeCoverage:
    pokemon: Pokemon
    defensive_coverage: dict[str, float] = field(default_factory=dict)
    offensive_coverage: dict[str, float] = field(default_factory=dict)
