import logging
import math
import random
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from nuzlocke_tool.config import PathConfig
from nuzlocke_tool.constants import (
    ACTIVE_PARTY_LIMIT,
    DOUBLE_ATTACK_MOVES,
    FLINCH_10_MOVES,
    FLINCH_30_MOVES,
    HIGH_CRIT_MOVES,
    MULTI_HIT_MOVES,
    OHKO_MOVES,
    ONE_BYTE,
    SELFDESTRUCT_MOVES,
    SPECIAL_TYPES,
    STAT_STAGE_MULTIPLIER,
    STATIC_DAMAGE_MOVES,
    SWIFT_MOVES,
    TAB_BOXED_NAME,
    TAB_DEAD_NAME,
    TAB_PARTY_NAME,
    TYPE_CHART,
)
from nuzlocke_tool.models import GameState, MoveData, Pokemon, PokemonData, PokemonStatus
from nuzlocke_tool.utils import load_yaml_file

if TYPE_CHECKING:
    from nuzlocke_tool.container import Container

LOGGER = logging.getLogger(__name__)


class BestMovesService:
    def __init__(self, container: "Container", game_state: GameState) -> None:
        self._container = container
        self._game_state = game_state
        self._move_repository = self._container.move_repository()
        self._pokemon_repository = self._container.pokemon_repository()

    def _apply_additional_modifiers(
        self,
        move_name: str,
        long_term_average: float,
        normal_damage: int,
    ) -> tuple[float, int, int]:
        damage_min = math.floor(normal_damage * 217 / 255)
        damage_max = normal_damage
        if move_name in MULTI_HIT_MOVES:
            damage_min *= 2
            damage_max *= 5
            long_term_average *= 3
        if move_name in DOUBLE_ATTACK_MOVES:
            damage_min *= 2
            damage_max *= 2
            long_term_average *= 2
        if move_name in FLINCH_10_MOVES:
            long_term_average *= 1.1
        if move_name in FLINCH_30_MOVES:
            long_term_average *= 1.3
        return (long_term_average, damage_min, damage_max)

    def _apply_stat_stage(self, base_stat: int, stat_stage: int) -> int:
        if stat_stage == 0:
            return base_stat
        return math.floor(base_stat * STAT_STAGE_MULTIPLIER[stat_stage])

    def calculate_best_moves_for_target(
        self,
        species: str,
        level: int,
        stat_stages: tuple[int, int],
        effects: tuple[bool, bool],
        attackers: list[tuple[Pokemon, int, int, int]],
    ) -> tuple[dict[str, str | int | list[str]], list[tuple[float, str, str, int, int]]]:
        if not species:
            return {}, []
        defender_stats = self._get_defender_stats(species, level, stat_stages)
        if not defender_stats:
            return {}, []
        move_results = []
        for pokemon, atk_stage, spe_stage, spd_stage in attackers:
            attacker_stats = self._get_attacker_stats(pokemon, (atk_stage, spe_stage, spd_stage))
            for move_name in pokemon.moves:
                if not move_name:
                    continue
                move_damage = self._calculate_move_damage(
                    pokemon,
                    move_name,
                    attacker_stats,
                    defender_stats,
                    effects,
                )
                if not move_damage:
                    continue
                long_term_avg, dmg_min, dmg_max = move_damage
                move_results.append((long_term_avg, pokemon.nickname, move_name, dmg_min, dmg_max))
        move_results.sort(key=lambda x: x[0], reverse=True)
        return defender_stats, move_results

    def _calculate_damage_components(  # noqa: PLR0913
        self,
        move_name: str,
        move_data: MoveData,
        party_member: Pokemon,
        attacker_stats: dict[str, int | list[str]],
        defender_stats: dict[str, str | int | list[str]],
        effects: tuple[bool, bool],
    ) -> tuple[int, int]:
        move_type = move_data["type"]
        is_special = move_type in SPECIAL_TYPES
        move_power = int(move_data["power"])
        if is_special:
            noncrit_attack = attacker_stats["spe"]
            noncrit_defense = defender_stats["spe"]
            crit_attack = attacker_stats["base_spe"]
            crit_defense = defender_stats["base_spe"]
        else:
            noncrit_attack = attacker_stats["atk"]
            noncrit_defense = defender_stats["def"]
            crit_attack = attacker_stats["base_atk"]
            crit_defense = defender_stats["base_def"]
        reflect_active, light_screen_active = effects
        if not is_special and reflect_active:
            noncrit_defense *= 2
        if is_special and light_screen_active:
            noncrit_defense *= 2
        if move_name in SELFDESTRUCT_MOVES:
            noncrit_defense = math.floor(noncrit_defense / 2)
            crit_defense = math.floor(crit_defense / 2)
        if noncrit_attack > ONE_BYTE or noncrit_defense > ONE_BYTE:
            noncrit_attack = math.floor(noncrit_attack / 4)
            noncrit_defense = math.floor(noncrit_defense / 4)
        stab = 1.5 if move_type in attacker_stats["types"] else 1.0
        type_chart_for_move = TYPE_CHART[move_type]
        defender_types = defender_stats["types"]
        type1_multi = type_chart_for_move.get(defender_types[0], 1)
        type2_multi = type_chart_for_move.get(defender_types[1], 1) if len(defender_types) > 1 else 1
        normal_base = math.floor(2 * party_member.level / 5 + 2)
        normal_damage = self._compute_final_damage(
            normal_base,
            move_power,
            noncrit_attack,
            noncrit_defense,
            stab,
            type1_multi,
            type2_multi,
        )
        critical_factor = (2 * party_member.level + 5) / (party_member.level + 5)
        crit_base = math.floor(2 * party_member.level * critical_factor / 5 + 2)
        crit_damage = self._compute_final_damage(
            crit_base,
            move_power,
            crit_attack,
            crit_defense,
            stab,
            type1_multi,
            type2_multi,
        )
        return normal_damage, crit_damage

    def _calculate_move_damage(
        self,
        pokemon: Pokemon,
        move_name: str,
        attacker_stats: dict[str, int | list[str]],
        defender_stats: dict[str, str | int | list[str]],
        effects: tuple[bool, bool],
    ) -> tuple[float, int, int] | None:
        move_data = self._move_repository.get_by_id(move_name)
        special_damage_result = self._handle_special_damage_moves(
            move_name,
            move_data,
            pokemon,
            defender_stats,
        )
        if special_damage_result:
            return special_damage_result
        move_power = int(move_data["power"])
        if move_power == 0:
            return None
        normal_damage, crit_damage = self._calculate_damage_components(
            move_name,
            move_data,
            pokemon,
            attacker_stats,
            defender_stats,
            effects,
        )
        crit_chance = (
            max(255, 8 * math.floor(attacker_stats["base_spd"] / 2)) / 256
            if move_name in HIGH_CRIT_MOVES
            else math.floor(attacker_stats["spd"] / 2) / 256
        )
        weighted_damage = (normal_damage * (1 - crit_chance) + crit_damage * crit_chance) * 235 / 255
        move_accuracy = float(move_data["accuracy"])
        accuracy_rate = 1 if move_name in SWIFT_MOVES else move_accuracy * 255 / 25600
        long_term_average = weighted_damage * accuracy_rate
        return self._apply_additional_modifiers(move_name, long_term_average, normal_damage)

    def _compute_base_stat(self, pokemon_data: PokemonData, stat: str, level: int, dv: int = 0) -> int:
        base = pokemon_data[stat.lower()]
        stat_value = math.floor((base + dv) * 2 * level / 100)
        if stat == "hp":
            stat_value += level + 10
        else:
            stat_value += 5
        return stat_value

    def _compute_base_stat_with_dv(self, pokemon_data: PokemonData, stat: str, pokemon: Pokemon) -> int:
        dv = pokemon.dvs[stat]
        return self._compute_base_stat(pokemon_data, stat, pokemon.level, dv)

    def _compute_final_damage(  # noqa: PLR0913
        self,
        base: int,
        power: int,
        attack: int,
        defense: int,
        stab: float,
        type1_multi: float,
        type2_multi: float,
    ) -> int:
        damage = math.floor(math.floor(base * power * attack / defense) / 50) + 2
        damage = math.floor(damage * stab)
        damage = math.floor(damage * type1_multi)
        damage = math.floor(damage * type2_multi)
        return max(1, damage)

    def _get_attacker_stats(
        self,
        pokemon: Pokemon,
        stat_stages: tuple[int, int, int],
    ) -> dict[str, int | list[str]]:
        pokemon_data = self._pokemon_repository.get_by_id(pokemon.species)
        atk_stage, spe_stage, spd_stage = stat_stages
        base_atk = self._compute_base_stat_with_dv(pokemon_data, "Atk", pokemon)
        modified_atk = self._apply_stat_stage(base_atk, atk_stage)
        base_spe = self._compute_base_stat_with_dv(pokemon_data, "Spe", pokemon)
        modified_spe = self._apply_stat_stage(base_spe, spe_stage)
        base_spd = self._compute_base_stat_with_dv(pokemon_data, "Spd", pokemon)
        modified_spd = self._apply_stat_stage(base_spd, spd_stage)
        return {
            "base_atk": base_atk,
            "base_spe": base_spe,
            "base_spd": base_spd,
            "atk": modified_atk,
            "spe": modified_spe,
            "spd": modified_spd,
            "types": pokemon_data["type"],
        }

    def _get_defender_stats(
        self,
        species: str,
        level: int,
        stat_stages: tuple[int, int],
    ) -> dict[str, str | int | list[str]]:
        defending_pokemon = self._pokemon_repository.get_by_id(species)
        def_stage, spe_stage = stat_stages
        base_hp = self._compute_base_stat(defending_pokemon, "hp", level)
        base_def = self._compute_base_stat(defending_pokemon, "def", level)
        modified_def = self._apply_stat_stage(base_def, def_stage)
        base_spe = self._compute_base_stat(defending_pokemon, "spe", level)
        modified_spe = self._apply_stat_stage(base_spe, spe_stage)
        return {
            "species": species,
            "level": level,
            "hp": base_hp,
            "base_def": base_def,
            "base_spe": base_spe,
            "def": modified_def,
            "spe": modified_spe,
            "types": defending_pokemon["type"],
        }

    def _handle_special_damage_moves(
        self,
        move_name: str,
        move_data: MoveData,
        party_member: Pokemon,
        defender_stats: dict[str, str | int | list[str]],
    ) -> tuple[float, int, int] | None:
        if move_name in OHKO_MOVES:
            move_accuracy = float(move_data["accuracy"])
            accuracy_rate = move_accuracy * 255 / 25600
            return (defender_stats["hp"] * accuracy_rate, 0, defender_stats["hp"])
        if move_name in STATIC_DAMAGE_MOVES:
            if move_name == "Sonicboom":
                static_val = damage_min = damage_max = 20
            elif move_name == "Dragon Rage":
                static_val = damage_min = damage_max = 40
            elif move_name in {"Night Shade", "Seismic Toss"}:
                static_val = damage_min = damage_max = party_member.level
            elif move_name == "Psywave":
                damage_min = 1
                damage_max = math.floor(party_member.level * 1.5)
                static_val = (damage_min + damage_max) / 2
            move_accuracy = float(move_data["accuracy"])
            accuracy_rate = move_accuracy * 255 / 25600
            return (static_val * accuracy_rate, damage_min, damage_max)
        return None


