"""Главное окно: карта, поиск и счётчик."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QWidget,
)
from PySide6.QtWidgets import QCompleter

from mapknowlage.audio import Sounds
from mapknowlage.catalog import Catalog
from mapknowlage.database import ProgressDB
from mapknowlage.fonts import FONTS
from mapknowlage.journal import JournalDialog
from mapknowlage.minimap import Minimap
from mapknowlage.view import MapView


class MainWindow(QMainWindow):
    def __init__(self, catalog: Catalog, db: ProgressDB, sounds: Sounds) -> None:
        super().__init__()
        self.catalog = catalog
        self.db = db
        self.sounds = sounds
        self.setWindowTitle("MapKnowlage")
        self.resize(1440, 900)

        self.view = MapView(catalog, db, sounds)
        self.setCentralWidget(self.view)
        self.view.open_author_requested.connect(self.open_journal)
        self.view.progress_changed.connect(self._refresh_stats)
        self.view.view_changed.connect(self._refresh_minimap)

        self.hud = QWidget(self.view)
        self.hud.setObjectName("hud")
        hud_layout = QHBoxLayout(self.hud)
        hud_layout.setContentsMargins(16, 8, 16, 8)
        self.title = QLabel("MAPKNOWLAGE")
        self.title.setStyleSheet(
            f'font-family: "{FONTS.display}"; font-size: 16px; letter-spacing: 1px; color: #f3e6c4; background: transparent;'
        )
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск автора или книги")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(360)
        self.search.setStyleSheet(
            f"""
            QLineEdit {{
                background: #f4e6c0;
                color: #2b1e12;
                border: 1px solid #d4af37;
                padding: 6px 10px;
                font-family: "{FONTS.text}";
                font-size: 16px;
            }}
            """
        )
        self.stats = QLabel()
        self.stats.setStyleSheet(
            f'font-family: "{FONTS.text}"; font-size: 16px; color: #f3e6c4; background: transparent;'
        )
        self.mute = QPushButton("Звук")
        self.mute.setCheckable(True)
        self.mute.setChecked(True)
        self.mute.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mute.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                color: #f3e6c4;
                border: 1px solid #d4af37;
                padding: 4px 10px;
                font-family: "{FONTS.text}";
                font-size: 15px;
            }}
            QPushButton:checked {{
                background: #8c6b1f;
            }}
            """
        )
        self.mute.toggled.connect(self._toggle_sound)
        hud_layout.addWidget(self.title)
        hud_layout.addStretch(1)
        hud_layout.addWidget(self.search)
        hud_layout.addStretch(1)
        hud_layout.addWidget(self.stats)
        hud_layout.addWidget(self.mute)
        self.hud.setStyleSheet("QWidget#hud { background: rgba(43, 30, 18, 220); }")

        labels = []
        self._search_targets: dict[str, str] = {}
        for author in catalog.authors:
            self._remember(labels, author.name, author.id)
            for book in author.books:
                self._remember(labels, f"{book.title} — {author.name}", author.id)
        completer = QCompleter(labels, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.search.setCompleter(completer)
        completer.activated.connect(self._jump)

        zone_paint = [(item.color, item.path()) for item in self.view.zone_items]
        self.minimap = Minimap(self.view, zone_paint, self.view.scene.sceneRect())
        self.minimap.jumped.connect(self.view.glide_to)

        self.hint = QLabel("Колесо — плавный масштаб    перетаскивание — обзор    ПКМ — метка    Home — вся карта", self.view)
        self.hint.setStyleSheet(
            f'background: rgba(244, 230, 192, 220); color: #2b1e12; padding: 4px 8px; font-family: "{FONTS.text}"; font-size: 14px;'
        )
        self._refresh_stats()
        self._layout_overlays()

    def _remember(self, labels: list[str], text: str, author_id: str) -> None:
        if text not in self._search_targets:
            labels.append(text)
            self._search_targets[text] = author_id

    def _jump(self, text: str) -> None:
        author_id = self._search_targets.get(text)
        if author_id:
            self.view.focus_author(author_id)
            self.view.setFocus()

    def _toggle_sound(self, enabled: bool) -> None:
        self.sounds.enabled = enabled

    def _refresh_stats(self) -> None:
        authors = len(self.catalog.authors)
        unique_books = {book.id for author in self.catalog.authors for book in author.books}
        self.stats.setText(
            f"Ознакомлено {self.db.acquainted_count()} / {authors}    "
            f"Книг {self.db.done_books_total()} / {len(unique_books)}"
        )

    def _refresh_minimap(self) -> None:
        self.minimap.set_view_rect(self.view.visible_scene_rect())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._layout_overlays()

    def _layout_overlays(self) -> None:
        self.hud.setGeometry(0, 0, self.view.width(), 56)
        self.hint.adjustSize()
        self.hint.move(16, self.view.height() - self.hint.height() - 14)
        self.minimap.move(
            self.view.width() - self.minimap.width() - 16,
            self.view.height() - self.minimap.height() - 16,
        )
        self.hud.raise_()
        self.minimap.raise_()
        self.hint.raise_()

    def open_journal(self, author_id: str) -> None:
        author = self.catalog.author(author_id)
        dialog = JournalDialog(author, self.db, self.view.portrait_of(author_id), FONTS, self)
        dialog.saved.connect(self.view.refresh_author)
        self.sounds.play("open")
        dialog.exec()
        self.view.refresh_author(author_id)
