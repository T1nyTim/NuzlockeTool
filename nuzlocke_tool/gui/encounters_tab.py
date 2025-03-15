from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nuzlocke_tool.constants import LABEL_LOCATION, LABEL_POKEMON, LABEL_STATUS
from nuzlocke_tool.container import Container
from nuzlocke_tool.models.models import GameState
from nuzlocke_tool.models.view_models import EncounterViewModel


class EncountersTab(QWidget):
    def __init__(self, container: Container, game_state: GameState, parent: QWidget) -> None:
        super().__init__(parent)
        self._container = container
        self._encounter_widgets = {}
        self._game_state = game_state
        self._location_repository = self._container.location_repository()
        self._location_row = {}
        self._view_models = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([LABEL_LOCATION, LABEL_POKEMON, LABEL_STATUS])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.table)

    def init_table(self) -> None:
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
            self._location_row,
        )

    def set_state(self, game_state: GameState) -> None:
        self._game_state = game_state
        self.init_table()
        self.update_encounters()

    def update_encounters(self) -> None:
        for row in self._location_row.values():
            self.table.setItem(row, 1, QTableWidgetItem("None"))
            self.table.setItem(row, 2, QTableWidgetItem("None"))
            self.table.item(row, 0).setData(Qt.ItemDataRole.ForegroundRole, None)
        self._view_models = EncounterViewModel.create_view_models(
            list(self._location_row.keys()),
            self._game_state.pokemon,
            self._location_row,
        )
        for view_model in self._view_models:
            if not view_model.has_encounter:
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