class GameService:
    def __init__(self, container: "Container") -> None:
        self._container = container
        self._save_service = self._container.save_service()

    @staticmethod
    def _create_journal_file(game: str, ruleset: str) -> Path:
        folder = PathConfig.journal_folder()
        base_name = f"{game}_{ruleset}_"
        i = 1
        while True:
            journal_file = folder / f"{base_name}{i}.journal"
            if not journal_file.exists():
                break
            i += 1
        journal_file.touch(exist_ok=False)
        return journal_file

    def new_game(self, game: str, ruleset: str, generation: str, sub_region_clause: bool) -> GameState:
        game_data_loader = self._container.game_data_loader()
        game_data_loader.load_pokemon_data(generation)
        game_data_loader.load_move_data(generation)
        journal_file = self._create_journal_file(game, ruleset)
        save_file = self._save_service.create_save_file(game, ruleset)
        game_state = GameState(game, ruleset, sub_region_clause, journal_file, save_file, [], [], {})
        journal_service = self._container.journal_service_factory(game_state)
        journal_service.add_new_session_entry(game, ruleset)
        if sub_region_clause:
            journal_service.add_clause_entry("Sub-Region")
        return game_state

    def load_game(self, save_path: Path) -> GameState:
        game_state = self._save_service.load_session(save_path)
        versions = load_yaml_file(PathConfig.versions_file())
        version_info = versions[game_state.game]
        generation = version_info["generation"]
        game_data_loader = self._container.game_data_loader()
        game_data_loader.load_pokemon_data(generation)
        game_data_loader.load_move_data(generation)
        return game_state

    def save_game(self, game_state: GameState) -> None:
        self._save_service.save_session(game_state)


