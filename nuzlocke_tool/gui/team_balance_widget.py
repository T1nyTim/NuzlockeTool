from PyQt6.QtCore import QEvent, QObject, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nuzlocke_tool.constants import (
    ALIGN_CENTER,
    NEUTRAL_MULTI,
    NOT_VERY_EFFECTIVE_MULTI,
    RESIZE_DELAY,
    SMALL_WINDOW_THRESHOLD,
    SUPER_EFFECTIVE_MULTI,
    SUPER_RESISTANCE_THRESHOLD,
    TYPE_CHART,
    ULTRA_EFFECTIVE_MULTI,
    ULTRA_RESISTANCE_THRESHOLD,
    WEAK_RESISTANCE_THRESHOLD,
)
from nuzlocke_tool.container import Container
from nuzlocke_tool.models.models import EventType, GameState
from nuzlocke_tool.services.team_balance_service import TeamBalanceService
from nuzlocke_tool.utils.utils import clear_layout


class TeamBalanceWidget(QWidget):
    def __init__(self, container: Container, parent: QWidget) -> None:
        super().__init__(parent)
        self._container = container
        self._event_manager = self._container.event_manager()
        self._event_manager.subscribe(EventType.POKEMON_ADDED, self._on_team_changed)
        self._event_manager.subscribe(EventType.POKEMON_EDITED, self._on_team_changed)
        self._event_manager.subscribe(EventType.POKEMON_TRANSFERRED, self._on_team_changed)
        self._event_manager.subscribe(EventType.POKEMON_REMOVED, self._on_team_changed)
        self._event_manager.subscribe(EventType.MOVE_UPDATED, self._on_team_changed)
        self._event_manager.subscribe(EventType.SESSION_LOADED, self._on_team_changed)
        self._event_manager.subscribe(EventType.SESSION_CREATED, self._on_team_changed)
        self._game_state = self._container.game_state()
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._delayed_resize_update)
        self._team_balance_service = TeamBalanceService(self._container, self._game_state)
        self._init_ui()

    def __del__(self) -> None:
        self._event_manager.unsubscribe(EventType.POKEMON_ADDED, self._on_team_changed)
        self._event_manager.unsubscribe(EventType.POKEMON_EDITED, self._on_team_changed)
        self._event_manager.unsubscribe(EventType.POKEMON_TRANSFERRED, self._on_team_changed)
        self._event_manager.unsubscribe(EventType.POKEMON_REMOVED, self._on_team_changed)
        self._event_manager.unsubscribe(EventType.MOVE_UPDATED, self._on_team_changed)
        self._event_manager.unsubscribe(EventType.SESSION_LOADED, self._on_team_changed)
        self._event_manager.unsubscribe(EventType.SESSION_CREATED, self._on_team_changed)
        if hasattr(self, "_defensive_content") and self._defensive_content:
            self._defensive_content.deleteLater()
        if hasattr(self, "_offensive_content") and self._offensive_content:
            self._offensive_content.deleteLater()

    def _analyze_team_balance(self) -> None:
        self._clear_analysis()
        balance_data = self._team_balance_service.calculate_team_balance()
        self._display_defensive_analysis(balance_data.defensive_categories)
        self._display_offensive_analysis(
            balance_data.offensive_coverage,
            balance_data.offensive_best_scores,
            balance_data.pokemon_best_moves,
            balance_data.pokemon_best_move_details,
        )

    def _clear_analysis(self) -> None:
        if hasattr(self, "_defensive_content") and self._defensive_content:
            self._defensive_content.deleteLater()
        if hasattr(self, "_offensive_content") and self._offensive_content:
            self._offensive_content.deleteLater()
        self._defensive_content = QWidget(self)
        self._defensive_content_layout = QVBoxLayout(self._defensive_content)
        if hasattr(self, "_defensive_tab") and self._defensive_tab.layout():
            scroll_area = self._defensive_tab.findChild(QScrollArea)
            if scroll_area:
                scroll_area.setWidget(self._defensive_content)
        self._offensive_content = QWidget(self)
        self._offensive_content_layout = QVBoxLayout(self._offensive_content)
        if hasattr(self, "_offensive_tab") and self._offensive_tab.layout():
            scroll_area = self._offensive_tab.findChild(QScrollArea)
            if scroll_area:
                scroll_area.setWidget(self._offensive_content)

    def _create_color_for_multiplier(self, multi: float, is_offensive: bool) -> QColor:  # noqa: C901
        color = QColor(255, 100, 100)
        if is_offensive:
            if multi >= ULTRA_EFFECTIVE_MULTI:
                color = QColor(0, 200, 0)
            elif multi >= SUPER_EFFECTIVE_MULTI:
                color = QColor(100, 255, 100)
            elif multi > NEUTRAL_MULTI:
                color = QColor(150, 220, 150)
            elif multi == NEUTRAL_MULTI:
                color = QColor(200, 200, 200)
            elif multi >= NOT_VERY_EFFECTIVE_MULTI:
                color = QColor(255, 150, 0)
        elif multi <= ULTRA_RESISTANCE_THRESHOLD:
            color = QColor(0, 200, 0)
        elif multi <= SUPER_RESISTANCE_THRESHOLD:
            color = QColor(100, 255, 100)
        elif multi < NEUTRAL_MULTI:
            color = QColor(150, 220, 150)
        elif multi == NEUTRAL_MULTI:
            color = QColor(200, 200, 200)
        elif multi <= WEAK_RESISTANCE_THRESHOLD:
            color = QColor(255, 150, 0)
        return color

    def _create_section_header(self, text: str, parent: QWidget) -> QLabel:
        frame = QFrame(parent)
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setFrameShadow(QFrame.Shadow.Raised)
        frame.setStyleSheet("background-color: #2c3e50; border-radius: 4px;")
        label = QLabel(text, frame)
        label.setStyleSheet("color: #ecf0f1;")
        font = QFont()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 2)
        label.setFont(font)
        label.setAlignment(ALIGN_CENTER)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.addWidget(label)
        return frame

    def _create_type_header(self, text: str, parent: QWidget) -> QLabel:
        label = QLabel(text, parent)
        label.setStyleSheet("color: #bdc3c7; border-bottom: 1px solid #34495e; padding: 4px;")
        font = QFont()
        font.setBold(True)
        label.setFont(font)
        label.setAlignment(ALIGN_CENTER)
        return label

    def _delayed_resize_update(self) -> None:
        if hasattr(self, "_type_filter") and self._type_filter:
            self._update_offensive_grid(self._type_filter.currentText())

    def _display_defensive_analysis(self, categories: dict[float, list[str]]) -> None:
        header = QLabel("Team Defensive Coverage Analysis", self._defensive_content)
        header.setAlignment(ALIGN_CENTER)
        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(header_font.pointSize() + 3)
        header.setFont(header_font)
        header.setStyleSheet("color: #3498db;")
        self._defensive_content_layout.addWidget(header)
        description = QLabel(
            "This analysis shows how susceptible your team is to each attack type.\n"
            "Lower multipliers are better (your team resists those types).\n"
            "Higher multipliers indicate potential weaknesses in your team composition.",
            self._defensive_content,
        )
        description.setWordWrap(True)
        self._defensive_content_layout.addWidget(description)
        for multi, types in sorted(categories.items(), key=lambda x: x[0], reverse=True):
            category_label = f"x{multi:.3g} Score"
            section_header = self._create_section_header(category_label, self._defensive_content)
            self._defensive_content_layout.addWidget(section_header)
            sorted_types = sorted(types)
            type_list = ", ".join(sorted_types)
            type_label = QLabel(type_list, self._defensive_content)
            type_label.setWordWrap(True)
            color = self._create_color_for_multiplier(multi, False)
            palette = type_label.palette()
            palette.setColor(type_label.foregroundRole(), color)
            type_label.setPalette(palette)
            self._defensive_content_layout.addWidget(type_label)
        self._defensive_content_layout.addStretch()

    def _display_offensive_analysis(
        self,
        offensive_data: dict[str, dict[str, float]],
        best_scores: dict[str, float],
        pokemon_best_moves: dict[str, dict[str, float]],
        pokemon_best_move_details: dict[str, dict[str, tuple[str, float]]],
    ) -> None:
        header = QLabel("Team Offensive Coverage Analysis", self._offensive_content)
        header.setAlignment(ALIGN_CENTER)
        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(header_font.pointSize() + 3)
        header.setFont(header_font)
        header.setStyleSheet("color: #3498db;")
        self._offensive_content_layout.addWidget(header)
        description = QLabel(
            "This analysis shows how effective your team's moves are against different type combinations.\n"
            "Higher multipliers are better (your moves are super effective).\n"
            "The team score is calculated by multiplying the best move from each team member.",
            self._offensive_content,
        )
        description.setWordWrap(True)
        self._offensive_content_layout.addWidget(description)
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter by type:", self._offensive_content)
        filter_layout.addWidget(filter_label)
        self._type_filter = QComboBox(self._offensive_content)
        self._type_filter.addItem("All Types")
        for type_name in sorted(TYPE_CHART.keys()):
            self._type_filter.addItem(type_name)
        self._type_filter.currentTextChanged.connect(self._filter_offensive_analysis)
        filter_layout.addWidget(self._type_filter)
        filter_layout.addStretch()
        self._offensive_content_layout.addLayout(filter_layout)
        self._offensive_grid_container = QWidget(self._offensive_content)
        self._offensive_grid_layout = QGridLayout(self._offensive_grid_container)
        self._offensive_content_layout.addWidget(self._offensive_grid_container)
        self._offensive_data = offensive_data
        self._best_scores = best_scores
        self._pokemon_best_moves = pokemon_best_moves
        self._pokemon_best_move_details = pokemon_best_move_details
        self._update_offensive_grid("All Types")
        self._offensive_content_layout.addStretch()

    def _filter_offensive_analysis(self, filter_type: str) -> None:
        self._update_offensive_grid(filter_type)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        tabs = QTabWidget(self)
        self._defensive_tab = QWidget(self)
        tabs.addTab(self._defensive_tab, "Defensive Coverage")
        self._offensive_tab = QWidget(self)
        tabs.addTab(self._offensive_tab, "Offensive Coverage")
        defensive_layout = QVBoxLayout(self._defensive_tab)
        defensive_scroll = QScrollArea(self)
        defensive_scroll.setWidgetResizable(True)
        self._defensive_content = QWidget(self)
        self._defensive_content_layout = QVBoxLayout(self._defensive_content)
        defensive_scroll.setWidget(self._defensive_content)
        defensive_layout.addWidget(defensive_scroll)
        offensive_layout = QVBoxLayout(self._offensive_tab)
        self._offensive_scroll = QScrollArea(self)
        self._offensive_scroll.setWidgetResizable(True)
        self._offensive_scroll.viewport().installEventFilter(self)
        self._offensive_content = QWidget(self)
        self._offensive_content_layout = QVBoxLayout(self._offensive_content)
        self._offensive_scroll.setWidget(self._offensive_content)
        offensive_layout.addWidget(self._offensive_scroll)
        layout.addWidget(tabs)

    def _on_team_changed(self, _: dict) -> None:
        self._analyze_team_balance()

    def _update_offensive_grid(self, filter_type: str) -> None:
        clear_layout(self._offensive_grid_layout)
        categories = {}
        for type_combo, score in self._best_scores.items():
            if filter_type != "All Types" and filter_type not in type_combo:
                continue
            if score not in categories:
                categories[score] = []
            categories[score].append(type_combo)
        sorted_categories = sorted(categories.items(), key=lambda x: x[0])
        container_width = (
            self._offensive_scroll.viewport().width() if hasattr(self, "_offensive_scroll") else 0
        )
        num_col = 6 if container_width >= SMALL_WINDOW_THRESHOLD else 3
        current_row = 0
        for score, type_combos in sorted_categories:
            if score <= 0:
                continue
            score_header = self._create_section_header(f"x{score:.3g} Score", self._offensive_grid_container)
            self._offensive_grid_layout.addWidget(score_header, current_row, 0, 1, num_col)
            current_row += 1
            for type_combo in sorted(type_combos):
                type_names = type_combo.split(",")
                combo_display = "/".join(type_names)
                combo_header = self._create_type_header(combo_display, self._offensive_grid_container)
                self._offensive_grid_layout.addWidget(combo_header, current_row, 0, 1, num_col)
                current_row += 1
                move_details = self._pokemon_best_move_details[type_combo]
                pokemon_moves = [(name, details) for name, details in move_details.items()]
                pokemon_moves.sort(key=lambda x: x[0])
                moves_container = QWidget(self._offensive_grid_container)
                moves_layout = QGridLayout(moves_container)
                for i, (pokemon_name, (move_name, effectiveness)) in enumerate(pokemon_moves):
                    row_idx = i // num_col
                    col_idx = i % num_col
                    move_info = f"{pokemon_name}: {move_name} (x{effectiveness:.2g})"
                    move_label = QLabel(move_info, moves_container)
                    move_label.setWordWrap(True)
                    color = self._create_color_for_multiplier(effectiveness, True)
                    move_label.setStyleSheet(f"color: {color.name()};")
                    moves_layout.addWidget(move_label, row_idx, col_idx)
                self._offensive_grid_layout.addWidget(moves_container, current_row, 0, 1, num_col)
                current_row += 1

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if (
            obj == self._offensive_scroll.viewport()
            and event.type() == QEvent.Type.Resize
            and hasattr(self, "_offensive_scroll")
            and self._type_filter
        ):
            self._resize_timer.start(RESIZE_DELAY)
        return super().eventFilter(obj, event)

    def set_state(self, game_state: GameState) -> None:
        self._game_state = game_state
        self._team_balance_service = TeamBalanceService(self._container, game_state)
        self._analyze_team_balance()
