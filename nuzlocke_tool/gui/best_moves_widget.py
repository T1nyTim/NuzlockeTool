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
    LABEL_ATTACK,
    LABEL_CHECKBOX_LIGHT_SCREEN,
    LABEL_CHECKBOX_REFLECT,
    LABEL_DEFENDING_POKEMON,
    LABEL_DEFENSE_STAGE,
    LABEL_LEVEL,
    LABEL_PARTY_MEMBER,
    LABEL_SPECIAL,
    LABEL_SPECIAL_STAGE,
    LABEL_SPEED,
    POKEMON_LEVEL_MAX,
    POKEMON_LEVEL_MIN,
    POKEMON_STAT_STAGE_MAX,
    POKEMON_STAT_STAGE_MIN,
)
from nuzlocke_tool.container import Container
from nuzlocke_tool.models.models import EventType, GameState
from nuzlocke_tool.models.view_models import BestMoveViewModel
from nuzlocke_tool.services.best_moves_service import BestMovesService
from nuzlocke_tool.services.pokemon_service import PokemonService
from nuzlocke_tool.utils.utils import add_pokemon_image, clear_layout, clear_widget, load_pokemon_image


class BestMovesToolWidget(QWidget):
    def __init__(self, container: Container, parent: QWidget) -> None:
        super().__init__(parent)
        self._container = container
        self._event_manager = self._container.event_manager()
        self._event_manager.subscribe(EventType.POKEMON_ADDED, self._on_pokemon_changed)
        self._event_manager.subscribe(EventType.POKEMON_EDITED, self._on_pokemon_changed)
        self._event_manager.subscribe(EventType.POKEMON_TRANSFERRED, self._on_pokemon_changed)
        self._event_manager.subscribe(EventType.POKEMON_REMOVED, self._on_pokemon_changed)
        self._game_state = self._container.game_state()
        self._best_moves_service = BestMovesService(self._container, self._game_state)
        self._pokemon_repository = self._container.pokemon_repository()
        self._pokemon_service = PokemonService(self._container, self._game_state)
        self._view_model = BestMoveViewModel()

    def __del__(self) -> None:
        self._event_manager.unsubscribe(EventType.POKEMON_ADDED, self._on_pokemon_changed)
        self._event_manager.unsubscribe(EventType.POKEMON_EDITED, self._on_pokemon_changed)
        self._event_manager.unsubscribe(EventType.POKEMON_TRANSFERRED, self._on_pokemon_changed)
        self._event_manager.unsubscribe(EventType.POKEMON_REMOVED, self._on_pokemon_changed)

    def _calculate_best_moves(self) -> None:
        clear_layout(self._results_layout)
        self._view_model.defending_pokemon = self._pokemon_selector.text()
        self._view_model.defending_level = self._level_spinner.value()
        self._view_model.defense_stage = self._defense_spinner.value()
        self._view_model.special_stage = self._special_spinner.value()
        self._view_model.reflect_active = self._reflect_checkbox.isChecked()
        self._view_model.light_screen_active = self._light_screen_checkbox.isChecked()
        if not self._view_model.has_valid_defender:
            self._results_layout.addWidget(QLabel(self._view_model.defender_display_text, self))
            return
        self._view_model.attacker_stages = []
        for party_member, atk_spin, spe_spin, spd_spin in self._party_stage_spinboxes:
            self._view_model.attacker_stages.append(
                (party_member, atk_spin.value(), spe_spin.value(), spd_spin.value()),
            )
        defender_stats, move_results = self._best_moves_service.calculate_best_moves_for_target(
            self._view_model.defending_pokemon,
            self._view_model.defending_level,
            (self._view_model.defense_stage, self._view_model.special_stage),
            (self._view_model.reflect_active, self._view_model.light_screen_active),
            self._view_model.attacker_stages,
        )
        if defender_stats:
            self._view_model.defending_hp = defender_stats.get("hp")
        self._view_model.move_results = move_results
        self._results_layout.addWidget(QLabel(self._view_model.defender_display_text, self))
        for result_text in self._view_model.formatted_results:
            self._results_layout.addWidget(QLabel(result_text, self))

    def _on_pokemon_changed(self, _: dict) -> None:
        self.update_party_stage_section()

    def _update_image(self, selected_pokemon: str) -> None:
        pixmap = load_pokemon_image(selected_pokemon)
        self._pokemon_image.setPixmap(pixmap)

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
        pokemon_names = self._pokemon_repository.get_all_species()
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
        layout.addStretch()

    def set_state(self, game_state: GameState) -> None:
        self._best_moves_service = BestMovesService(self._container, game_state)
        self._game_state = game_state
        self._pokemon_service = PokemonService(self._container, game_state)
        self._view_model = BestMoveViewModel()
        self.init_ui()

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
        for party_member in self._pokemon_service.active_pokemon:
            row_layout = QHBoxLayout()
            member_label = QLabel(str(party_member), self)
            row_layout.addWidget(member_label)
            atk_stage_spin = QSpinBox(self)
            atk_stage_spin.setRange(POKEMON_STAT_STAGE_MIN, POKEMON_STAT_STAGE_MAX)
            row_layout.addWidget(atk_stage_spin)
            spe_stage_spin = QSpinBox(self)
            spe_stage_spin.setRange(POKEMON_STAT_STAGE_MIN, POKEMON_STAT_STAGE_MAX)
            row_layout.addWidget(spe_stage_spin)
            spd_stage_spin = QSpinBox(self)
            spd_stage_spin.setRange(POKEMON_STAT_STAGE_MIN, POKEMON_STAT_STAGE_MAX)
            row_layout.addWidget(spd_stage_spin)
            self._party_stage_layout.addLayout(row_layout)
            self._party_stage_spinboxes.append((party_member, atk_stage_spin, spe_stage_spin, spd_stage_spin))