class JournalService:
    def __init__(self, game_state: GameState) -> None:
        self._journal_file = game_state.journal_file

    def add_capture_entry(self, pokemon: Pokemon) -> None:
        status_map = {PokemonStatus.ACTIVE: "Party", PokemonStatus.BOXED: "Box"}
        entry = f"Caught {pokemon} in {pokemon.encountered}. Added to {status_map[pokemon.status]}."
        self._append_entry(entry)

    def add_clause_entry(self, clause: str) -> None:
        entry = f"New session is using the {clause} clause."
        self._append_entry(entry)

    def add_dead_entry(self, pokemon: Pokemon) -> None:
        entry = f"{pokemon} has Died."
        self._append_entry(entry)

    def add_decision_entry(self, decision: str, outcome: str) -> None:
        entry = f"Randomly pick {decision}: {outcome}"
        self._append_entry(entry)

    def add_delete_move_entry(self, nickname: str, move: str) -> None:
        entry = f"{nickname} deleted move: {move}"
        self._append_entry(entry)

    def add_evolved_entry(self, pokemon: Pokemon, old_species: str) -> None:
        entry = f"{pokemon.nickname} evolved from {old_species} to {pokemon.species}"
        self._append_entry(entry)

    def add_learn_move_entry(self, nickname: str, move: str, old_move: str | None = None) -> None:
        entry = f"{nickname} learned move: {move}"
        if old_move:
            entry += f" (replacing {old_move})"
        self._append_entry(entry)

    def add_new_session_entry(self, game: str, ruleset: str) -> None:
        entry = f"Started new session in {game}."
        self._append_entry(entry)
        entry = f"New session is utilising the {ruleset} ruleset."
        self._append_entry(entry)

    def add_transfer_entry(self, pokemon: Pokemon, target: str) -> None:
        entry = f"Transferred {pokemon} to {target}."
        self._append_entry(entry)

    def _append_entry(self, entry: str) -> None:
        with self._journal_file.open("a") as f:
            f.write(f"{entry}\n")


