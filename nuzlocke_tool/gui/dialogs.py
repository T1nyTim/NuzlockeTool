import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QWidget,
)

from nuzlocke_tool.config import PathConfig
from nuzlocke_tool.constants import (
    BUTTON_CANCEL,
    BUTTON_OK,
    DIALOG_ADD_POKEMON_TITLE,
    DIALOG_NEW_SESSION_TITLE,
    LABEL_ATTACK_SHORT,
    LABEL_CHECKBOX_SUBREGIONS,
    LABEL_DEFENSE_SHORT,
    LABEL_DETERMINANT_VALUES_SHORT,
    LABEL_ENCOUNTER,
    LABEL_GAME_VERSION,
    LABEL_HEALTH_SHORT,
    LABEL_LEVEL,
    LABEL_MOVES,
    LABEL_NICKNAME,
    LABEL_RULESET,
    LABEL_SPECIAL_SHORT,
    LABEL_SPECIES,
    LABEL_SPEED_SHORT,
    MSG_BOX_MSG_INVALID_ENCOUNTER,
    MSG_BOX_MSG_INVALID_MOVE,
    MSG_BOX_MSG_INVALID_NICKNAME,
    MSG_BOX_MSG_INVALID_SPECIES,
    MSG_BOX_MSG_NO_ENCOUNTER,
    MSG_BOX_MSG_NO_MOVE_FIRST_ONLY,
    MSG_BOX_MSG_NO_NICKNAME,
    MSG_BOX_MSG_NO_RULESET,
    MSG_BOX_MSG_NO_SPECIES,
    MSG_BOX_MSG_NO_VERSION,
    MSG_BOX_TITLE_INPUT_ERR,
    NO_SPACING,
    POKEMON_DV_MAX,
    POKEMON_DV_MIN,
    POKEMON_LEVEL_MAX,
    POKEMON_LEVEL_MIN,
    POKEMON_MOVES_LIMIT,
    TOOLTIP_CHECKBOX_SUBREGIONS,
)
from nuzlocke_tool.data_loader import GameDataLoader
from nuzlocke_tool.models import GameState, Pokemon, PokemonStatus
from nuzlocke_tool.utils import load_yaml_file

LOGGER = logging.getLogger(__name__)


