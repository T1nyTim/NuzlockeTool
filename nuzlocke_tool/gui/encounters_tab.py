from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QAction, QBrush
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QMenu,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nuzlocke_tool.constants import (
    LABEL_HEADER_LOCATION,
    LABEL_HEADER_POKEMON,
    LABEL_HEADER_STATUS,
    MENU_ACTION_FAILED_ENCOUNTER_NAME,
)
from nuzlocke_tool.container import Container
from nuzlocke_tool.gui.dialogs import FailedEncounterDialog
from nuzlocke_tool.models.models import EventType
from nuzlocke_tool.models.view_models import EncounterViewModel


class EncountersTab(QWidget):
    def __init__(self, container: Container, parent: QWidget) -> None:
        super().__init__(parent)
        self._container = container
        self._encounter_widgets = {}
        self._event_manager = self._container.event_manager()
        self._game_state = self._container.game_state()
        self._location_repository = self._container.location_repository()
        self._location_row = {}
        self._save_service = self._container.save_service()
        self._view_models = []
        self._init_ui()

    def _add_failed_encounter(self, location: str) -> None:
        dialog = FailedEncounterDialog(self._container, location, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        failed_encounter = dialog.failed_encounter
        self._game_state.failed_encounters.append(failed_encounter)
        self._save_service.save_session(self._game_state)
        self._event_manager.publish(EventType.FAILED_ENCOUNTER_ADDED, {"failed_encounter": failed_encounter})
        self.update_encounters()
        journal_service = self._container.journal_service_factory(self._game_state)
        journal_service.add_failed_encounter_entry(failed_encounter)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(
            [LABEL_HEADER_LOCATION, LABEL_HEADER_POKEMON, LABEL_HEADER_STATUS],
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.table)

    def _init_table(self) -> None:
        locations = self._location_repository.get_for_game(
            self._game_state.game,
            self._game_state.sub_region_clause,
        )
        self.table.setRowCount(len(locations))
        self._location_row.clear()
        for row, location in enumerate(locations):
            item_location = self.table.item(row, 0)
            if item_location is None:
                self.table.setItem(row, 0, QTableWidgetItem(location))
                self.table.setItem(row, 1, QTableWidgetItem("None"))
                self.table.setItem(row, 2, QTableWidgetItem("None"))
            else:
                item_location.setText(location)
            self._location_row[location] = row
        self._view_models = EncounterViewModel.create_view_models(
            locations,
            self._game_state.pokemon,
            self._game_state.failed_encounters,
            self._location_row,
        )

    def _show_context_menu(self, pos: QPoint) -> None:
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        location = self.table.item(row, 0).text()
        has_successful_encounter = any(p.encountered == location for p in self._game_state.pokemon)
        has_failed_encounter = any(f.location == location for f in self._game_state.failed_encounters)
        menu = QMenu(self)
        failed_action = QAction(MENU_ACTION_FAILED_ENCOUNTER_NAME, self)
        failed_action.triggered.connect(lambda: self._add_failed_encounter(location))
        if has_successful_encounter or has_failed_encounter:
            failed_action.setEnabled(False)
        menu.addAction(failed_action)
        menu.exec(self.table.viewport().mapToGlobal(pos))
        self.table.clearSelection()

    def update(self) -> None:
        self._game_state = self._container.game_state()
        self._init_table()
        self.update_encounters()

    def update_encounters(self) -> None:
        for row in self._location_row.values():
            self.table.setItem(row, 1, QTableWidgetItem("None"))
            self.table.setItem(row, 2, QTableWidgetItem("None"))
            self.table.item(row, 0).setData(Qt.ItemDataRole.ForegroundRole, None)
        self._view_models = EncounterViewModel.create_view_models(
            list(self._location_row.keys()),
            self._game_state.pokemon,
            self._game_state.failed_encounters,
            self._location_row,
        )
        for view_model in self._view_models:
            if not view_model.has_encounter and not view_model.is_failed_encounter:
                continue
            row = view_model.row_index
            item_details = QTableWidgetItem(view_model.display_details)
            item_status = QTableWidgetItem(view_model.display_status)
            if view_model.status_color:
                self.table.item(row, 0).setForeground(QBrush(view_model.status_color))
                item_details.setForeground(QBrush(view_model.status_color))
                item_status.setForeground(QBrush(view_model.status_color))
            self.table.setItem(row, 1, item_details)
            self.table.setItem(row, 2, item_status)