class PokemonService:
    def __init__(self, container: "Container", game_state: GameState) -> None:
        self._container = container
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

    def add_pokemon(self, pokemon: Pokemon) -> None:
        self._game_state.pokemon.append(pokemon)
        self._game_state.encounters.append(pokemon.encountered)
        self._save_service.save_session(self._game_state)
        self._journal_service.add_capture_entry(pokemon)

    def edit_pokemon(self, pokemon: Pokemon, current_species: str) -> None:
        pokemon_data = self._pokemon_repository.get_by_id(current_species)
        self._save_service.save_session(self._game_state)
        if "evolve" in pokemon_data and pokemon.species in pokemon_data["evolve"]:
            self._journal_service.add_evolved_entry(pokemon, current_species)

    def learn_move(self, pokemon: Pokemon, index: int, new_move: str) -> None:
        old_move = pokemon.moves[index] if index < len(pokemon.moves) else ""
        pokemon.moves[index] = new_move
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

    @staticmethod
    def _process_storage_status(status: PokemonStatus) -> str:
        status_map = {
            PokemonStatus.ACTIVE: TAB_PARTY_NAME,
            PokemonStatus.BOXED: TAB_BOXED_NAME,
            PokemonStatus.DEAD: TAB_DEAD_NAME,
        }
        return status_map[status]

    def remove_pokemon(self, pokemon: Pokemon) -> None:
        self._game_state.pokemon.remove(pokemon)
        if not any(p.encountered == pokemon.encountered for p in self._game_state.pokemon):
            self._game_state.encounters.remove(pokemon.encountered)
        self._save_service.save_session(self._game_state)

    def transfer_pokemon(self, pokemon: Pokemon, target_status: PokemonStatus) -> None:
        pokemon.status = target_status
        self._save_service.save_session(self._game_state)
        if target_status == PokemonStatus.DEAD:
            self._journal_service.add_dead_entry(pokemon)
        else:
            status_name = self._process_storage_status(target_status)
            self._journal_service.add_transfer_entry(pokemon, status_name)


