from dataclasses import dataclass, field
from pathlib import Path

from nuzlocke_tool.constants import TAB_BOXED_NAME, TAB_DEAD_NAME, TAB_PARTY_NAME


@dataclass
class GameData:
    location_data: dict[str, dict[str, str | list[str]]]
    pokemon_data: dict[str, dict[str, int | list[str]]]
    move_data: dict[str, dict[str, int | str]]


@dataclass
class GameState:
    game: str
    ruleset: str
    sub_region_clause: bool
    journal_file: Path | None
    save_file: Path | None
    encounters: list[str]
    decisions: dict[str, str]


@dataclass
class Pokemon:
    nickname: str
    species: str
    level: int
    caught_level: int
    moves: list[str]
    dvs: dict[str, int]
    encountered: str

    def __str__(self) -> str:
        return f"{self.nickname} ({self.species}) - Lv {self.level}"


@dataclass
class PartyManager:
    active: list[Pokemon] = field(default_factory=list)
    boxed: list[Pokemon] = field(default_factory=list)
    dead: list[Pokemon] = field(default_factory=list)

    def add_pokemon(self, pokemon: Pokemon, area: str) -> None:
        if area == "active":
            self.active.append(pokemon)
        elif area == "boxed":
            self.boxed.append(pokemon)
        elif area == "dead":
            self.dead.append(pokemon)

    @property
    def all_pokemon(self) -> list[Pokemon]:
        return self.active + self.boxed + self.dead

    def get_status(self, pokemon: Pokemon) -> str:
        if pokemon in self.active:
            return TAB_PARTY_NAME
        if pokemon in self.boxed:
            return TAB_BOXED_NAME
        if pokemon in self.dead:
            return TAB_DEAD_NAME
        return "Unknown"

    def transfer(self, pokemon: Pokemon, target: str) -> None:
        if pokemon in self.active:
            self.active.remove(pokemon)
        elif pokemon in self.boxed:
            self.boxed.remove(pokemon)
        elif pokemon in self.dead:
            self.dead.remove(pokemon)
        if target == "active":
            self.active.append(pokemon)
        elif target == "boxed":
            self.boxed.append(pokemon)
        elif target == "dead":
            self.dead.append(pokemon)
