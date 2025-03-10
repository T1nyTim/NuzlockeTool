import logging
from dataclasses import asdict
from pathlib import Path

import yaml
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QLayout, QWidget

from nuzlocke_tool import images_folder
from nuzlocke_tool.constants import IMAGE_SIZE_POKEMON
from nuzlocke_tool.models import GameState, PartyManager

LOGGER = logging.getLogger(__name__)


def add_pokemon_image(layout: QLayout, species: str, parent: QWidget) -> QLabel:
    pixmap = load_pokemon_image(species)
    label = QLabel(parent)
    label.setPixmap(pixmap)
    label.setFixedSize(IMAGE_SIZE_POKEMON, IMAGE_SIZE_POKEMON)
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignHCenter)
    return label


def append_journal_entry(journal_file: Path, entry: str) -> None:
    with journal_file.open("a", encoding="utf-8") as f:
        f.write(f"{entry}\n")


def clear_layout(layout: QLayout) -> None:
    while layout.count():
        child = layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()
        elif child.layout():
            clear_layout(child.layout())

def clear_widget(widget: QWidget) -> None:
    layout = widget.layout()
    if layout is not None:
        clear_layout(layout)


def get_image_filename(species: str) -> str:
    mapping = {
        "Nidoran (F)": "nidoranf",
        "Nidoran (M)": "nidoranm",
        "Farfetch'd": "farfetchd",
        "Mr. Mime": "mr.mime",
    }
    return mapping.get(species, species.lower())


def load_pokemon_image(species: str) -> QPixmap:
    filename = get_image_filename(species)
    image_path = f"{images_folder()!s}/{filename}.png"
    return QPixmap(image_path)


def load_yaml_file(file_path: Path) -> dict[str, str | list[str]]:
    with file_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    LOGGER.info("Loaded YAML file: %s", str(file_path))
    return data

def save_session(game_state: GameState, party_manager: PartyManager) -> None:
    game_state_dict = asdict(game_state)
    game_state_dict["journal_file"] = str(game_state_dict["journal_file"])
    game_state_dict["save_file"] = str(game_state_dict["save_file"])
    data = {"game_state": game_state_dict, "party_manager": asdict(party_manager)}
    save_path = game_state.save_file
    with save_path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)
