import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class PathConfig:
    @staticmethod
    def decisions_file() -> Path:
        file = PathConfig.resources_folder() / "decisions.yaml"
        if not file.exists():
            LOGGER.critical("Decisions file does not exist: %s", file)
        return file

    @staticmethod
    def get_project_root() -> Path:
        return Path(__file__).parent.parent

    @staticmethod
    def images_folder() -> Path:
        folder = PathConfig.resources_folder() / "images"
        if not folder.exists():
            LOGGER.error("Images folder does not exist: %s", folder)
        return folder

    @staticmethod
    def journal_folder() -> Path:
        folder = PathConfig.get_project_root() / "journal"
        if not folder.exists():
            LOGGER.warning("Journal folder does not exist: %s", folder)
            folder.mkdir(parents=True, exist_ok=True)
            LOGGER.info("Journal folder created.")
        return folder

    @staticmethod
    def locations_file() -> Path:
        file = PathConfig.resources_folder() / "locations.yaml"
        if not file.exists():
            LOGGER.critical("Locations file does not exist: %s", file)
        return file

    @staticmethod
    def resources_folder() -> Path:
        folder = PathConfig.get_project_root() / "resources"
        if not folder.exists():
            LOGGER.critical("Resources folder does not exist: %s", folder)
        return folder

    @staticmethod
    def rules_file() -> Path:
        file = PathConfig.resources_folder() / "rules.yaml"
        if not file.exists():
            LOGGER.critical("Rules file does not exist: %s", file)
        return file

    @staticmethod
    def save_folder() -> Path:
        folder = PathConfig.get_project_root() / "save"
        if not folder.exists():
            LOGGER.warning("Save folder does not exist: %s", folder)
            folder.mkdir(parents=True, exist_ok=True)
            LOGGER.info("Save folder created.")
        return folder

    @staticmethod
    def versions_file() -> Path:
        file = PathConfig.resources_folder() / "versions.yaml"
        if not file.exists():
            LOGGER.critical("Rules file does not exist: %s", file)
        return file
