import logging
from collections.abc import Callable

from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QContextMenuEvent, QPainter
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QMenu,
    QSizePolicy,
    QSpinBox,
    QStyle,
    QStyleOption,
    QVBoxLayout,
    QWidget,
)

from nuzlocke_tool.command import EditPokemonCommand, UpdateMoveCommand
from nuzlocke_tool.constants import (
    ALIGN_CENTER,
    LABEL_DETERMINANT_VALUES_SHORT,
    LABEL_LEVEL,
    LABEL_MOVES,
    LABEL_NICKNAME,
    LABEL_POKEMON_CARD_WIDTH,
    LABEL_SPECIES,
    LINE_HEIGHT,
    MENU_ACTION_EDIT_NAME,
    NO_SPACING,
    OBJECT_NAME_CARD_WIDGET,
    POKEMON_LEVEL_MAX,
    POKEMON_LEVEL_MIN,
    POKEMON_MOVES_LIMIT,
    SPACING,
    STYLE_SHEET_WIDGET_CARD,
    TAB_BOXED_NAME,
    TAB_DEAD_NAME,
    TAB_PARTY_NAME,
    WIDGET_POKEMON_CARD_WIDTH,
)
from nuzlocke_tool.container import Container
from nuzlocke_tool.gui.dialogs import PokemonDialog
from nuzlocke_tool.models import GameState, Pokemon, PokemonStatus
from nuzlocke_tool.utils import add_pokemon_image, load_pokemon_image

LOGGER = logging.getLogger(__name__)