class RandomDecisionService:
    def __init__(self, container: "Container", game_state: GameState) -> None:
        self._container = container
        self._game_state = game_state
        self._journal_service = self._container.journal_service_factory(game_state)
        self._save_service = self._container.save_service()

    def make_decision(self, decision_key: str, decision_options: list[str], display_name: str) -> str:
        outcome = random.choice(decision_options)
        self._game_state.decisions[decision_key] = outcome
        self._save_service.save_session(self._game_state)
        self._journal_service.add_decision_entry(display_name, outcome)
        return outcome


class SaveService:
    @staticmethod
    def create_save_file(game: str, ruleset: str) -> Path:
        folder = PathConfig.save_folder()
        base_name = f"{game}_{ruleset}_"
        i = 1
        while True:
            save_file = folder / f"{base_name}{i}.sav"
            if not save_file.exists():
                break
            i += 1
        save_file.touch(exist_ok=False)
        LOGGER.info("Created new save file: %s", save_file)
        return save_file

    @staticmethod
    def load_session(filepath: Path) -> GameState:
        with filepath.open("r") as f:
            data = yaml.safe_load(f)
        data["journal_file"] = Path(data["journal_file"])
        data["save_file"] = Path(data["save_file"])
        pokemon_list = []
        for pokemon_dict in data["pokemon"]:
            status_str = pokemon_dict.pop("status")
            pokemon = Pokemon(**pokemon_dict, status=PokemonStatus[status_str])
            pokemon_list.append(pokemon)
        data["pokemon"] = pokemon_list
        LOGGER.info("Game loaded from %s", filepath)
        return GameState(**data)

    @staticmethod
    def save_session(game_state: GameState) -> None:
        game_state_dict = asdict(game_state)
        game_state_dict["journal_file"] = str(game_state_dict["journal_file"])
        game_state_dict["save_file"] = str(game_state_dict["save_file"])
        pokemon_list = []
        for pokemon in game_state_dict["pokemon"]:
            pokemon_dict = {k: v for k, v in pokemon.items() if k != "status"}
            pokemon_dict["status"] = pokemon["status"].name
            pokemon_list.append(pokemon_dict)
        game_state_dict["pokemon"] = pokemon_list
        with game_state.save_file.open("w") as f:
            yaml.dump(game_state_dict, f)
        LOGGER.info("Game saved to %s", game_state.save_file)

    def _append_entry(self, entry: str) -> None:
        with self._journal_file.open("a") as f:
            f.write(f"{entry}\n")
