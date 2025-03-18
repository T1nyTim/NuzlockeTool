import logging
import sys
from platform import python_version

from PyQt6.QtWidgets import QApplication

from nuzlocke_tool import __version__
from nuzlocke_tool.container import Container
from nuzlocke_tool.gui.main_window import NuzlockeTrackerMainWindow
from nuzlocke_tool.utils.logs import setup_logging

LOGGER = logging.getLogger(__name__)


def main() -> None:
    setup_logging(logging.WARNING)
    LOGGER.info("Python v%s", python_version())
    LOGGER.info("Nuzlocke Tool v%s", __version__)
    container = Container()
    app = QApplication(sys.argv)
    window = NuzlockeTrackerMainWindow(container)
    window.showMaximized()
    app.exec()


if __name__ == "__main__":
    main()
