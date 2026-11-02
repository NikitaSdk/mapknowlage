"""Окно автора: портрет, биография, книги и отметки."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal
import numpy as np

from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mapknowlage.catalog import Author
from mapknowlage.database import ProgressDB
from mapknowlage.fonts import FontBook
from mapknowlage.style import journal_stylesheet

def _star_icon(filled: bool) -> QIcon:
    pixmap = QPixmap(36, 36)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    for index in range(10):
        angle = -math.pi / 2 + index * math.pi / 5
        radius = 14 if index % 2 == 0 else 6
        x = 18 + math.cos(angle) * radius
        y = 18 + math.sin(angle) * radius
        if index == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    path.closeSubpath()
    pen = QPen(QColor("#8c6b1f"))
    pen.setWidthF(1.4)
    painter.setPen(pen)
    painter.setBrush(QColor("#e2b43a") if filled else Qt.GlobalColor.transparent)
    painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)


def _parchment(width: int, height: int) -> QPixmap:
    rng = np.random.default_rng(4)
    yy = np.linspace(0, 1, height)[:, None]
    xx = np.linspace(0, 1, width)[None, :]
    noise = rng.normal(0, 8, (height, width))
    red = np.clip(236 - yy * 34 - xx * 10 + noise, 0, 255)
    green = np.clip(214 - yy * 40 - xx * 8 + noise * 0.85, 0, 255)
    blue = np.clip(168 - yy * 36 + noise * 0.4, 0, 255)
    rgb = np.dstack((red, green, blue)).astype(np.uint8)
    image = QImage(rgb.data, width, height, width * 3, QImage.Format.Format_RGB888).copy()
    return QPixmap.fromImage(image)


STATUSES = (
    ("planned", "В планах"),
    ("reading", "Читаю"),
    ("done", "Прочитано"),
)


class JournalDialog(QDialog):
    saved = Signal(str)

    def __init__(self, author: Author, db: ProgressDB, portrait: QPixmap, fonts: FontBook, parent=None) -> None:
        super().__init__(parent)
        self.author = author
        self.db = db
        self.setWindowTitle(author.name)
        self.setModal(True)
        self.resize(640, 780)
        self._paper = _parchment(640, 780)
        self.setStyleSheet(journal_stylesheet(fonts.text))

        page = QWidget()
        page.setObjectName("page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setSpacing(8)

        header = QHBoxLayout()
        avatar = QLabel()
        avatar.setPixmap(
            portrait.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )
        text_col = QVBoxLayout()
        name = QLabel(author.name)
        name.setObjectName("name")
        name.setWordWrap(True)
        text_col.addWidget(name)
        meta_text = " · ".join(part for part in (author.years, author.place) if part)
        meta = QLabel(meta_text)
        meta.setObjectName("meta")
        meta.setWordWrap(True)
        text_col.addWidget(meta)
        text_col.addStretch(1)
        header.addLayout(text_col, 1)
        header.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)

        self._section(layout, "О нём")
        bio = QLabel(author.bio)
        bio.setObjectName("bio")
        bio.setWordWrap(True)
        layout.addWidget(bio)

        if author.family:
            self._section(layout, "Семья")
            family = QLabel(author.family)
            family.setObjectName("family")
            family.setWordWrap(True)
            layout.addWidget(family)

        progress = db.author(author.id)
        self.stars = progress.stars
        self._section(layout, "Отметки")
        star_row = QHBoxLayout()
        self.star_buttons: list[QPushButton] = []
        for index in range(1, 4):
            button = QPushButton()
            button.setObjectName("star")
            button.setFixedSize(36, 36)
            button.setIconSize(button.size() * 0.7)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, value=index: self._set_stars(value))
            self.star_buttons.append(button)
            star_row.addWidget(button)
        star_row.addStretch(1)
        layout.addLayout(star_row)
        self._paint_stars()

        self.acquainted = QCheckBox("Ознакомлен")
        self.acquainted.setChecked(progress.acquainted)
        self.acquainted.stateChanged.connect(self._save_author)
        layout.addWidget(self.acquainted)

        self._section(layout, "Книги")
        self.combos: list[tuple[str, QComboBox]] = []
        for book in author.books:
            row = QHBoxLayout()
            bullet = QLabel("○")
            bullet.setObjectName("bullet")
            bullet.setFixedWidth(18)
            title = QLabel(book.title)
            title.setObjectName("book")
            title.setWordWrap(True)
            combo = QComboBox()
            for value, label in STATUSES:
                combo.addItem(label, value)
            current = db.book(book.id).status
            combo.setCurrentIndex(max(0, combo.findData(current)))
            combo.currentIndexChanged.connect(lambda _index, book_id=book.id, box=combo: self._save_book(book_id, box))
            row.addWidget(bullet, 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(title, 1)
            row.addWidget(combo)
            layout.addLayout(row)
            self.combos.append((book.id, combo))

        self.note = QTextEdit()
        self.note.setPlaceholderText("Заметка")
        self.note.setPlainText(progress.note)
        self.note.setFixedHeight(88)
        self.note.textChanged.connect(self._save_author)
        layout.addWidget(self.note)

        self.suggest = QPushButton("Все книги прочитаны — поставить галочку")
        self.suggest.clicked.connect(self._mark_acquainted)
        layout.addWidget(self.suggest)
        self._refresh_suggest()
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(page)
        scroll.viewport().setAutoFillBackground(False)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.addWidget(scroll)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self._paper)
        painter.setPen(QPen(QColor("#3a2a18"), 8))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.rect().adjusted(4, 4, -5, -5))
        painter.end()

    def _section(self, layout: QVBoxLayout, title: str) -> None:
        label = QLabel(f"●  {title}")
        label.setObjectName("section")
        layout.addSpacing(8)
        layout.addWidget(label)

    def _paint_stars(self) -> None:
        for index, button in enumerate(self.star_buttons, start=1):
            button.setIcon(_star_icon(index <= self.stars))

    def _set_stars(self, value: int) -> None:
        self.stars = 0 if self.stars == value else value
        self._paint_stars()
        self._save_author()

    def _mark_acquainted(self) -> None:
        self.acquainted.setChecked(True)

    def _save_author(self, *_args) -> None:
        self.db.set_author(
            self.author.id,
            acquainted=self.acquainted.isChecked(),
            stars=self.stars,
            note=self.note.toPlainText(),
        )
        self._refresh_suggest()
        self.saved.emit(self.author.id)

    def _save_book(self, book_id: str, combo: QComboBox) -> None:
        self.db.set_book(book_id, status=str(combo.currentData()))
        self._refresh_suggest()
        self.saved.emit(self.author.id)

    def _refresh_suggest(self) -> None:
        if not self.author.books:
            self.suggest.hide()
            return
        done = all(self.db.book(book.id).status == "done" for book in self.author.books)
        self.suggest.setVisible(done and not self.acquainted.isChecked())
