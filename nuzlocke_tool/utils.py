import logging
from pathlib import Path
from typing import Any

import yaml
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QLayout, QWidget

from nuzlocke_tool.config import PathConfig
from nuzlocke_tool.constants import IMAGE_SIZE_POKEMON

LOGGER = logging.getLogger(__name__)


def add_pokemon_image(layout: QLayout, species: str, parent: QWidget) -> QLabel:
    pixmap = load_pokemon_image(species)
    label = QLabel(parent)
    label.setPixmap(pixmap)
    label.setFixedSize(IMAGE_SIZE_POKEMON, IMAGE_SIZE_POKEMON)
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignHCenter)
    return label


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
    image_path = f"{PathConfig.images_folder()!s}/{filename}.png"
    return QPixmap(image_path)


def load_yaml_file(file_path: Path) -> dict[str, Any]:
    with file_path.open("r") as f:
        data = yaml.safe_load(f)
    LOGGER.info("Loaded YAML file: %s", str(file_path))
    return data
