"""Снимок карты без экрана, чтобы проверить раскладку."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from mapknowlage.app import build_window, configure
from mapknowlage.geometry import SCENE_H, SCENE_W


def main() -> None:
    app = QApplication([])
    configure(app)
    window = build_window()
    window.resize(1440, 900)
    window.show()
    app.processEvents()
    window.grab().save("preview.png")
    window.view.fit_all()
    app.processEvents()
    window.grab().save("preview_fit.png")

    methods = {}
    for shape in window.view.shapes:
        methods[shape.method] = methods.get(shape.method, 0) + 1
    print("methods", methods)
    print("scene", SCENE_W, SCENE_H)
    print("authors", len(window.catalog.authors))

    window.view.focus_author("plato")
    window.view.settle()
    plato = window.view.author_items["plato"]
    plato.stars = 3
    plato.acquainted = True
    plato.update()
    aurelius = window.view.author_items["aurelius"]
    aurelius.stars = 2
    aurelius.acquainted = True
    aurelius.update()
    app.processEvents()
    window.grab().save("preview_zoom.png")

    from mapknowlage.fonts import FONTS
    from mapknowlage.journal import JournalDialog

    dialog = JournalDialog(
        window.catalog.author("plato"),
        window.db,
        window.view.portrait_of("plato"),
        FONTS,
    )
    dialog.resize(620, 760)
    dialog.show()
    app.processEvents()
    dialog.grab().save("preview_journal.png")
    print("saved")


if __name__ == "__main__":
    main()
