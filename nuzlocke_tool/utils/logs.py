import datetime
import logging

from rich.logging import RichHandler

from nuzlocke_tool import __version__
from nuzlocke_tool.config import PathConfig
from nuzlocke_tool.constants import CONSOLE, LOG_FILE_LIMIT


def setup_logging(console_log_level: int, file_log_level: int = logging.INFO) -> None:
    log_folder = PathConfig.get_project_root() / "logs"
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
