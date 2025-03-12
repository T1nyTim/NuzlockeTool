import datetime
import logging
from pathlib import Path

from rich.logging import RichHandler

from nuzlocke_tool.constants import CONSOLE, LOG_FILE_LIMIT

__version__ = "0.5.2"

LOGGER = logging.getLogger(__name__)


def decisions_file() -> Path:
    file = resources_folder() / "decisions.yaml"
    if not file.exists():
        LOGGER.critical("Decisions file does not exist: %s", file)
    return file


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def images_folder() -> Path:
    folder = resources_folder() / "images"
    if not folder.exists():
        LOGGER.error("Images folder does not exist: %s", folder)
    return folder


def journal_folder() -> Path:
    folder = get_project_root() / "journal"
    if not folder.exists():
        LOGGER.warning("Journal folder does not exist: %s", folder)
        folder.mkdir(parents=True, exist_ok=True)
        LOGGER.info("Journal folder created.")
    return folder


def locations_file() -> Path:
    file = resources_folder() / "locations.yaml"
    if not file.exists():
        LOGGER.critical("Locations file does not exist: %s", file)
    return file


def resources_folder() -> Path:
    folder = get_project_root() / "resources"
    if not folder.exists():
        LOGGER.critical("Resources folder does not exist: %s", folder)
    return folder


def rules_file() -> Path:
    file = resources_folder() / "rules.yaml"
    if not file.exists():
        LOGGER.critical("Rules file does not exist: %s", file)
    return file


def setup_logging(console_log_level: int, file_log_level: int = logging.INFO) -> None:
    log_folder = get_project_root() / "logs"
    log_folder.mkdir(parents=True, exist_ok=True)
    log_files = sorted(log_folder.glob("*.log"), key=lambda f: f.stat().st_mtime)
    while len(log_files) >= LOG_FILE_LIMIT:
        log_files.pop(0).unlink()
    console_handler = RichHandler(
        level=console_log_level,
        console=CONSOLE,
        show_time=False,
        rich_tracebacks=True,
    )
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    log_filename = f"{datetime.datetime.now(tz=datetime.UTC):%Y%m%d_%H%M%S}_v{__version__}.log"
    file_handler = logging.FileHandler(filename=log_folder / log_filename)
    file_handler.setLevel(file_log_level)
    logging.basicConfig(
        format="[%(asctime)s] [%(levelname)s] {%(name)s} | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=file_log_level,
        handlers=[console_handler, file_handler],
    )


def save_folder() -> Path:
    folder = get_project_root() / "save"
    if not folder.exists():
        LOGGER.warning("Save folder does not exist: %s", folder)
        folder.mkdir(parents=True, exist_ok=True)
        LOGGER.info("Save folder created.")
    return folder


def versions_file() -> Path:
    file = resources_folder() / "versions.yaml"
    if not file.exists():
        LOGGER.critical("Rules file does not exist: %s", file)
    return file