class BasePokemonCardWidget(QWidget):
    transfer_requested = pyqtSignal(object, PokemonStatus)

    def __init__(
        self,
        container: Container,
        pokemon: Pokemon,
        game_state: GameState,
        parent: QWidget,
        transfer_options: list[tuple[str, str, Callable[[], bool] | None]] | None = None,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._game_state = game_state
        self._journal_service = self._container.journal_service_factory(self._game_state)
        self._pokemon = pokemon
        self._pokemon_repository = self._container.pokemon_repository()
        self._save_service = self._container.save_service()
        self._transfer_options = transfer_options if transfer_options is not None else []
        self.setObjectName(OBJECT_NAME_CARD_WIDGET)
        self.setStyleSheet(STYLE_SHEET_WIDGET_CARD)
        self._create_context_menu()

    def _add_image(self, layout: QLayout) -> None:
        self._image_label = add_pokemon_image(layout, self._pokemon.species, self)

    def _create_context_menu(self) -> None:
        self._context_menu = QMenu(self)
        for label, target, enabled_callback in self._transfer_options:
            transfer_action = QAction(f"Transfer to {label}", self)
            if enabled_callback:
                transfer_action.setEnabled(enabled_callback())
            transfer_action.triggered.connect(lambda _, t=target: self._transfer(t))
            self._context_menu.addAction(transfer_action)
        edit_action = QAction(MENU_ACTION_EDIT_NAME, self)
        edit_action.triggered.connect(self._edit)
        self._context_menu.addAction(edit_action)

    def _edit(self) -> None:
        dialog = PokemonDialog(
            self._container,
            self._game_state,
            self._pokemon.status,
            self,
            self._pokemon,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        command = EditPokemonCommand(
            self._container,
            self._game_state,
            self._pokemon,
            on_success=self._refresh,
        )
        main_window = self.window()
        main_window.command_manager.execute(command)
        LOGGER.info("Edited Pokemon: %s", self._pokemon)

    def _transfer(self, target: PokemonStatus) -> None:
        self.transfer_requested.emit(self._pokemon, target)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # noqa: N802
        self._context_menu.exec(event.globalPos())

    def paintEvent(self, event: QEvent) -> None:  # noqa: N802
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)
        super().paintEvent(event)


class ActivePokemonCardWidget(BasePokemonCardWidget):
    def __init__(
        self,
        container: Container,
        pokemon: Pokemon,
        game_state: GameState,
        parent: QWidget,
        transfer_enabled_callback: Callable[[], bool] | None = None,
    ) -> None:
        transfer_options = [
            (TAB_BOXED_NAME, PokemonStatus.BOXED, transfer_enabled_callback),
            (TAB_DEAD_NAME, PokemonStatus.DEAD, None),
        ]
        super().__init__(container, pokemon, game_state, parent, transfer_options)
        self._init_ui()

    def _create_dvs_widget(self) -> QWidget:
        dv_text = " | ".join(f"{stat}: {value}" for stat, value in self._pokemon.dvs.items())
        return QLabel(dv_text, self)

    def _create_group_widget(self, label_text: str, widget: QWidget) -> QWidget:
        group = QWidget(self)
        layout = QHBoxLayout(group)
        layout.setContentsMargins(NO_SPACING, NO_SPACING, NO_SPACING, NO_SPACING)
        layout.setSpacing(SPACING)
        label = QLabel(label_text, group)
        label.setMinimumWidth(LABEL_POKEMON_CARD_WIDTH)
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        layout.addWidget(label)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(widget)
        return group

    def _create_level_widget(self) -> QWidget:
        level_spin = QSpinBox(self)
        level_spin.setRange(POKEMON_LEVEL_MIN, POKEMON_LEVEL_MAX)
        level_spin.setValue(self._pokemon.level)
        level_spin.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        level_spin.lineEdit().setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        level_spin.valueChanged.connect(self._on_level_changed)
        return level_spin

    def _create_moves_widget(self) -> QWidget:
        species_key = self._pokemon.species
        entry = self._pokemon_repository.get_by_id(species_key)
        moves_entry = entry["moves"] if entry and isinstance(entry, dict) and "moves" in entry else None
        moves_layout = QHBoxLayout()
        moves_layout.setContentsMargins(NO_SPACING, NO_SPACING, NO_SPACING, NO_SPACING)
        current_moves = self._pokemon.moves
        while len(current_moves) < POKEMON_MOVES_LIMIT:
            current_moves.append("")
        for i in range(POKEMON_MOVES_LIMIT):
            combo = QComboBox(self)
            combo.addItem("")
            if moves_entry and isinstance(moves_entry, list):
                for m in moves_entry:
                    combo.addItem(m)
            idx = combo.findText(current_moves[i])
            combo.setCurrentIndex(idx)
            combo.currentIndexChanged.connect(
                lambda _, i=i, combo=combo: self._move_learned(i, combo.currentText()),
            )
            moves_layout.addWidget(combo)
        moves_widget = QWidget(self)
        moves_widget.setLayout(moves_layout)
        return moves_widget

    def _create_species_widget(self) -> QWidget:
        species_key = self._pokemon.species
        entry = self._pokemon_repository.get_by_id(species_key)
        if entry and isinstance(entry, dict) and "evolve" in entry:
            species_options = [self._pokemon.species, *entry.get("evolve", [])]
            species_combo = QComboBox(self)
            for opt in species_options:
                species_combo.addItem(self._process_species_name(opt), opt)
            species_combo.setCurrentIndex(species_options.index(self._pokemon.species))
            species_combo.currentIndexChanged.connect(self._on_species_changed)
            return species_combo
        return QLabel(self._process_species_name(self._pokemon.species), self)

    def _init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(SPACING, SPACING, SPACING, SPACING)
        main_layout.setSpacing(SPACING)
        self._add_image(main_layout)
        details_widget = QWidget(self)
        self._details_layout = QGridLayout(details_widget)
        self._details_layout.setContentsMargins(NO_SPACING, NO_SPACING, NO_SPACING, NO_SPACING)
        self._details_layout.setSpacing(SPACING)
        self._details_layout.setRowMinimumHeight(0, LINE_HEIGHT)
        self._nickname_label = QLabel(self._pokemon.nickname, self)
        nickname_group = self._create_group_widget(LABEL_NICKNAME, self._nickname_label)
        self._details_layout.addWidget(nickname_group, 0, 0)
        self._species_widget = self._create_species_widget()
        self._species_group = self._create_group_widget(LABEL_SPECIES, self._species_widget)
        self._details_layout.addWidget(self._species_group, 0, 1)
        self._level_spin = self._create_level_widget()
        level_group = self._create_group_widget(LABEL_LEVEL, self._level_spin)
        self._details_layout.addWidget(level_group, 1, 0)
        self._dvs_label = self._create_dvs_widget()
        dvs_group = self._create_group_widget(LABEL_DETERMINANT_VALUES_SHORT, self._dvs_label)
        self._details_layout.addWidget(dvs_group, 1, 1)
        self._moves_widget = self._create_moves_widget()
        self._moves_group = self._create_group_widget(LABEL_MOVES, self._moves_widget)
        self._details_layout.addWidget(self._moves_group, 2, 0, 1, 2)
        main_layout.addWidget(details_widget)

    def _move_learned(self, index: int, new_move: str) -> None:
        command = UpdateMoveCommand(
            self._container,
            self._game_state,
            self._pokemon,
            index,
            new_move,
            on_success=self._refresh_moves,
        )
        main_window = self.window()
        main_window.command_manager.execute(command)

    def _on_level_changed(self, value: int) -> None:
        self._pokemon.level = value
        self._save_service.save_session(self._game_state)

    def _on_species_changed(self, index: int) -> None:
        new_species = self._species_widget.itemData(index)
        if new_species != self._pokemon.species:
            self._journal_service.add_evolved_entry(self._pokemon, self._pokemon.species)
            LOGGER.info("Pokemon evolved from %s to %s", self._pokemon.species, new_species)
            self._pokemon.species = new_species
            self._save_service.save_session(self._game_state)
            self._refresh_species()
            self._refresh_moves()

    @staticmethod
    def _process_species_name(name: str) -> str:
        if name == "Nidoran (F)":
            return "Nidoran ♀"
        if name == "Nidoran (M)":
            return "Nidoran ♂"
        return name

    def _refresh(self) -> None:
        self._refresh_species()
        self._nickname_label.setText(self._pokemon.nickname)
        self._level_spin.setValue(self._pokemon.level)
        dv_text = " | ".join(f"{stat}: {value}" for stat, value in self._pokemon.dvs.items())
        self._dvs_label.setText(dv_text)
        self._details_layout.removeWidget(self._moves_group)
        self._refresh_moves()

    def _refresh_moves(self) -> None:
        self._moves_group.deleteLater()
        self._moves_widget = self._create_moves_widget()
        self._moves_group = self._create_group_widget(LABEL_MOVES, self._moves_widget)
        self._details_layout.addWidget(self._moves_group, 2, 0, 1, 2)

    def _refresh_species(self) -> None:
        pixmap = load_pokemon_image(self._pokemon.species)
        self._image_label.setPixmap(pixmap)
        self._details_layout.removeWidget(self._species_group)
        self._species_group.deleteLater()
        self._species_widget = self._create_species_widget()
        self._species_group = self._create_group_widget(LABEL_SPECIES, self._species_widget)
        self._details_layout.addWidget(self._species_group, 0, 1)


class StoragePokemonCardWidget(BasePokemonCardWidget):
    def __init__(
        self,
        container: Container,
        pokemon: Pokemon,
        game_state: str,
        parent: QWidget,
        transfer_options: list[tuple[str, str, Callable[[], bool] | None]] | None = None,
    ) -> None:
        super().__init__(container, pokemon, game_state, parent, transfer_options)
        self.setFixedSize(WIDGET_POKEMON_CARD_WIDTH, WIDGET_POKEMON_CARD_WIDTH)
        self._init_ui()

    def _add_level(self, layout: QVBoxLayout) -> None:
        self._level_label = QLabel(f"Lv {self._pokemon.level}", self)
        self._level_label.setAlignment(ALIGN_CENTER)
        layout.addWidget(self._level_label)

    def _add_nickname(self, layout: QVBoxLayout) -> None:
        self._nickname_label = QLabel(self._pokemon.nickname, self)
        self._nickname_label.setAlignment(ALIGN_CENTER)
        layout.addWidget(self._nickname_label)

    def _add_species(self, layout: QVBoxLayout) -> None:
        self._species_label = QLabel(self._pokemon.species, self)
        self._species_label.setAlignment(ALIGN_CENTER)
        layout.addWidget(self._species_label)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING, SPACING, SPACING, SPACING)
        layout.setSpacing(SPACING)
        self._add_image(layout)
        self._add_nickname(layout)
        self._add_species(layout)
        self._add_level(layout)

    def _refresh(self) -> None:
        pixmap = load_pokemon_image(self._pokemon.species)
        self._image_label.setPixmap(pixmap)
        self._nickname_label.setText(self._pokemon.nickname)
        self._species_label.setText(self._pokemon.species)
        self._level_label.setText(f"Lv {self._pokemon.level}")


class BoxedPokemonCardWidget(StoragePokemonCardWidget):
    def __init__(
        self,
        container: Container,
        pokemon: Pokemon,
        game_state: GameState,
        parent: QWidget,
        transfer_enabled_callback: Callable[[], bool] | None = None,
    ) -> None:
        transfer_options = [
            (TAB_PARTY_NAME, PokemonStatus.ACTIVE, transfer_enabled_callback),
            (TAB_DEAD_NAME, PokemonStatus.DEAD, None),
        ]
        super().__init__(container, pokemon, game_state, parent, transfer_options)


class DeadPokemonCardWidget(StoragePokemonCardWidget):
    def __init__(
        self,
        container: Container,
        pokemon: Pokemon,
        game_state: GameState,
        parent: QWidget,
        transfer_enabled_callback: Callable[[], bool] | None = None,
    ) -> None:
        transfer_options = [
            (TAB_PARTY_NAME, PokemonStatus.ACTIVE, transfer_enabled_callback),
            (TAB_BOXED_NAME, PokemonStatus.BOXED, None),
        ]
        super().__init__(container, pokemon, game_state, parent, transfer_options)
