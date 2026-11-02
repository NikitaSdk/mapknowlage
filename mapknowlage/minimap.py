"""Миникарта в углу."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class Minimap(QWidget):
    jumped = Signal(QPointF)

    def __init__(
        self,
        parent,
        zones: list[tuple[QColor, QPainterPath]],
        scene_rect: QRectF,
    ) -> None:
        super().__init__(parent)
        self.zones = zones
        self.scene_rect = scene_rect
        self.view_rect = QRectF()
        self.setFixedSize(220, 148)
        self._ox = 8.0
        self._oy = 8.0
        self._scale = 1.0

    def set_view_rect(self, rect: QRectF) -> None:
        self.view_rect = rect
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#3c4a44"))
        painter.setPen(QPen(QColor("#d4af37"), 2))
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))

        target = self.rect().adjusted(8, 8, -8, -8)
        scale = min(
            target.width() / self.scene_rect.width(),
            target.height() / self.scene_rect.height(),
        )
        self._scale = scale
        self._ox = target.x() + (target.width() - self.scene_rect.width() * scale) / 2
        self._oy = target.y() + (target.height() - self.scene_rect.height() * scale) / 2

        painter.save()
        painter.translate(self._ox, self._oy)
        painter.scale(scale, scale)
        painter.translate(-self.scene_rect.x(), -self.scene_rect.y())
        painter.setPen(QPen(QColor("#2b1e12"), 8))
        for color, path in self.zones:
            painter.setBrush(color)
            painter.drawPath(path)
        if not self.view_rect.isNull():
            frame = QPen(QColor("#f4e6c0"))
            frame.setWidthF(max(2.0, 2.0 / scale))
            painter.setPen(frame)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.view_rect)
        painter.restore()

    def mousePressEvent(self, event) -> None:
        if self._scale <= 0:
            return
        x = (event.position().x() - self._ox) / self._scale + self.scene_rect.x()
        y = (event.position().y() - self._oy) / self._scale + self.scene_rect.y()
        self.jumped.emit(QPointF(x, y))
