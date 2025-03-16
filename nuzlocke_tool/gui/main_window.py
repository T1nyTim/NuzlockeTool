import logging
from pathlib import Path

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from nuzlocke_tool.command import AddPokemonCommand, CommandManager, TransferPokemonCommand
from nuzlocke_tool.config import PathConfig
from nuzlocke_tool.constants import (
    ACTIVE_PARTY_LIMIT,
    ALIGN_LEFT,
    ALIGN_TOP,
    BUTTON_ADD_POKEMON,
    LABEL_TOOL_BEST_MOVE,
    LABEL_TOOL_RANDOM_DECISION,
    MAIN_WINDOW_TITLE,
    MENU_ACTION_EXIT_NAME,
    MENU_ACTION_LOAD_NAME,
    MENU_ACTION_NEW_NAME,
    MENU_ACTION_UNDO_NAME,
    MENU_EDIT_NAME,
    MENU_FILE_NAME,
    MSG_BOX_MSG_NO_DATA_FILE,
    MSG_BOX_MSG_PARTY_FULL,
    MSG_BOX_TITLE_NO_FILE,
    MSG_BOX_TITLE_PARTY_FULL,
    RESIZE_DELAY,
    SPACING,
    STYLE_SHEET_COMBO_BOX,
    TAB_BOXED_NAME,
    TAB_DEAD_NAME,
    TAB_ENCOUNTER_NAME,
    TAB_PARTY_NAME,
    TAB_RULES_NAME,
    TAB_TOOLS_NAME,
    WIDGET_POKEMON_CARD_WIDTH,
)
from nuzlocke_tool.container import Container
from nuzlocke_tool.gui.best_moves_widget import BestMovesToolWidget
from nuzlocke_tool.gui.card_widgets import (
    ActivePokemonCardWidget,
    BoxedPokemonCardWidget,
    DeadPokemonCardWidget,
)
from nuzlocke_tool.gui.dialogs import NewSessionDialog, PokemonDialog
from nuzlocke_tool.gui.encounters_tab import EncountersTab
from nuzlocke_tool.gui.random_decision_widget import RandomDecisionToolWidget
from nuzlocke_tool.models.models import EventType, GameState, Pokemon, PokemonCardType, PokemonStatus
from nuzlocke_tool.models.view_models import GameStateViewModel, PokemonCardViewModel
from nuzlocke_tool.services.game_service import GameService
from nuzlocke_tool.services.pokemon_service import PokemonService
from nuzlocke_tool.services.random_decision_service import RandomDecisionService
from nuzlocke_tool.utils import clear_layout, load_yaml_file

LOGGER = logging.getLogger(__name__)


