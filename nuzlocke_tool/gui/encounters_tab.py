from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nuzlocke_tool.constants import (
    LABEL_LOCATION,
    LABEL_POKEMON,
    LABEL_STATUS,
    TAB_BOXED_NAME,
    TAB_DEAD_NAME,
    TAB_PARTY_NAME,
    TABLE_COLOR_BOXED,
    TABLE_COLOR_DEAD,
    TABLE_COLOR_PARTY,
)
from nuzlocke_tool.container import Container
from nuzlocke_tool.models import GameState, PokemonStatus


class EncountersTab(QWidget):
    def __init__(self, container: Container, game_state: GameState, parent: QWidget) -> None:
        super().__init__(parent)
        self._container = container
        self._encounter_widgets = {}
        self._game_data_loader = self._container.game_data_loader()
        self._game_state = game_state
        self._location_row = {}
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
        region_type = "Partial" if self._game_state.sub_region_clause else "Full"
        locations = [
            location
            for location, info in self._game_data_loader.location_data.items()
            if (info.get("type") == region_type or info.get("type") is None)
            and self._game_state.game in info["games"]
        ]
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

    def set_state(self, game_state: GameState) -> None:
        self._game_state = game_state
        self.init_table()
        self.update_encounters()

    def update_encounters(self) -> None:
        for row in self._location_row.values():
            self.table.setItem(row, 1, QTableWidgetItem("None"))
            self.table.setItem(row, 2, QTableWidgetItem("None"))
            self.table.item(row, 0).setData(Qt.ItemDataRole.ForegroundRole, None)
        for pokemon in self._game_state.pokemon:
            location = pokemon.encountered
            if location in self._location_row:
                row = self._location_row[location]
                details = f"{pokemon.nickname} ({pokemon.species}) - Caught Lv{pokemon.caught_level}"
                status_map = {
                    PokemonStatus.ACTIVE: TAB_PARTY_NAME,
                    PokemonStatus.BOXED: TAB_BOXED_NAME,
                    PokemonStatus.DEAD: TAB_DEAD_NAME,
                }
                status = status_map[pokemon.status]
                item_details = QTableWidgetItem(details)
                item_status = QTableWidgetItem(status)
                if pokemon.status == PokemonStatus.ACTIVE:
                    color = QColor(TABLE_COLOR_PARTY)
                elif pokemon.status == PokemonStatus.BOXED:
                    color = QColor(TABLE_COLOR_BOXED)
                elif pokemon.status == PokemonStatus.DEAD:
                    color = QColor(TABLE_COLOR_DEAD)
                else:
                    color = None
                if color:
                    self.table.item(row, 0).setForeground(QBrush(color))
                    item_details.setForeground(QBrush(color))
                    item_status.setForeground(QBrush(color))
                self.table.setItem(row, 1, item_details)
                self.table.setItem(row, 2, item_status)