class BaseDialog(QDialog):
    def __init__(self, title: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self._form_layout = QFormLayout(self)
        self.setLayout(self._form_layout)

    def _setup_buttons(self) -> None:
        buttons = QDialogButtonBox(BUTTON_OK | BUTTON_CANCEL, self)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        self._form_layout.addRow(buttons)


class NewSessionDialog(BaseDialog):
    def __init__(self, rulesets: dict[str, dict[str, int | list[str]]], parent: QWidget) -> None:
        super().__init__(DIALOG_NEW_SESSION_TITLE, parent)
        self._rulesets = rulesets
        self._selected_game = None
        self._selected_generation = None
        self._selected_ruleset_name = None
        self._versions = load_yaml_file(PathConfig.versions_file())
        self._init_ui()

    def _init_ui(self) -> None:
        self._game_combo = QComboBox(self)
        self._game_combo.addItems(list(self._versions.keys()))
        self._game_combo.currentTextChanged.connect(self._on_game_changed)
        self._form_layout.addRow(LABEL_GAME_VERSION, self._game_combo)
        self._rules_combo = QComboBox(self)
        self._form_layout.addRow(LABEL_RULESET, self._rules_combo)
        self._sub_region_checkbox = QCheckBox(LABEL_CHECKBOX_SUBREGIONS, self)
        self._sub_region_checkbox.setToolTip(TOOLTIP_CHECKBOX_SUBREGIONS)
        self._form_layout.addRow(self._sub_region_checkbox)
        self._setup_buttons()
        self._on_game_changed(self._game_combo.currentText())

    def _on_game_changed(self, game: str) -> None:
        version_info = self._versions.get(game, {})
        self._selected_generation = version_info.get("generation")
        filtered = {
            name: info
            for name, info in self._rulesets.items()
            if info.get("earliest_gen") <= self._selected_generation
        }
        self._rules_combo.clear()
        self._rules_combo.addItems(list(filtered.keys()))

    def _validate_and_accept(self) -> None:
        self._selected_game = self._game_combo.currentText().strip()
        self._selected_ruleset_name = self._rules_combo.currentText().strip()
        if not self._selected_game:
            QMessageBox.warning(self, MSG_BOX_TITLE_INPUT_ERR, MSG_BOX_MSG_NO_VERSION)
            return
        if not self._selected_ruleset_name:
            QMessageBox.warning(self, MSG_BOX_TITLE_INPUT_ERR, MSG_BOX_MSG_NO_RULESET)
            return
        self.accept()

    @property
    def selection(self) -> tuple[str, str, str, bool]:
        return (
            self._selected_game,
            self._selected_ruleset_name,
            self._selected_generation,
            self._sub_region_checkbox.isChecked(),
        )


class PokemonDialog(BaseDialog):
    def __init__(
        self,
        game_state: GameState,
        game_data_loader: GameDataLoader,
        status: PokemonStatus,
        parent: QWidget,
        pokemon: Pokemon | None = None,
    ) -> None:
        super().__init__(DIALOG_ADD_POKEMON_TITLE, parent)
        self._game_data_loader = game_data_loader
        self._game_state = game_state
        self._moves_by_species = self._extract_moves_mapping()
        self._allowed_species = list(self._moves_by_species.keys())
        self._status = status
        self.pokemon = pokemon
        self._init_ui()

    def _extract_moves_mapping(self) -> dict[str, list[str]]:
        moves_mapping = {}
        for species, info in self._game_data_loader.pokemon_data.items():
            moves_mapping[species] = info["moves"]
        return moves_mapping

    def _init_ui(self) -> None:
        self._setup_nickname_section()
        self._setup_species_section()
        self._setup_level_section()
        self._setup_moves_section()
        self._setup_dv_section()
        self._setup_encounter_section()
        self._setup_buttons()

    def _setup_dv_section(self) -> None:
        dv_widget = QWidget(self)
        dv_layout = QHBoxLayout(dv_widget)
        dv_layout.setContentsMargins(NO_SPACING, NO_SPACING, NO_SPACING, NO_SPACING)
        self._dv_spins = {}
        for stat in [
            LABEL_HEALTH_SHORT,
            LABEL_ATTACK_SHORT,
            LABEL_DEFENSE_SHORT,
            LABEL_SPECIAL_SHORT,
            LABEL_SPEED_SHORT,
        ]:
            stat_label = QLabel(stat, self)
            spin = QSpinBox(self)
            spin.setRange(POKEMON_DV_MIN, POKEMON_DV_MAX)
            if self.pokemon is not None:
                spin.setValue(self.pokemon.dvs[stat])
            spin.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            spin.lineEdit().setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            self._dv_spins[stat] = spin
            dv_layout.addWidget(stat_label)
            dv_layout.addWidget(spin)
        self._form_layout.addRow(LABEL_DETERMINANT_VALUES_SHORT, dv_widget)

    def _setup_encounter_section(self) -> None:
        region_type = "Partial" if self._game_state.sub_region_clause else "Full"
        valid_locations = [
            location
            for location, info in self._game_data_loader.location_data.items()
            if (info.get("type") == region_type or info.get("type") is None)
            and self._game_state.game in info.get("games", [])
            and location not in self._game_state.encounters
        ]
        valid_locations.sort()
        self._encounter_edit = QLineEdit(self)
        if self.pokemon is not None:
            self._encounter_edit.setText(self.pokemon.encountered)
        completer = QCompleter(valid_locations)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._encounter_edit.setCompleter(completer)
        self._form_layout.addRow(LABEL_ENCOUNTER, self._encounter_edit)

    def _setup_level_section(self) -> None:
        self._level_spin = QSpinBox(self)
        self._level_spin.setRange(POKEMON_LEVEL_MIN, POKEMON_LEVEL_MAX)
        if self.pokemon is not None:
            self._level_spin.setValue(self.pokemon.level)
        self._level_spin.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._level_spin.lineEdit().setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self._form_layout.addRow(LABEL_LEVEL, self._level_spin)

    def _setup_moves_section(self) -> None:
        self._moves_edits = []
        moves_widget = QWidget(self)
        moves_layout = QHBoxLayout(moves_widget)
        moves_layout.setContentsMargins(NO_SPACING, NO_SPACING, NO_SPACING, NO_SPACING)
        for i in range(POKEMON_MOVES_LIMIT):
            move_edit = QLineEdit(self)
            if self.pokemon is not None and i < len(self.pokemon.moves):
                move_edit.setText(self.pokemon.moves[i])
            else:
                move_edit.setEnabled(False)
            moves_layout.addWidget(move_edit)
            self._moves_edits.append(move_edit)
        if self.pokemon is not None:
            self._update_moves_completer(self.pokemon.species)
        self._form_layout.addRow(LABEL_MOVES, moves_widget)

    def _setup_nickname_section(self) -> None:
        self._nickname_edit = QLineEdit(self)
        if self.pokemon is not None:
            self._nickname_edit.setText(self.pokemon.nickname)
        self._form_layout.addRow(LABEL_NICKNAME, self._nickname_edit)

    def _setup_species_section(self) -> None:
        self._species_edit = QLineEdit(self)
        species_completer = QCompleter(self._allowed_species)
        species_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._species_edit.setCompleter(species_completer)
        if self.pokemon is not None:
            self._species_edit.setText(self.pokemon.species)
        self._form_layout.addRow(LABEL_SPECIES, self._species_edit)
        self._species_edit.textChanged.connect(self._update_moves_completer)

    def _update_moves_completer(self, species_text: str) -> None:
        species = species_text.strip()
        allowed_moves = self._moves_by_species.get(species, [])
        for move_edit in self._moves_edits:
            completer = QCompleter(allowed_moves)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            move_edit.setCompleter(completer)
            move_edit.setEnabled(True)
            current_move = move_edit.text().strip()
            if species in self._allowed_species and current_move and current_move not in allowed_moves:
                move_edit.clear()

    def _validate_and_accept(self) -> None:
        error = self._validate_inputs()
        if error:
            QMessageBox.warning(self, MSG_BOX_TITLE_INPUT_ERR, error)
            return
        nickname = self._nickname_edit.text().strip()
        species = self._species_edit.text().strip()
        level = self._level_spin.value()
        moves = [edit.text().strip() for edit in self._moves_edits]
        dvs = {stat: spin.value() for stat, spin in self._dv_spins.items()}
        encountered = self._encounter_edit.text().strip()
        if self.pokemon is None:
            self.pokemon = Pokemon(nickname, species, level, level, moves, dvs, encountered, self._status)
        else:
            self.pokemon.nickname = nickname
            self.pokemon.species = species
            self.pokemon.level = level
            self.pokemon.moves = moves
            self.pokemon.dvs = dvs
            self.pokemon.encountered = encountered
        super().accept()

    def _validate_inputs(self) -> None:
        nickname = self._nickname_edit.text().strip()
        species = self._species_edit.text().strip()
        moves = [edit.text().strip() for edit in self._moves_edits]
        encountered = self._encounter_edit.text().strip()
        error = None
        if not nickname:
            error = MSG_BOX_MSG_NO_NICKNAME
        elif not isinstance(nickname, str):
            error = MSG_BOX_MSG_INVALID_NICKNAME
        elif not species:
            error = MSG_BOX_MSG_NO_SPECIES
        elif species not in self._allowed_species:
            error = MSG_BOX_MSG_INVALID_SPECIES
        elif not moves[0]:
            error = MSG_BOX_MSG_NO_MOVE_FIRST_ONLY
        elif moves[0] not in self._moves_by_species.get(species):
            error = MSG_BOX_MSG_INVALID_MOVE
        elif not encountered:
            error = MSG_BOX_MSG_NO_ENCOUNTER
        elif not isinstance(encountered, str):
            error = MSG_BOX_MSG_INVALID_ENCOUNTER
        return error
