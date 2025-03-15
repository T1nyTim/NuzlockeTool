import logging

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from nuzlocke_tool.config import PathConfig
from nuzlocke_tool.constants import (
    ALIGN_CENTER,
    LABEL_DECISION_CINNABAR_ENCOUNTER,
    LABEL_DECISION_DOJO_GIFT,
    LABEL_DECISION_EEVEELUTION,
    LABEL_DECISION_FOSSIL,
    LABEL_DECISION_MAGIKARP,
    LABEL_DECISION_SAFFRON_GIFT,
    LABEL_DECISION_STARTER,
    OBJECT_NAME_LABEL_OUTCOME,
    STYLE_SHEET_LABEL_OUTCOME,
)
from nuzlocke_tool.container import Container
from nuzlocke_tool.models.models import EventType, GameState
from nuzlocke_tool.models.view_models import DecisionViewModel
from nuzlocke_tool.services.random_decision_service import RandomDecisionService
from nuzlocke_tool.utils import clear_widget, load_yaml_file

LOGGER = logging.getLogger(__name__)


class RandomDecisionToolWidget(QWidget):
    def __init__(self, container: Container, game_state: GameState, parent: QWidget) -> None:
        super().__init__(parent)
        self._container = container
        self._decision_data = load_yaml_file(PathConfig.decisions_file())
        self._decisions = {}
        self._event_manager = self._container.event_manager()
        self._event_manager.subscribe(EventType.DECISION_MADE, self._on_decision_made)
        self._game_state = game_state
        self._journal_service = self._container.journal_service_factory(self._game_state)
        self._outcome_labels = {}
        self._save_service = self._container.save_service()
        self._view_models = []

    def _extract_decision_mapping(self) -> dict[str, list[str]]:
        decisions_mapping = {}
        for decision, info in self._decision_data.items():
            for generation in info:
                if self._game_state.game in generation["game"]:
                    decisions_mapping[decision] = generation["options"]
        return decisions_mapping

    def _generate_view_models(self) -> list[DecisionViewModel]:
        decision_mapping = self._extract_decision_mapping()
        view_models = []
        for key, options in decision_mapping.items():
            display_name = self._generate_decision_name(key)
            current_outcome = self._game_state.decisions.get(key)
            view_models.append(
                DecisionViewModel.create_from_data(key, display_name, options, current_outcome),
            )
        return view_models

    @staticmethod
    def _generate_decision_name(decision_key: str) -> str:
        statements = {
            "Starter": LABEL_DECISION_STARTER,
            "Magikarp": LABEL_DECISION_MAGIKARP,
            "Fossil": LABEL_DECISION_FOSSIL,
            "SaffronGift": LABEL_DECISION_SAFFRON_GIFT,
            "DojoGift": LABEL_DECISION_DOJO_GIFT,
            "Eeveelution": LABEL_DECISION_EEVEELUTION,
            "CinnabarEncounter": LABEL_DECISION_CINNABAR_ENCOUNTER,
        }
        return statements[decision_key]

    def _on_decision_made(self, data: dict[str, str]) -> None:
        decision_key = data["decision_key"]
        outcome = data["outcome"]
        if decision_key in self._outcome_labels:
            self._outcome_labels[decision_key].setText(outcome)
        for view_model in self._view_models:
            if view_model.key == decision_key:
                view_model.current_outcome = outcome
                break

    def _randomize_decision(self, view_model: DecisionViewModel) -> None:
        outcome = self._decision_service.make_decision(
            view_model.key,
            view_model.options,
            view_model.display_name,
        )
        LOGGER.info("Randomly decided: %s, from: %s", outcome, ", ".join(view_model.options))

    def init_ui(self) -> None:
        clear_widget(self)
        if self.layout() is None:
            layout = QVBoxLayout(self)
            self.setLayout(layout)
        else:
            layout = self.layout()
        self._view_models = self._generate_view_models()
        self._outcome_labels = {}
        for view_model in self._view_models:
            row_layout = QHBoxLayout()
            button = QPushButton(view_model.button_text, self)
            button.clicked.connect(lambda _, vm=view_model: self._randomize_decision(vm))
            row_layout.addWidget(button)
            outcome_label = QLabel(view_model.outcome_text, self)
            outcome_label.setAlignment(ALIGN_CENTER)
            outcome_label.setObjectName(OBJECT_NAME_LABEL_OUTCOME)
            outcome_label.setStyleSheet(STYLE_SHEET_LABEL_OUTCOME)
            row_layout.addWidget(outcome_label)
            self._outcome_labels[view_model.key] = outcome_label
            layout.addLayout(row_layout)
        layout.addStretch()

    def set_state(self, game_state: GameState) -> None:
        self._decision_data = load_yaml_file(PathConfig.decisions_file())
        self._decision_service = RandomDecisionService(self._container, game_state)
        self._game_state = game_state
        self._journal_service = self._container.journal_service_factory(game_state)
        self.init_ui()
