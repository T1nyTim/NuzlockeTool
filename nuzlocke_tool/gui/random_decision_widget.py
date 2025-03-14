import logging
import random

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
from nuzlocke_tool.models import GameState
from nuzlocke_tool.utils import clear_widget, load_yaml_file

LOGGER = logging.getLogger(__name__)


class RandomDecisionToolWidget(QWidget):
    def __init__(self, container: Container, game_state: GameState, parent: QWidget) -> None:
        super().__init__(parent)
        self._container = container
        self._decision_data = load_yaml_file(PathConfig.decisions_file())
        self._decisions = {}
        self._game_state = game_state
        self._journal_service = self._container.journal_service_factory(self._game_state)
        self._save_service = self._container.save_service()

    def _extract_decision_mapping(self) -> dict[str, list[str]]:
        decisions_mapping = {}
        for decision, info in self._decision_data.items():
            for generation in info:
                if self._game_state.game in generation["game"]:
                    decisions_mapping[decision] = generation["options"]
        return decisions_mapping

    def init_ui(self) -> None:
        clear_widget(self)
        if self.layout() is None:
            layout = QVBoxLayout(self)
            self.setLayout(layout)
        else:
            layout = self.layout()
        self._decision_data = self._extract_decision_mapping()
        for decision, options in self._decision_data.items():
            row_layout = QHBoxLayout()
            button = QPushButton(f"Randomly pick {self._generate_decision_name(decision)}", self)
            button.clicked.connect(lambda _, key=decision: self._randomize_decision(key))
            row_layout.addWidget(button)
            outcome_label = QLabel("", self)
            outcome_label.setAlignment(ALIGN_CENTER)
            outcome_label.setObjectName(OBJECT_NAME_LABEL_OUTCOME)
            outcome_label.setStyleSheet(STYLE_SHEET_LABEL_OUTCOME)
            if decision in self._game_state.decisions:
                outcome_label.setText(self._game_state.decisions[decision])
            row_layout.addWidget(outcome_label)
            layout.addLayout(row_layout)
            self._decisions[decision] = (options, outcome_label)
        layout.addStretch()

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

    def _randomize_decision(self, decision_key: str) -> None:
        decision, outcome_label = self._decisions.get(decision_key, (None, None))
        outcome = random.choice(decision)
        outcome_label.setText(outcome)
        self._game_state.decisions[decision_key] = outcome
        self._save_service.save_session(self._game_state)
        self._journal_service.add_decision_entry(self._generate_decision_name(decision_key), outcome)
        LOGGER.info("Randomly decided: %s, from: %s", outcome, ", ".join(decision))

    def set_state(self, game_state: GameState) -> None:
        self._decision_data = load_yaml_file(PathConfig.decisions_file())
        self._game_state = game_state
        self._journal_service = self._container.journal_service_factory(game_state)
        self.init_ui()
