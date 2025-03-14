from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path


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
