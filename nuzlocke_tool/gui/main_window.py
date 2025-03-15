import copy
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
from nuzlocke_tool.models.models import GameState, Pokemon, PokemonCardType, PokemonStatus
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
        self._game_data_loader = self._container.game_data_loader()
        self._game_data_loader.load_location_data()
        self._game_service = GameService(container)
        self._game_state = GameState("", "", False, None, None, None, [], [], {})  # noqa: FBT003
        self._journal_service = None
        self._pokemon_service = None
        self._save_service = self._container.save_service()
        self._create_menu()
        self._init_tabs()

    def _add_active_pokemon(self) -> None:
        if self._pokemon_service.party_full:
            QMessageBox.warning(self, MSG_BOX_TITLE_PARTY_FULL, MSG_BOX_MSG_PARTY_FULL)
            return
        dialog = PokemonDialog(self._container, self._game_state, PokemonStatus.ACTIVE, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        command = AddPokemonCommand(
            self._container,
            dialog.pokemon,
            self._pokemon_service,
            on_success=self._after_pokemon_added,
        )
        _ = self.command_manager.execute(command)
        LOGGER.info("Added active Pokemon: %s", dialog.pokemon)

    def _add_boxed_pokemon(self) -> None:
        dialog = PokemonDialog(self._container, self._game_state, PokemonStatus.BOXED, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        command = AddPokemonCommand(
            self._container,
            dialog.pokemon,
            self._pokemon_service,
            on_success=self._after_pokemon_added,
        )
        _ = self.command_manager.execute(command)
        LOGGER.info("Added boxed Pokemon: %s", dialog.pokemon)

    def _after_pokemon_added(self) -> None:
        self._update_active_party_display()
        self._update_boxed_pokemon_display()
        self._encounters_tab.update_encounters()

    def _after_transfer(self) -> None:
        self._update_active_party_display()
        self._update_boxed_pokemon_display()
        self._update_dead_pokemon_display()
        self._encounters_tab.update_encounters()

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
            on_success=self._after_transfer,
        )
        success = self.command_manager.execute(command)
        if not success:
            QMessageBox.warning(self, MSG_BOX_TITLE_PARTY_FULL, MSG_BOX_MSG_PARTY_FULL)
            return
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
            self._game_state = self._game_service.new_game(game, ruleset, generation, sub_region_clause)
        except FileNotFoundError as e:
            QMessageBox.critical(self, MSG_BOX_TITLE_NO_FILE, f"{MSG_BOX_MSG_NO_DATA_FILE}{e}")
            return
        self._pokemon_service = PokemonService(self._container, self._game_state)
        self._decision_service = RandomDecisionService(self._container, self._game_state)
        ruleset = rulesets[self._game_state.ruleset]
        if ruleset:
            rules_text = f"{self._game_state.ruleset} Rules:\n- " + (
                "\n- ".join(ruleset["rules"]) if isinstance(ruleset["rules"], list) else ruleset["rules"]
            )
            self._rules_text.setPlainText(rules_text)
        self._update_active_party_display()
        self._update_boxed_pokemon_display()
        self._encounters_tab.set_state(self._game_state)
        self._random_decision_widget.set_state(self._game_state)
        self._best_moves_widget.set_state(self._game_state)
        self._party_tab.setEnabled(True)
        self._encounters_tab.setEnabled(True)
        self._tools_tab.setEnabled(True)
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
            self._game_state = self._game_service.load_game(save_file)
        except FileNotFoundError as e:
            QMessageBox.critical(self, MSG_BOX_TITLE_NO_FILE, f"{MSG_BOX_MSG_NO_DATA_FILE}{e}")
            return
        self._pokemon_service = PokemonService(self._container, self._game_state)
        self._decision_service = RandomDecisionService(self._container, self._game_state)
        rulesets = load_yaml_file(PathConfig.rules_file())
        ruleset = rulesets[self._game_state.ruleset]
        if ruleset:
            rules_text = f"{self._game_state.ruleset} Rules:\n- " + (
                "\n- ".join(ruleset["rules"]) if isinstance(ruleset["rules"], list) else ruleset["rules"]
            )
            self._rules_text.setPlainText(rules_text)
        self._update_active_party_display()
        self._update_boxed_pokemon_display()
        self._update_dead_pokemon_display()
        self._encounters_tab.set_state(self._game_state)
        self._random_decision_widget.set_state(self._game_state)
        self._best_moves_widget.set_state(self._game_state)
        self._party_tab.setEnabled(True)
        self._encounters_tab.setEnabled(True)
        self._tools_tab.setEnabled(True)
        LOGGER.info(
            "Resumed previous session for game|rules: %s|%s",
            self._game_state.game,
            self._game_state.ruleset,
        )

    def _prompt_for_save_file(self) -> None:
        folder = PathConfig.save_folder()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Save File",
            str(folder),
            "Save Files (*.sav)",
        )
        return Path(file_path) if file_path else None

    def _undo_action(self) -> None:
        self.command_manager.undo()
        self._update_active_party_display()
        self._update_boxed_pokemon_display()
        self._update_dead_pokemon_display()
        self._encounters_tab.update_encounters()

    def _update_active_party_display(self) -> None:
        clear_layout(self._active_party_layout)
        view_model_factory = self._container.view_model_factory()
        active_view_model_pairs = view_model_factory.create_pokemon_viewmodels(
            self._game_state,
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
        can_add_more = True
        if self._pokemon_service.party_full:
            can_add_more = False
        else:
            test_state = copy.deepcopy(self._game_state)
            dummy_pokemon = Pokemon(
                nickname="A",
                species="Bulbasaur",
                level=5,
                caught_level=5,
                moves=["Tackle"],
                dvs={"HP": 0, "Atk": 0, "Def": 0, "Spd": 0, "Spe": 0},
                encountered="Pallet Town",
                status=PokemonStatus.ACTIVE,
            )
            test_state.pokemon.append(dummy_pokemon)
            if not self._game_state.rule_strategy.validate_party(test_state):
                can_add_more = False
        if can_add_more:
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
        view_model_factory = self._container.view_model_factory()
        boxed_view_model_pairs = view_model_factory.create_pokemon_viewmodels(
            self._game_state,
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
        view_model_factory = self._container.view_model_factory()
        dead_view_model_pairs = view_model_factory.create_pokemon_viewmodels(
            self._game_state,
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

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if (
            obj == self._boxed_scroll_area.viewport() or obj == self._dead_scroll_area.viewport()
        ) and event.type() == QEvent.Type.Resize:
            self._resize_timer.start(RESIZE_DELAY)
            return False
        return super().eventFilter(obj, event)
