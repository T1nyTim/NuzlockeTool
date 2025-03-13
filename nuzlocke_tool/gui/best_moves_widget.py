import math

from PyQt6.QtWidgets import (
    QCheckBox,
    QCompleter,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from nuzlocke_tool.constants import (
    ALIGN_CENTER,
    ALIGN_H_CENTER,
    ALIGN_TOP,
    BUTTON_CALC_MOVE,
    DOUBLE_ATTACK_MOVES,
    FLINCH_10_MOVES,
    FLINCH_30_MOVES,
    HIGH_CRIT_MOVES,
    LABEL_ATTACK,
    LABEL_CHECKBOX_LIGHT_SCREEN,
    LABEL_CHECKBOX_REFLECT,
    LABEL_DEFENDING_POKEMON,
    LABEL_DEFENSE_STAGE,
    LABEL_LEVEL,
    LABEL_NO_DEFENDING_POKEMON,
    LABEL_NO_MOVES,
    LABEL_PARTY_MEMBER,
    LABEL_SPECIAL,
    LABEL_SPECIAL_STAGE,
    LABEL_SPEED,
    MULTI_HIT_MOVES,
    OHKO_MOVES,
    ONE_BYTE,
    POKEMON_LEVEL_MAX,
    POKEMON_LEVEL_MIN,
    POKEMON_STAT_STAGE_MAX,
    POKEMON_STAT_STAGE_MIN,
    SELFDESTRUCT_MOVES,
    SPECIAL_TYPES,
    STAT_STAGE_MULTIPLIER,
    STATIC_DAMAGE_MOVES,
    SWIFT_MOVES,
    TYPE_CHART,
)
from nuzlocke_tool.data_loader import GameDataLoader
from nuzlocke_tool.models import PartyManager, Pokemon
from nuzlocke_tool.utils import add_pokemon_image, clear_layout, clear_widget, load_pokemon_image


class BestMovesToolWidget(QWidget):
    def __init__(
        self,
        game_data_loader: GameDataLoader,
        party_manager: PartyManager,
        parent: QWidget,
    ) -> None:
        super().__init__(parent)
        self._game_data_loader = game_data_loader
        self._party_manager = party_manager

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

    def _calculate_best_moves(self) -> None:
        clear_layout(self._results_layout)
        defending_species = self._pokemon_selector.text()
        if not defending_species:
            self._results_layout.addWidget(QLabel(LABEL_NO_DEFENDING_POKEMON, self))
            return
        defender_stats = self._get_defender_stats()
        move_results = []
        for idx, party_member in enumerate(self._party_manager.active):
            attacker_stats = self._get_attacker_stats(party_member, idx)
            for move_name in party_member.moves:
                if not move_name:
                    continue
                move_damage = self._calculate_move_damage(
                    party_member,
                    move_name,
                    attacker_stats,
                    defender_stats,
                )
                if not move_damage:
                    continue
                long_term_average, damage_min, damage_max = move_damage
                move_results.append(
                    (long_term_average, party_member.nickname, move_name, damage_min, damage_max),
                )
        move_results.sort(key=lambda x: x[0], reverse=True)
        self._results_layout.addWidget(
            QLabel(
                (
                    f"Defending {defending_species} at level {defender_stats['level']} with "
                    f"{defender_stats['hp']} HP"
                ),
                self,
            ),
        )
        if not move_results:
            self._results_layout.addWidget(QLabel(LABEL_NO_MOVES, self))
            return
        for i, (lta, nickname, move_name, dmg_min, dmg_max) in enumerate(move_results[:5]):
            result_text = (
                f"{i + 1}. {nickname}'s {move_name}: Damage Range = {dmg_min} - {dmg_max} (Long-Term "
                f"Average = {lta:.1f})"
            )
            self._results_layout.addWidget(QLabel(result_text, self))

    def _calculate_damage_components(
        self,
        move_name: str,
        move_data: dict[str, dict[str, int | str]],
        party_member: Pokemon,
        attacker_stats: dict[str, int | list[str]],
        defender_stats: dict[str, str | int | list[str]],
    ) -> tuple[int, int]:
        move_type = move_data.get("type")
        is_special = move_type in SPECIAL_TYPES
        move_power = int(move_data.get("power"))
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
        if not is_special and self._reflect_checkbox.isChecked():
            noncrit_defense *= 2
        if is_special and self._light_screen_checkbox.isChecked():
            noncrit_defense *= 2
        if move_name in SELFDESTRUCT_MOVES:
            noncrit_defense = math.floor(noncrit_defense / 2)
            crit_defense = math.floor(crit_defense / 2)
        if noncrit_attack > ONE_BYTE or noncrit_defense > ONE_BYTE:
            noncrit_attack = math.floor(noncrit_attack / 4)
            noncrit_defense = math.floor(noncrit_defense / 4)
        stab = 1.5 if move_type in attacker_stats["types"] else 1.0
        type_chart_for_move = TYPE_CHART.get(move_type)
        defender_types = defender_stats["types"]
        type1_multi = type_chart_for_move.get(defender_types[0], 1)
        type2_multi = type_chart_for_move.get(defender_types[1], 1) if len(defender_types) > 1 else 1
        normal_base = math.floor(2 * party_member.level / 5 + 2)
        critical_factor = (2 * party_member.level + 5) / (party_member.level + 5)
        crit_base = math.floor(2 * party_member.level * critical_factor / 5 + 2)
        normal_damage = max(
            1,
            math.floor(
                math.floor(
                    math.floor(
                        (
                            math.floor(
                                math.floor(normal_base * move_power * noncrit_attack / noncrit_defense) / 50,
                            )
                            + 2
                        )
                        * stab,
                    )
                    * type1_multi,
                )
                * type2_multi,
            ),
        )
        crit_damage = max(
            1,
            math.floor(
                math.floor(
                    math.floor(
                        (math.floor(math.floor(crit_base * move_power * crit_attack / crit_defense) / 50) + 2)
                        * stab,
                    )
                    * type1_multi,
                )
                * type2_multi,
            ),
        )
        return (normal_damage, crit_damage)

    def _calculate_move_damage(
        self,
        party_member: Pokemon,
        move_name: str,
        attacker_stats: dict[str, int | list[str]],
        defender_stats: dict[str, str | int | list[str]],
    ) -> tuple[float, int, int] | None:
        move_data = self._game_data_loader.move_data.get(move_name)
        special_damage_result = self._handle_special_damage_moves(
            move_name,
            move_data,
            party_member,
            defender_stats,
        )
        if special_damage_result:
            return special_damage_result
        move_power = int(move_data.get("power"))
        if move_power == 0:
            return None
        normal_damage, crit_damage = self._calculate_damage_components(
            move_name,
            move_data,
            party_member,
            attacker_stats,
            defender_stats,
        )
        crit_chance = (
            max(255, 8 * math.floor(attacker_stats["base_spd"] / 2)) / 256
            if move_name in HIGH_CRIT_MOVES
            else math.floor(attacker_stats["spd"] / 2) / 256
        )
        weighted_damage = (normal_damage * (1 - crit_chance) + crit_damage * crit_chance) * 235 / 255
        move_accuracy = float(move_data.get("accuracy"))
        accuracy_rate = 1 if move_name in SWIFT_MOVES else move_accuracy * 255 / 25600
        long_term_average = weighted_damage * accuracy_rate
        return self._apply_additional_modifiers(move_name, long_term_average, normal_damage)

    def _compute_stats(
        self,
        pokemon_data: dict[str, dict[str, int | list[str]]],
        stat: str,
        pokemon: Pokemon | None = None,
        stat_stage: int | None = None,
        level: int | None = None,
    ) -> tuple[int, int]:
        base = pokemon_data.get(stat.lower())
        dv = pokemon.dvs.get(stat) if pokemon else 0
        level = level if level else pokemon.level
        base_stat = math.floor((base + dv) * 2 * level / 100)
        if stat == "hp":
            base_stat += level + 10
        else:
            base_stat += 5
        modified_stat = (
            math.floor(base_stat * STAT_STAGE_MULTIPLIER.get(stat_stage)) if stat_stage is not None else None
        )
        return base_stat, modified_stat

    def _get_attacker_stats(self, party_member: Pokemon, idx: int) -> dict[str, int | list[str]]:
        party_data = self._game_data_loader.pokemon_data.get(party_member.species)
        _, atk_spin, spe_spin, spd_spin = self._party_stage_spinboxes[idx]
        base_atk, modified_atk = self._compute_stats(party_data, "Atk", party_member, atk_spin.value())
        base_spe, modified_spe = self._compute_stats(party_data, "Spe", party_member, spe_spin.value())
        base_spd, modified_spd = self._compute_stats(party_data, "Spd", party_member, spd_spin.value())
        attacker_types = party_data.get("type")
        return {
            "base_atk": base_atk,
            "base_spe": base_spe,
            "base_spd": base_spd,
            "atk": modified_atk,
            "spe": modified_spe,
            "spd": modified_spd,
            "types": attacker_types,
        }

    def _get_defender_stats(self) -> dict[str, str | int | list[str]] | None:
        defending_species = self._pokemon_selector.text()
        if not defending_species:
            return None
        defending_pokemon = self._game_data_loader.pokemon_data.get(defending_species)
        level = self._level_spinner.value()
        def_stage = self._defense_spinner.value()
        spe_stage = self._special_spinner.value()
        base_hp, _ = self._compute_stats(defending_pokemon, "hp", level=level)
        base_def, modified_def = self._compute_stats(
            defending_pokemon,
            "def",
            stat_stage=def_stage,
            level=level,
        )
        base_spe, modified_spe = self._compute_stats(
            defending_pokemon,
            "spe",
            stat_stage=spe_stage,
            level=level,
        )
        defending_types = defending_pokemon.get("type")
        return {
            "species": defending_species,
            "level": level,
            "hp": base_hp,
            "base_def": base_def,
            "base_spe": base_spe,
            "def": modified_def,
            "spe": modified_spe,
            "types": defending_types,
        }

    def _handle_special_damage_moves(
        self,
        move_name: str,
        move_data: dict[str, dict[str, int | str]],
        party_member: Pokemon,
        defender_stats: dict[str, str | int | list[str]],
    ) -> tuple[float, int, int] | None:
        if move_name in OHKO_MOVES:
            move_accuracy = float(move_data.get("accuracy"))
            accuracy_rate = move_accuracy * 255 / 25600
            return (defender_stats["hp"] * accuracy_rate, 0, defender_stats["hp"])
        if move_name in STATIC_DAMAGE_MOVES:
            if move_name == "Sonicboom":
                static_val = damage_min = damage_max = 20
            elif move_name == "Dragon Rage":
                static_val = damage_min = damage_max = 40
            elif move_name in {"Night Shade", "Seismic Toss"}:
                static_val = damage_min = damage_max = party_member.level
            else:
                damage_min = 1
                damage_max = math.floor(party_member.level * 1.5)
                static_val = (damage_min + damage_max) / 2
            move_accuracy = float(move_data.get("accuracy"))
            accuracy_rate = move_accuracy * 255 / 25600
            return (static_val * accuracy_rate, damage_min, damage_max)
        return None

    def init_ui(self) -> None:
        clear_widget(self)
        if self.layout() is None:
            layout = QVBoxLayout(self)
            self.setLayout(layout)
        else:
            layout = self.layout()
        top_layout = QHBoxLayout()
        left_column = QVBoxLayout()
        left_column.addWidget(QLabel(LABEL_DEFENDING_POKEMON, self), alignment=ALIGN_CENTER)
        self._pokemon_selector = QLineEdit(self)
        pokemon_names = list(self._game_data_loader.pokemon_data.keys())
        completer = QCompleter(pokemon_names, self)
        self._pokemon_selector.setCompleter(completer)
        self._pokemon_selector.textChanged.connect(self._update_image)
        left_column.addWidget(self._pokemon_selector)
        self._pokemon_image = add_pokemon_image(left_column, self._pokemon_selector.text(), self)
        left_column.addWidget(self._pokemon_image, alignment=ALIGN_TOP | ALIGN_H_CENTER)
        top_layout.addLayout(left_column, 1)
        right_column = QFormLayout()
        self._level_spinner = QSpinBox(self)
        self._level_spinner.setRange(POKEMON_LEVEL_MIN, POKEMON_LEVEL_MAX)
        right_column.addRow(QLabel(LABEL_LEVEL, self), self._level_spinner)
        self._defense_spinner = QSpinBox(self)
        self._defense_spinner.setRange(POKEMON_STAT_STAGE_MIN, POKEMON_STAT_STAGE_MAX)
        right_column.addRow(QLabel(LABEL_DEFENSE_STAGE, self), self._defense_spinner)
        self._special_spinner = QSpinBox(self)
        self._special_spinner.setRange(POKEMON_STAT_STAGE_MIN, POKEMON_STAT_STAGE_MAX)
        right_column.addRow(QLabel(LABEL_SPECIAL_STAGE, self), self._special_spinner)
        checkboxes_layout = QHBoxLayout()
        self._light_screen_checkbox = QCheckBox(LABEL_CHECKBOX_LIGHT_SCREEN, self)
        checkboxes_layout.addWidget(self._light_screen_checkbox)
        self._reflect_checkbox = QCheckBox(LABEL_CHECKBOX_REFLECT, self)
        checkboxes_layout.addWidget(self._reflect_checkbox)
        right_column.addRow(checkboxes_layout)
        top_layout.addLayout(right_column, 1)
        layout.addLayout(top_layout)
        party_stage_widget = QWidget(self)
        self._party_stage_layout = QVBoxLayout(party_stage_widget)
        self.update_party_stage_section()
        layout.addWidget(party_stage_widget)
        calculate_button = QPushButton(BUTTON_CALC_MOVE, self)
        calculate_button.clicked.connect(self._calculate_best_moves)
        layout.addWidget(calculate_button)
        results_area = QWidget(self)
        self._results_layout = QVBoxLayout(results_area)
        layout.addWidget(results_area)
        results_area.setLayout(self._results_layout)
        layout.addStretch()

    def set_state(self, game_data_loader: GameDataLoader, party_manager: PartyManager) -> None:
        self._game_data_loader = game_data_loader
        self._party_manager = party_manager
        self.init_ui()

    def _update_image(self, selected_pokemon: str) -> None:
        pixmap = load_pokemon_image(selected_pokemon)
        self._pokemon_image.setPixmap(pixmap)

    def update_party_stage_section(self) -> None:
        if not hasattr(self, "_party_stage_layout"):
            return
        clear_layout(self._party_stage_layout)
        self._party_stage_spinboxes = []
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel(LABEL_PARTY_MEMBER, self), alignment=ALIGN_CENTER)
        header_layout.addWidget(QLabel(LABEL_ATTACK, self), alignment=ALIGN_CENTER)
        header_layout.addWidget(QLabel(LABEL_SPECIAL, self), alignment=ALIGN_CENTER)
        header_layout.addWidget(QLabel(LABEL_SPEED, self), alignment=ALIGN_CENTER)
        self._party_stage_layout.addLayout(header_layout)
        for party_member in self._party_manager.active:
            row_layout = QHBoxLayout()
            member_label = QLabel(str(party_member), self)
            atk_stage_spin = QSpinBox(self)
            atk_stage_spin.setRange(POKEMON_STAT_STAGE_MIN, POKEMON_STAT_STAGE_MAX)
            spe_stage_spin = QSpinBox(self)
            spe_stage_spin.setRange(POKEMON_STAT_STAGE_MIN, POKEMON_STAT_STAGE_MAX)
            spd_stage_spin = QSpinBox(self)
            spd_stage_spin.setRange(POKEMON_STAT_STAGE_MIN, POKEMON_STAT_STAGE_MAX)
            row_layout.addWidget(member_label)
            row_layout.addWidget(atk_stage_spin)
            row_layout.addWidget(spe_stage_spin)
            row_layout.addWidget(spd_stage_spin)
            self._party_stage_layout.addLayout(row_layout)
            self._party_stage_spinboxes.append((party_member, atk_stage_spin, spe_stage_spin, spd_stage_spin))