class NuzlockeTrackerMainWindow(QMainWindow):
    def __init__(self, container: Container) -> None:
        super().__init__()
        self.setWindowTitle(MAIN_WINDOW_TITLE)
        self.setStyleSheet(STYLE_SHEET_COMBO_BOX)
        self.command_manager = CommandManager()
        self._container = container
        self._event_manager = self._container.event_manager()
        self._event_manager.subscribe(EventType.POKEMON_ADDED, self._on_pokemon_changed)
        self._event_manager.subscribe(EventType.POKEMON_EDITED, self._on_pokemon_edited)
        self._event_manager.subscribe(EventType.POKEMON_REMOVED, self._on_pokemon_changed)
        self._event_manager.subscribe(EventType.POKEMON_TRANSFERRED, self._on_pokemon_transferred)
        self._event_manager.subscribe(EventType.SESSION_CREATED, self._on_session_loaded)
        self._event_manager.subscribe(EventType.SESSION_LOADED, self._on_session_loaded)
        self._game_data_loader = self._container.game_data_loader()
        self._game_data_loader.load_location_data()
        self._game_service = GameService(container)
        self._game_state = GameState("", "", False, None, None, None, [], [], {})
        self._game_state_view_model = GameStateViewModel(is_game_active=False)
        self._journal_service = None
        self._pokemon_service = None
        self._save_service = self._container.save_service()
        self._create_menu()
        self._init_tabs()
        self._update_ui_from_viewmodel()

    def _add_active_pokemon(self) -> None:
        if self._pokemon_service.party_full:
            QMessageBox.warning(self, MSG_BOX_TITLE_PARTY_FULL, MSG_BOX_MSG_PARTY_FULL)
            return
        dialog = PokemonDialog(self._container, self._game_state, PokemonStatus.ACTIVE, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        command = AddPokemonCommand(self._container, dialog.pokemon, self._pokemon_service)
        _ = self.command_manager.execute(command)
        LOGGER.info("Added active Pokemon: %s", dialog.pokemon)

    def _add_boxed_pokemon(self) -> None:
        dialog = PokemonDialog(self._container, self._game_state, PokemonStatus.BOXED, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        command = AddPokemonCommand(self._container, dialog.pokemon, self._pokemon_service)
        _ = self.command_manager.execute(command)
        LOGGER.info("Added boxed Pokemon: %s", dialog.pokemon)

    def _create_active_party_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        self._active_party_widget = QWidget(widget)
        self._active_party_layout = QVBoxLayout(self._active_party_widget)
        self._active_party_layout.setAlignment(ALIGN_TOP)
        scroll_area = QScrollArea(widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self._active_party_widget)
        layout.addWidget(scroll_area)
        return widget

    def _create_boxed_pokemon_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        self._boxed_pokemon_widget = QWidget(widget)
        self._boxed_pokemon_layout = QGridLayout(self._boxed_pokemon_widget)
        self._boxed_pokemon_layout.setContentsMargins(SPACING, SPACING, SPACING, SPACING)
        self._boxed_pokemon_layout.setSpacing(SPACING)
        self._boxed_pokemon_layout.setAlignment(ALIGN_TOP | ALIGN_LEFT)
        self._boxed_pokemon_widget.setLayout(self._boxed_pokemon_layout)
        self._boxed_scroll_area = QScrollArea(widget)
        self._boxed_scroll_area.viewport().installEventFilter(self)
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._update_boxed_pokemon_display)
        self._boxed_scroll_area.setWidgetResizable(True)
        self._boxed_scroll_area.setWidget(self._boxed_pokemon_widget)
        self._boxed_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self._boxed_scroll_area)
        return widget

    def _create_dead_pokemon_widget(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        self._dead_pokemon_widget = QWidget(widget)
        self._dead_pokemon_layout = QGridLayout(self._dead_pokemon_widget)
        self._dead_pokemon_layout.setContentsMargins(SPACING, SPACING, SPACING, SPACING)
        self._dead_pokemon_layout.setSpacing(SPACING)
        self._dead_pokemon_layout.setAlignment(ALIGN_TOP | ALIGN_LEFT)
        self._dead_pokemon_widget.setLayout(self._dead_pokemon_layout)
        self._dead_scroll_area = QScrollArea(widget)
        self._dead_scroll_area.viewport().installEventFilter(self)
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._update_dead_pokemon_display)
        self._dead_scroll_area.setWidgetResizable(True)
        self._dead_scroll_area.setWidget(self._dead_pokemon_widget)
        self._dead_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self._dead_scroll_area)
        return widget

    def _create_encounters_tab(self) -> QWidget:
        self._encounters_tab = EncountersTab(self._container, self._game_state, self)
        self._encounters_tab.setEnabled(False)
        return self._encounters_tab

    def _create_menu(self) -> None:
        menubar = self.menuBar()
        file_menu = menubar.addMenu(MENU_FILE_NAME)
        new_action = QAction(MENU_ACTION_NEW_NAME, self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_file)
        file_menu.addAction(new_action)
        load_action = QAction(MENU_ACTION_LOAD_NAME, self)
        load_action.setShortcut("Ctrl+L")
        load_action.triggered.connect(self._load_file)
        file_menu.addAction(load_action)
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_file)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        exit_action = QAction(MENU_ACTION_EXIT_NAME, self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        edit_menu = self.menuBar().addMenu(MENU_EDIT_NAME)
        undo_action = QAction(MENU_ACTION_UNDO_NAME, self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self._undo_action)
        edit_menu.addAction(undo_action)

    def _create_party_tab(self) -> QWidget:
        self._party_tab = QWidget(self)
        self._party_tab.setEnabled(False)
        party_layout = QVBoxLayout(self._party_tab)
        party_subtabs = QTabWidget(self._party_tab)
        active_widget = self._create_active_party_widget()
        party_subtabs.addTab(active_widget, TAB_PARTY_NAME)
        boxed_widget = self._create_boxed_pokemon_widget()
        party_subtabs.addTab(boxed_widget, TAB_BOXED_NAME)
        dead_widget = self._create_dead_pokemon_widget()
        party_subtabs.addTab(dead_widget, TAB_DEAD_NAME)
        party_layout.addWidget(party_subtabs)
        self._party_tab.setLayout(party_layout)
        return self._party_tab

    def _create_rules_tab(self) -> QWidget:
        tab = QWidget(self)
        layout = QVBoxLayout(tab)
        self._rules_text = QTextEdit(tab)
        self._rules_text.setReadOnly(True)
        layout.addWidget(self._rules_text)
        return tab

    def _create_tools_tab(self) -> QWidget:
        self._tools_tab = QWidget(self)
        self._tools_tab.setEnabled(False)
        layout = QVBoxLayout(self._tools_tab)
        tool_selector = QComboBox(self._tools_tab)
        tool_selector.addItems([LABEL_TOOL_RANDOM_DECISION, LABEL_TOOL_BEST_MOVE])
        layout.addWidget(tool_selector)
        tool_stack = QStackedWidget(self._tools_tab)
        self._random_decision_widget = RandomDecisionToolWidget(
            self._container,
            self._game_state,
            self._tools_tab,
        )
        tool_stack.addWidget(self._random_decision_widget)
        self._best_moves_widget = BestMovesToolWidget(
            self._container,
            self._game_state,
            self._tools_tab,
        )
        tool_stack.addWidget(self._best_moves_widget)
        tool_selector.currentIndexChanged.connect(tool_stack.setCurrentIndex)
        layout.addWidget(tool_stack)
        self._tools_tab.setLayout(layout)
        return self._tools_tab

    def _handle_transfer(self, pokemon: Pokemon, target: PokemonStatus) -> None:
        command = TransferPokemonCommand(
            self._container,
            self._game_state,
            pokemon,
            target,
            self._pokemon_service,
        )
        success = self.command_manager.execute(command)
        if not success:
            QMessageBox.warning(self, MSG_BOX_TITLE_PARTY_FULL, MSG_BOX_MSG_PARTY_FULL)
            return
        self._update_game_state_viewmodel()
        LOGGER.info("Transfered Pokemon to %s: %s", target, pokemon)

    def _init_tabs(self) -> None:
        tabs = QTabWidget(self)
        self.setCentralWidget(tabs)
        tabs.addTab(self._create_rules_tab(), TAB_RULES_NAME)
        tabs.addTab(self._create_party_tab(), TAB_PARTY_NAME)
        tabs.addTab(self._create_encounters_tab(), TAB_ENCOUNTER_NAME)
        tabs.addTab(self._create_tools_tab(), TAB_TOOLS_NAME)

    def _new_file(self) -> None:
        rulesets = load_yaml_file(PathConfig.rules_file())
        dialog = NewSessionDialog(rulesets, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        game, ruleset, generation, sub_region_clause = dialog.selection
        try:
            self._game_service.new_game(game, ruleset, generation, sub_region_clause)
        except FileNotFoundError as e:
            QMessageBox.critical(self, MSG_BOX_TITLE_NO_FILE, f"{MSG_BOX_MSG_NO_DATA_FILE}{e}")
            return
        LOGGER.info(
            "Started new session for game|rules: %s|%s",
            self._game_state.game,
            self._game_state.ruleset,
        )

    def _load_file(self) -> None:
        save_file = self._prompt_for_save_file()
        if save_file is None:
            return
        try:
            self._game_service.load_game(save_file)
        except FileNotFoundError as e:
            QMessageBox.critical(self, MSG_BOX_TITLE_NO_FILE, f"{MSG_BOX_MSG_NO_DATA_FILE}{e}")
            return
        LOGGER.info(
            "Resumed previous session for game|rules: %s|%s",
            self._game_state.game,
            self._game_state.ruleset,
        )

    def _on_pokemon_changed(self, data: dict[str, Pokemon]) -> None:
        pokemon = data["pokemon"]
        if pokemon.status == PokemonStatus.ACTIVE:
            self._update_active_party_display()
            self._best_moves_widget.update_party_stage_section()
        elif pokemon.status == PokemonStatus.BOXED:
            self._update_boxed_pokemon_display()
        self._encounters_tab.update_encounters()

    def _on_pokemon_edited(self, data: dict[str, Pokemon]) -> None:
        pokemon = data["pokemon"]
        if pokemon.status == PokemonStatus.ACTIVE:
            self._update_active_party_display()
            self._best_moves_widget.update_party_stage_section()
        elif pokemon.status == PokemonStatus.BOXED:
            self._update_boxed_pokemon_display()
        elif pokemon.status == PokemonStatus.DEAD:
            self._update_dead_pokemon_display()
        self._encounters_tab.update_encounters()

    def _on_pokemon_transferred(self, data: dict[str, PokemonStatus]) -> None:
        previous_status = data["previous_status"]
        new_status = data["new_status"]
        self._update_game_state_viewmodel()
        if PokemonStatus.ACTIVE in {previous_status, new_status}:
            self._update_active_party_display()
            self._best_moves_widget.update_party_stage_section()
        if PokemonStatus.BOXED in {previous_status, new_status}:
            self._update_boxed_pokemon_display()
        if PokemonStatus.DEAD in {previous_status, new_status}:
            self._update_dead_pokemon_display()
        self._encounters_tab.update_encounters()

    def _on_session_loaded(self, data: dict[str, GameState]) -> None:
        self._game_state = data["game_state"]
        self._pokemon_service = PokemonService(self._container, self._game_state)
        self._decision_service = RandomDecisionService(self._container, self._game_state)
        self._update_game_state_viewmodel()
        self._update_active_party_display()
        self._update_boxed_pokemon_display()
        self._update_dead_pokemon_display()
        self._encounters_tab.set_state(self._game_state)
        self._random_decision_widget.set_state(self._game_state)
        self._best_moves_widget.set_state(self._game_state)

    def _prompt_for_save_file(self) -> None:
        folder = PathConfig.save_folder()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Save File",
            str(folder),
            "Save Files (*.sav)",
        )
        return Path(file_path) if file_path else None

    def _save_file(self) -> None:
        if not self._game_state_view_model.is_game_active:
            return
        self._game_service.save_game(self._game_state)

    def _undo_action(self) -> None:
        self.command_manager.undo()
        self._update_active_party_display()
        self._update_boxed_pokemon_display()
        self._update_dead_pokemon_display()
        self._encounters_tab.update_encounters()

    def _update_active_party_display(self) -> None:
        clear_layout(self._active_party_layout)
        active_view_model_pairs = PokemonCardViewModel.create_pokemon_viewmodels(
            self._game_state,
            self._container.pokemon_repository(),
            PokemonStatus.ACTIVE,
            PokemonCardType.ACTIVE,
        )
        for view_model, pokemon in active_view_model_pairs:
            card = ActivePokemonCardWidget(
                self._container,
                view_model,
                pokemon,
                self._game_state,
                self._active_party_widget,
                None,
            )
            card.transfer_requested.connect(self._handle_transfer)
            self._active_party_layout.addWidget(card)
        if self._game_state_view_model.can_add_to_party:
            add_button = QPushButton(BUTTON_ADD_POKEMON, self._active_party_widget)
            add_button.clicked.connect(self._add_active_pokemon)
            self._active_party_layout.addWidget(add_button)
        self._best_moves_widget.update_party_stage_section()

    def _update_boxed_pokemon_display(self) -> None:
        clear_layout(self._boxed_pokemon_layout)
        boxed_pokemon = self._pokemon_service.boxed_pokemon
        available_width = self._boxed_scroll_area.viewport().width()
        card_total_width = WIDGET_POKEMON_CARD_WIDTH + SPACING
        columns = max(1, available_width // card_total_width)
        boxed_view_model_pairs = PokemonCardViewModel.create_pokemon_viewmodels(
            self._game_state,
            self._container.pokemon_repository(),
            PokemonStatus.BOXED,
            PokemonCardType.BOXED,
        )
        for idx, (view_model, pokemon) in enumerate(boxed_view_model_pairs):
            card = BoxedPokemonCardWidget(
                self._container,
                view_model,
                pokemon,
                self._game_state,
                self._boxed_pokemon_widget,
                lambda: len(self._pokemon_service.active_pokemon) < ACTIVE_PARTY_LIMIT,
            )
            card.transfer_requested.connect(self._handle_transfer)
            row = idx // columns
            col = idx % columns
            self._boxed_pokemon_layout.addWidget(card, row, col)
        add_button = QPushButton(BUTTON_ADD_POKEMON, self._boxed_pokemon_widget)
        add_button.setFixedSize(WIDGET_POKEMON_CARD_WIDTH, WIDGET_POKEMON_CARD_WIDTH)
        add_button.clicked.connect(self._add_boxed_pokemon)
        next_idx = len(boxed_pokemon)
        row = next_idx // columns
        col = next_idx % columns
        self._boxed_pokemon_layout.addWidget(add_button, row, col)

    def _update_dead_pokemon_display(self) -> None:
        clear_layout(self._dead_pokemon_layout)
        available_width = self._dead_scroll_area.viewport().width()
        card_total_width = WIDGET_POKEMON_CARD_WIDTH + SPACING
        columns = max(1, available_width // card_total_width)
        dead_view_model_pairs = PokemonCardViewModel.create_pokemon_viewmodels(
            self._game_state,
            self._container.pokemon_repository(),
            PokemonStatus.DEAD,
            PokemonCardType.DEAD,
        )
        for idx, (view_model, pokemon) in enumerate(dead_view_model_pairs):
            card = DeadPokemonCardWidget(
                self._container,
                view_model,
                pokemon,
                self._game_state,
                self._dead_pokemon_widget,
                lambda: len(self._pokemon_service.active_pokemon) < ACTIVE_PARTY_LIMIT,
            )
            card.transfer_requested.connect(self._handle_transfer)
            row = idx // columns
            col = idx % columns
            self._dead_pokemon_layout.addWidget(card, row, col)

    def _update_game_state_viewmodel(self) -> None:
        self._game_state_view_model = GameStateViewModel.from_game_state(
            self._game_state,
            self._pokemon_service,
        )
        self._update_ui_from_viewmodel()

    def _update_ui_from_viewmodel(self) -> None:
        self._party_tab.setEnabled(self._game_state_view_model.is_game_active)
        self._encounters_tab.setEnabled(self._game_state_view_model.is_game_active)
        self._tools_tab.setEnabled(self._game_state_view_model.is_game_active)
        if self._game_state_view_model.is_game_active and self._game_state_view_model.ruleset_description:
            rules_text = (
                f"{self._game_state_view_model.ruleset_name} Rules:\n- "
                f"{'\n- '.join(self._game_state_view_model.ruleset_description)}"
            )
            self._rules_text.setPlainText(rules_text)
        else:
            self._rules_text.clear()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if (
            obj == self._boxed_scroll_area.viewport() or obj == self._dead_scroll_area.viewport()
        ) and event.type() == QEvent.Type.Resize:
            self._resize_timer.start(RESIZE_DELAY)
            return False
        return super().eventFilter(obj, event)
