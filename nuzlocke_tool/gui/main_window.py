import logging
from pathlib import Path

import yaml
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

from nuzlocke_tool import (
    journal_folder,
    locations_file,
    resources_folder,
    rules_file,
    save_folder,
    versions_file,
)
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
    MENU_FILE_NAME,
    MSG_BOX_MSG_NO_MOVE_FILE,
    MSG_BOX_MSG_NO_POKEMON_FILE,
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
from nuzlocke_tool.gui.best_moves_widget import BestMovesToolWidget
from nuzlocke_tool.gui.card_widgets import (
    ActivePokemonCardWidget,
    BoxedPokemonCardWidget,
    DeadPokemonCardWidget,
)
from nuzlocke_tool.gui.dialogs import NewSessionDialog, PokemonDialog
from nuzlocke_tool.gui.encounters_tab import EncountersTab
from nuzlocke_tool.gui.random_decision_widget import RandomDecisionToolWidget
from nuzlocke_tool.models import GameData, GameState, PartyManager, Pokemon
from nuzlocke_tool.utils import append_journal_entry, clear_layout, load_yaml_file, save_session

LOGGER = logging.getLogger(__name__)


class NuzlockeTrackerMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(MAIN_WINDOW_TITLE)
        self.setStyleSheet(STYLE_SHEET_COMBO_BOX)
        location_data = load_yaml_file(locations_file())
        self._game_data = GameData(location_data, {}, {})
        self._game_state = GameState("", "", False, None, None, [], {})  # noqa: FBT003
        self._party_manager = PartyManager()
        self._create_menu()
        self._init_tabs()

    def _add_active_pokemon(self) -> None:
        if len(self._party_manager.active) >= ACTIVE_PARTY_LIMIT:
            QMessageBox.warning(self, MSG_BOX_TITLE_PARTY_FULL, MSG_BOX_MSG_PARTY_FULL)
            return
        new_pokemon = self._add_pokemon()
        if new_pokemon is None:
            return
        self._party_manager.active.append(new_pokemon)
        self._update_active_party_display()
        self._encounters_tab.update_encounters()
        self._game_state.encounters.append(new_pokemon.encountered)
        save_session(self._game_state, self._party_manager)
        append_journal_entry(
            self._game_state.journal_file,
            f"Caught {new_pokemon} @ {new_pokemon.encountered}. Added to the Party.",
        )
        LOGGER.info("Added active Pokemon: %s", new_pokemon)

    def _add_boxed_pokemon(self) -> None:
        new_pokemon = self._add_pokemon()
        if new_pokemon is None:
            return
        self._party_manager.boxed.append(new_pokemon)
        self._update_boxed_pokemon_display()
        self._encounters_tab.update_encounters()
        self._game_state.encounters.append(new_pokemon.encountered)
        save_session(self._game_state, self._party_manager)
        append_journal_entry(
            self._game_state.journal_file,
            f"Caught {new_pokemon} @ {new_pokemon.encountered}. Added to the Box.",
        )
        LOGGER.info("Added boxed Pokemon: %s", new_pokemon)

    def _add_pokemon(self) -> Pokemon | None:
        dialog = PokemonDialog(self._game_state, self._game_data, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.pokemon

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
        self._encounters_tab = EncountersTab(self._game_state, self._party_manager, self._game_data, self)
        self._encounters_tab.setEnabled(False)
        return self._encounters_tab

    def _create_menu(self) -> None:
        menubar = self.menuBar()
        file_menu = menubar.addMenu(MENU_FILE_NAME)
        new_action = QAction(MENU_ACTION_NEW_NAME, self)
        new_action.triggered.connect(self._new_file)
        file_menu.addAction(new_action)
        load_action = QAction(MENU_ACTION_LOAD_NAME, self)
        load_action.triggered.connect(self._load_file)
        file_menu.addAction(load_action)
        file_menu.addSeparator()
        exit_action = QAction(MENU_ACTION_EXIT_NAME, self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

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
            self._game_state,
            self._party_manager,
            self._tools_tab,
        )
        tool_stack.addWidget(self._random_decision_widget)
        self._best_moves_widget = BestMovesToolWidget(self._game_data, self._party_manager, self._tools_tab)
        tool_stack.addWidget(self._best_moves_widget)
        tool_selector.currentIndexChanged.connect(tool_stack.setCurrentIndex)
        layout.addWidget(tool_stack)
        self._tools_tab.setLayout(layout)
        return self._tools_tab

    def _handle_transfer(self, pokemon: Pokemon, target: str) -> None:
        self._party_manager.transfer(pokemon, target)
        self._update_active_party_display()
        self._update_boxed_pokemon_display()
        self._update_dead_pokemon_display()
        self._encounters_tab.update_encounters()
        save_session(self._game_state, self._party_manager)
        target_name = self._process_storage_status(target)
        if target_name == TAB_DEAD_NAME:
            append_journal_entry(self._game_state.journal_file, f"{pokemon} has Died.")
        else:
            append_journal_entry(self._game_state.journal_file, f"Transfered {pokemon} to {target_name}.")
        LOGGER.info("Transfered Pokemon to %s: %s", target, pokemon)

    def _init_tabs(self) -> None:
        tabs = QTabWidget(self)
        self.setCentralWidget(tabs)
        tabs.addTab(self._create_rules_tab(), TAB_RULES_NAME)
        tabs.addTab(self._create_party_tab(), TAB_PARTY_NAME)
        tabs.addTab(self._create_encounters_tab(), TAB_ENCOUNTER_NAME)
        tabs.addTab(self._create_tools_tab(), TAB_TOOLS_NAME)

    def _new_file(self) -> None:
        rulesets = load_yaml_file(rules_file())
        dialog = NewSessionDialog(rulesets, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._game_state.game, self._game_state.ruleset, generation, self._game_state.sub_region_clause = (
            dialog.selection
        )
        pokemon_data_file = f"gen{generation}_pokemon.yaml"
        pokemon_yaml_path = resources_folder() / pokemon_data_file
        if not pokemon_yaml_path.exists():
            QMessageBox.critical(
                self,
                MSG_BOX_TITLE_NO_FILE,
                f"{MSG_BOX_MSG_NO_POKEMON_FILE}{pokemon_yaml_path}",
            )
            return
        self._game_data.pokemon_data = load_yaml_file(pokemon_yaml_path)
        move_data_file = f"gen{generation}_moves.yaml"
        move_yaml_path = resources_folder() / move_data_file
        if not move_yaml_path.exists():
            QMessageBox.critical(
                self,
                MSG_BOX_TITLE_NO_FILE,
                f"{MSG_BOX_MSG_NO_MOVE_FILE}{move_yaml_path}",
            )
            return
        self._game_data.move_data = load_yaml_file(move_yaml_path)
        ruleset = rulesets.get(self._game_state.ruleset)
        if ruleset:
            rules_text = f"{self._game_state.ruleset} Rules:\n- " + (
                "\n- ".join(ruleset["rules"]) if isinstance(ruleset["rules"], list) else ruleset["rules"]
            )
            self._rules_text.setPlainText(rules_text)
        self._party_manager.active.clear()
        self._party_manager.boxed.clear()
        self._update_active_party_display()
        self._update_boxed_pokemon_display()
        self._encounters_tab.init_table()
        self._encounters_tab.update_encounters()
        self._random_decision_widget.init_ui()
        self._best_moves_widget.init_ui()
        self._party_tab.setEnabled(True)
        self._encounters_tab.setEnabled(True)
        self._tools_tab.setEnabled(True)
        self._game_state.journal_file = self._new_journal_file(
            self._game_state.game,
            self._game_state.ruleset,
        )
        self._game_state.save_file = self._new_save_file(self._game_state.game, self._game_state.ruleset)
        append_journal_entry(
            self._game_state.journal_file,
            f"Started new session in {self._game_state.game}.",
        )
        append_journal_entry(
            self._game_state.journal_file,
            f"New session is utilising the {self._game_state.ruleset} ruleset.",
        )
        if self._game_state.sub_region_clause:
            append_journal_entry(self._game_state.journal_file, "New session is using the Sub-Region Clause.")
        LOGGER.info(
            "Started new session for game|rules: %s|%s",
            self._game_state.game,
            self._game_state.ruleset,
        )

    @staticmethod
    def _new_journal_file(game: str, ruleset: str) -> Path:
        folder = journal_folder()
        base_name = f"{game}_{ruleset}_"
        i = 1
        while True:
            journal_file = folder / f"{base_name}{i}.journal"
            if not journal_file.exists():
                break
            i += 1
        journal_file.touch(exist_ok=False)
        return journal_file

    @staticmethod
    def _new_save_file(game: str, ruleset: str) -> Path:
        folder = save_folder()
        base_name = f"{game}_{ruleset}_"
        i = 1
        while True:
            save_file = folder / f"{base_name}{i}.sav"
            if not save_file.exists():
                break
            i += 1
        save_file.touch(exist_ok=False)
        return save_file

    def _load_file(self) -> None:
        save_file = self._prompt_for_save_file()
        if save_file is None:
            return
        self._load_session_data(save_file)
        versions = load_yaml_file(versions_file())
        version_info = versions.get(self._game_state.game)
        generation = version_info.get("generation")
        pokemon_data_file = f"gen{generation}_pokemon.yaml"
        pokemon_yaml_path = resources_folder() / pokemon_data_file
        self._game_data.pokemon_data = load_yaml_file(pokemon_yaml_path)
        move_data_file = f"gen{generation}_moves.yaml"
        move_yaml_path = resources_folder() / move_data_file
        self._game_data.move_data = load_yaml_file(move_yaml_path)
        rulesets = load_yaml_file(rules_file())
        ruleset = rulesets.get(self._game_state.ruleset)
        if ruleset:
            rules_text = f"{self._game_state.ruleset} Rules:\n- " + (
                "\n- ".join(ruleset["rules"]) if isinstance(ruleset["rules"], list) else ruleset["rules"]
            )
            self._rules_text.setPlainText(rules_text)
        self._update_active_party_display()
        self._update_boxed_pokemon_display()
        self._update_dead_pokemon_display()
        self._encounters_tab.set_state(self._game_state, self._party_manager, self._game_data)
        self._random_decision_widget.set_state(self._game_state, self._party_manager)
        self._best_moves_widget.set_state(self._game_data, self._party_manager)
        self._party_tab.setEnabled(True)
        self._encounters_tab.setEnabled(True)
        self._tools_tab.setEnabled(True)
        LOGGER.info(
            "Resumed previous session for game|rules: %s|%s",
            self._game_state.game,
            self._game_state.ruleset,
        )

    def _load_session_data(self, filepath: Path) -> tuple[GameState, PartyManager]:
        with filepath.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        game_state_data = data["game_state"]
        game_state_data["journal_file"] = Path(game_state_data["journal_file"])
        game_state_data["save_file"] = Path(game_state_data["save_file"])
        self._game_state = GameState(**game_state_data)
        party_data = data["party_manager"]
        party_data["active"] = [Pokemon(**p) for p in party_data.get("active")]
        party_data["boxed"] = [Pokemon(**p) for p in party_data.get("boxed")]
        party_data["dead"] = [Pokemon(**p) for p in party_data.get("dead")]
        self._party_manager = PartyManager(**party_data)

    @staticmethod
    def _process_storage_status(status: str) -> str:
        status_name = {"active": TAB_PARTY_NAME, "boxed": TAB_BOXED_NAME, "dead": TAB_DEAD_NAME}
        return status_name.get(status)

    def _prompt_for_save_file(self) -> None:
        folder = save_folder()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Save File",
            str(folder),
            "Save Files (*.sav)",
        )
        return Path(file_path) if file_path else None

    def _update_active_party_display(self) -> None:
        clear_layout(self._active_party_layout)
        for mon in self._party_manager.active:
            card = ActivePokemonCardWidget(
                mon,
                self._game_state,
                self._game_data,
                self._active_party_widget,
                lambda: len(self._party_manager.active) > 1,
            )
            card.transfer_requested.connect(self._handle_transfer)
            self._active_party_layout.addWidget(card)
        if len(self._party_manager.active) < ACTIVE_PARTY_LIMIT:
            add_button = QPushButton(BUTTON_ADD_POKEMON, self._active_party_widget)
            add_button.clicked.connect(self._add_active_pokemon)
            self._active_party_layout.addWidget(add_button)
        self._best_moves_widget.update_party_stage_section()

    def _update_boxed_pokemon_display(self) -> None:
        clear_layout(self._boxed_pokemon_layout)
        available_width = self._boxed_scroll_area.viewport().width()
        card_total_width = WIDGET_POKEMON_CARD_WIDTH + SPACING
        columns = max(1, available_width // card_total_width)
        for idx, mon in enumerate(self._party_manager.boxed):
            card = BoxedPokemonCardWidget(
                mon,
                self._game_state,
                self._game_data,
                self._boxed_pokemon_widget,
                lambda: len(self._party_manager.active) < ACTIVE_PARTY_LIMIT,
            )
            card.transfer_requested.connect(self._handle_transfer)
            row = idx // columns
            col = idx % columns
            self._boxed_pokemon_layout.addWidget(card, row, col)
        add_button = QPushButton(BUTTON_ADD_POKEMON, self._boxed_pokemon_widget)
        add_button.setFixedSize(WIDGET_POKEMON_CARD_WIDTH, WIDGET_POKEMON_CARD_WIDTH)
        add_button.clicked.connect(self._add_boxed_pokemon)
        next_idx = len(self._party_manager.boxed)
        row = next_idx // columns
        col = next_idx % columns
        self._boxed_pokemon_layout.addWidget(add_button, row, col)

    def _update_dead_pokemon_display(self) -> None:
        clear_layout(self._dead_pokemon_layout)
        available_width = self._dead_scroll_area.viewport().width()
        card_total_width = WIDGET_POKEMON_CARD_WIDTH + SPACING
        columns = max(1, available_width // card_total_width)
        for idx, mon in enumerate(self._party_manager.dead):
            card = DeadPokemonCardWidget(
                mon,
                self._game_state,
                self._game_data,
                self._dead_pokemon_widget,
                lambda: len(self._party_manager.active) < ACTIVE_PARTY_LIMIT,
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
