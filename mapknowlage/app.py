"""Точка входа окна."""

from __future__ import annotations

import sys

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from mapknowlage.audio import Sounds
from mapknowlage.catalog import load_catalog
from mapknowlage.database import ProgressDB
from mapknowlage.fonts import FONTS, load_fonts
from mapknowlage.paths import asset_dir, progress_path
from mapknowlage.style import app_stylesheet
from mapknowlage.window import MainWindow


def configure(app: QApplication) -> None:
    app.setStyle("Fusion")
    load_fonts()
    app.setStyleSheet(app_stylesheet(FONTS.text, FONTS.display))
    app.setFont(QFont(FONTS.text, 12))
    icon = asset_dir() / "icon.png"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))


def build_window() -> MainWindow:
    catalog = load_catalog()
    database = ProgressDB(progress_path())
    sounds = Sounds()
    return MainWindow(catalog, database, sounds)


def main() -> None:
    app = QApplication(sys.argv)
    configure(app)
    window = build_window()
    window.show()
    sys.exit(app.exec())
