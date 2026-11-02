"""Объекты сцены: зона, портрет, метка, подпись, декор."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsItem,
    QGraphicsPathItem,
)

from mapknowlage.catalog import Author, Zone
from mapknowlage.fonts import FONTS

RADIUS = 50.0


def loops_to_path(loops: list[list[tuple[float, float]]]) -> QPainterPath:
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.WindingFill)
    for loop in loops:
        if len(loop) < 3:
            continue
        path.addPath(_bezier(loop))
    return path


def _bezier(points: list[tuple[float, float]]) -> QPainterPath:
    path = QPainterPath()
    count = len(points)
    path.moveTo(points[0][0], points[0][1])
    for index in range(count):
        p0 = points[(index - 1) % count]
        p1 = points[index]
        p2 = points[(index + 1) % count]
        p3 = points[(index + 2) % count]
        path.cubicTo(
            p1[0] + (p2[0] - p0[0]) / 6.0,
            p1[1] + (p2[1] - p0[1]) / 6.0,
            p2[0] - (p3[0] - p1[0]) / 6.0,
            p2[1] - (p3[1] - p1[1]) / 6.0,
            p2[0],
            p2[1],
        )
    path.closeSubpath()
    return path


class ZoneItem(QGraphicsPathItem):
    def __init__(self, zone: Zone, loops: list[list[tuple[float, float]]]) -> None:
        super().__init__()
        self.zone = zone
        self.color = QColor(zone.color)
        self._hover = False
        self.centroid = QPointF(zone.cx, zone.cy)
        self.setPath(loops_to_path(loops))
        self.setAcceptHoverEvents(True)
        self.setData(0, "zone")
        self.setZValue(1)
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setToolTip(zone.name)
        self.setCacheMode(QGraphicsItem.CacheMode.ItemCoordinateCache)

    def hoverEnterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().hoverLeaveEvent(event)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = self.path()
        color = QColor(self.color)
        color.setAlpha(255 if self._hover else 236)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPath(path)

        ink = QPen(QColor("#2b2418"))
        ink.setWidthF(2.4)
        ink.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(ink)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    def _hatch(self, painter: QPainter, path: QPainterPath) -> None:
        bounds = path.boundingRect()
        cx = bounds.center().x()
        cy = bounds.center().y()
        pen = QPen(QColor("#2B1E12"))
        pen.setWidthF(1.6)
        painter.setPen(pen)
        steps = 110
        for index in range(steps):
            percent = index / steps
            point = path.pointAtPercent(percent)
            dx, dy = point.x() - cx, point.y() - cy
            length = math.hypot(dx, dy) or 1.0
            nx, ny = dx / length, dy / length
            tick = 8 + (index % 3) * 5
            painter.drawLine(
                QPointF(point.x() + nx * 2, point.y() + ny * 2),
                QPointF(point.x() + nx * tick, point.y() + ny * tick),
            )


class ZoneLabel(QGraphicsItem):
    def __init__(self, text: str, radius: float = 300) -> None:
        super().__init__()
        self.text = text.upper()
        self.font = QFont(FONTS.text)
        self.font.setWeight(QFont.Weight.DemiBold)
        limit = max(200.0, radius * 1.45)
        size = 86
        metrics = QFontMetrics(self.font)
        while size > 32:
            self.font.setPixelSize(size)
            metrics = QFontMetrics(self.font)
            if metrics.horizontalAdvance(self.text) <= limit:
                break
            size -= 2
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setData(0, "label")
        self.setZValue(8)
        self._width = metrics.horizontalAdvance(self.text) + 16
        self._height = metrics.height() + 8

    def boundingRect(self) -> QRectF:
        return QRectF(-self._width / 2, -self._height / 2, self._width, self._height)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setFont(self.font)
        rect = self.boundingRect()
        painter.setPen(QColor("#f4e7c4"))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            painter.drawText(rect.translated(dx, dy), Qt.AlignmentFlag.AlignCenter, self.text)
        painter.setPen(QColor("#2b1e12"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text)


class ZoneBoard(QGraphicsItem):
    """Карточка острова: тема, сколько книг прочитано, кто авторы. Размер в пикселях экрана."""

    WIDTH = 210.0

    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = title.upper()
        self.count_line = ""
        self.name_rows: list[list[tuple[str, bool]]] = []
        self._height = 64.0
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setData(0, "board")
        self.setZValue(30)

    def set_summary(
        self,
        names: list[tuple[str, bool]],
        books_done: int,
        books_total: int,
        authors_known: int,
    ) -> None:
        self.count_line = (
            f"книги {books_done}/{books_total}    авторы {authors_known}/{len(names)}"
        )
        self.name_rows = self._wrap(names)
        self.prepareGeometryChange()
        self._height = 14 + 18 + 16 + 14 * max(1, len(self.name_rows)) + 10
        self.update()

    def _wrap(self, names: list[tuple[str, bool]]) -> list[list[tuple[str, bool]]]:
        font = QFont(FONTS.text, 11)
        metrics = QFontMetrics(font)
        rows: list[list[tuple[str, bool]]] = []
        row: list[tuple[str, bool]] = []
        width = 0.0
        limit = self.WIDTH - 18
        for name, known in names:
            piece = name if not row else "   " + name
            advance = metrics.horizontalAdvance(piece)
            if row and width + advance > limit:
                rows.append(row)
                row = [(name, known)]
                width = float(metrics.horizontalAdvance(name))
            else:
                row.append((name, known))
                width += advance
        if row:
            rows.append(row)
        return rows

    def boundingRect(self) -> QRectF:
        return QRectF(-self.WIDTH / 2, -self._height / 2, self.WIDTH, self._height)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.boundingRect().adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(QColor("#2b2418"), 1.3))
        painter.setBrush(QColor(247, 239, 220, 242))
        painter.drawRoundedRect(rect, 5, 5)

        title_font = QFont(FONTS.text, 12)
        title_font.setWeight(QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor("#24180f"))
        painter.drawText(
            QRectF(rect.x() + 8, rect.y() + 4, rect.width() - 16, 18),
            Qt.AlignmentFlag.AlignCenter,
            self.title,
        )

        count_font = QFont(FONTS.text, 10)
        painter.setFont(count_font)
        painter.setPen(QColor("#5c4630"))
        painter.drawText(
            QRectF(rect.x() + 8, rect.y() + 22, rect.width() - 16, 15),
            Qt.AlignmentFlag.AlignCenter,
            self.count_line,
        )

        name_font = QFont(FONTS.text, 11)
        painter.setFont(name_font)
        metrics = QFontMetrics(name_font)
        y = rect.y() + 42
        for row in self.name_rows:
            pieces = []
            total = 0.0
            for index, (name, known) in enumerate(row):
                text = name if index == 0 else "   " + name
                pieces.append((text, known, name))
                total += metrics.horizontalAdvance(text)
            x = rect.center().x() - total / 2
            for text, known, _name in pieces:
                painter.setPen(QColor("#1f6b34") if known else QColor("#3a3128"))
                painter.drawText(QPointF(x, y), text)
                x += metrics.horizontalAdvance(text)
            y += 14


class AuthorItem(QGraphicsItem):
    def __init__(self, author: Author, portrait: QPixmap) -> None:
        super().__init__()
        self.author = author
        self.portrait = portrait
        self.acquainted = False
        self.stars = 0
        self.done = 0
        self.total = len(author.books)
        self.show_name = False
        self.setPos(author.x, author.y)
        self.setAcceptHoverEvents(True)
        self.setData(0, "author")
        self.setZValue(10)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hover = False
        self._label = author.name.split()[-1] if author.name.split() else author.name
        self._name_font = QFont(FONTS.text)
        self._name_font.setPixelSize(16)
        self._name_font.setWeight(QFont.Weight.Bold)
        self.setCacheMode(QGraphicsItem.CacheMode.ItemCoordinateCache)
        self._refresh_tip()

    def boundingRect(self) -> QRectF:
        return QRectF(-RADIUS - 110, -RADIUS - 28, (RADIUS + 110) * 2, RADIUS * 2 + 78)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), RADIUS + 8, RADIUS + 8)
        path.addRect(-RADIUS - 100, -RADIUS, 100, RADIUS + 10)
        path.addRect(RADIUS, -RADIUS, 46, RADIUS + 10)
        return path

    def apply_progress(self, acquainted: bool, stars: int, done: int) -> None:
        self.acquainted = acquainted
        self.stars = stars
        self.done = done
        self._refresh_tip()
        self.update()

    def _refresh_tip(self) -> None:
        self.setToolTip(
            f"{self.author.name}\n{self.author.years}\nПрочитано {self.done}/{self.total}"
        )

    def hoverEnterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().hoverLeaveEvent(event)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(43, 30, 18, 70))
        painter.drawEllipse(QPointF(3, 5), RADIUS, RADIUS)

        clip = QPainterPath()
        clip.addEllipse(QPointF(0, 0), RADIUS - 5, RADIUS - 5)
        painter.save()
        painter.setClipPath(clip)
        target = QRectF(-RADIUS + 5, -RADIUS + 5, (RADIUS - 5) * 2, (RADIUS - 5) * 2)
        painter.drawPixmap(target, self.portrait, QRectF(self.portrait.rect()))
        painter.restore()

        outer = QPen(QColor("#d7c39a") if self._hover else QColor("#b9975a"))
        outer.setWidthF(4.5)
        painter.setPen(outer)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(0, 0), RADIUS, RADIUS)
        inner = QPen(QColor("#8c6b1f"))
        inner.setWidthF(1.6)
        painter.setPen(inner)
        painter.drawEllipse(QPointF(0, 0), RADIUS - 6, RADIUS - 6)

        star_y = -RADIUS * 0.42
        if self.stars:
            badge_w = 10 + self.stars * 24
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(244, 230, 196, 235))
            painter.drawRoundedRect(
                QRectF(-RADIUS - 16 - badge_w, star_y - 15, badge_w + 8, 30),
                9,
                9,
            )
            for index in range(self.stars):
                _star(painter, -RADIUS - 22 - index * 24, star_y, 11, 4.6)
        if self.acquainted:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(244, 230, 196, 235))
            painter.drawEllipse(QPointF(RADIUS + 26, star_y), 15, 15)
            _check(painter, RADIUS + 16, star_y)

        if self.show_name:
            painter.setFont(self._name_font)
            metrics = QFontMetrics(self._name_font)
            width = metrics.horizontalAdvance(self._label) + 16
            height = metrics.height() + 6
            rect = QRectF(-width / 2, RADIUS + 5, width, height)
            painter.setPen(QPen(QColor("#3a2a18"), 1.4))
            painter.setBrush(QColor("#fff6e4"))
            painter.drawRoundedRect(rect, 5, 5)
            painter.setPen(QColor("#1a120c"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._label)


class MarkerItem(QGraphicsItem):
    def __init__(self, marker_id: int, x: float, y: float, icon: str, label: str) -> None:
        super().__init__()
        self.marker_id = marker_id
        self.icon = icon
        self.label = label
        self.setPos(x, y)
        self.setData(0, "marker")
        self.setZValue(12)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(label or icon)

    def boundingRect(self) -> QRectF:
        return QRectF(-24, -36, 140, 72)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#2b1e12"))
        pen.setWidthF(2)
        painter.setPen(pen)
        painter.setBrush(QColor("#e2b43a"))
        if self.icon == "scroll":
            painter.drawRoundedRect(QRectF(-16, -22, 32, 22), 4, 4)
            painter.drawLine(QPointF(-10, -16), QPointF(10, -16))
            painter.drawLine(QPointF(-10, -10), QPointF(6, -10))
        elif self.icon == "skull":
            painter.drawEllipse(QPointF(0, -16), 12, 11)
            painter.setBrush(QColor("#2b1e12"))
            painter.drawEllipse(QPointF(-4, -18), 2.2, 2.2)
            painter.drawEllipse(QPointF(4, -18), 2.2, 2.2)
        else:
            painter.drawLine(QPointF(0, -28), QPointF(0, 4))
            flag = QPainterPath()
            flag.moveTo(0, -28)
            flag.lineTo(18, -20)
            flag.lineTo(0, -12)
            flag.closeSubpath()
            painter.drawPath(flag)
        if self.label:
            painter.setPen(QColor("#2b1e12"))
            painter.setFont(QFont(FONTS.text, 11))
            painter.drawText(QRectF(16, -24, 110, 20), Qt.AlignmentFlag.AlignLeft, self.label)


class RoadItem(QGraphicsPathItem):
    def __init__(self, points: list[tuple[float, float]]) -> None:
        super().__init__()
        path = QPainterPath()
        if points:
            path.moveTo(points[0][0], points[0][1])
            for x, y in points[1:]:
                path.lineTo(x, y)
        pen = QPen(QColor("#4a3420"))
        pen.setWidthF(3)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setPath(path)
        self.setData(0, "decor")
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setZValue(2)


class CompassItem(QGraphicsItem):
    def __init__(self) -> None:
        super().__init__()
        self.setData(0, "decor")
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setZValue(0)

    def boundingRect(self) -> QRectF:
        return QRectF(-170, -170, 340, 340)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#4a3420"))
        pen.setWidthF(2)
        painter.setPen(pen)
        painter.setBrush(QColor(201, 168, 106, 80))
        painter.drawEllipse(QPointF(0, 0), 78, 78)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(0, 0), 118, 118)
        star = QPainterPath()
        for index in range(8):
            angle = -math.pi / 2 + index * math.pi / 4
            radius = 150 if index % 2 == 0 else 48
            x = math.cos(angle) * radius
            y = math.sin(angle) * radius
            if index == 0:
                star.moveTo(x, y)
            else:
                star.lineTo(x, y)
        star.closeSubpath()
        painter.setBrush(QBrush(QColor(201, 168, 106, 150)))
        painter.drawPath(star)
        painter.setPen(QColor("#2b1e12"))
        painter.setFont(QFont(FONTS.display, 14))
        painter.drawText(QRectF(-16, -158, 32, 22), Qt.AlignmentFlag.AlignCenter, "N")


class WhirlpoolItem(QGraphicsItem):
    def __init__(self) -> None:
        super().__init__()
        self.setData(0, "decor")
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setZValue(0)
        self._path = QPainterPath()
        for index in range(680):
            t = index / 680
            angle = t * math.pi * 7
            radius = 16 + t * 250
            x = math.cos(angle) * radius
            y = math.sin(angle) * radius * 0.82
            if index == 0:
                self._path.moveTo(x, y)
            else:
                self._path.lineTo(x, y)

    def boundingRect(self) -> QRectF:
        return QRectF(-280, -240, 560, 480)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(74, 48, 58, 210))
        pen.setWidthF(7)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self._path)


class ShipItem(QGraphicsItem):
    def __init__(self) -> None:
        super().__init__()
        self.setData(0, "decor")
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setZValue(0)

    def boundingRect(self) -> QRectF:
        return QRectF(-80, -70, 160, 110)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#3a2a1c"))
        pen.setWidthF(2)
        painter.setPen(pen)
        painter.setBrush(QColor(166, 124, 74, 180))
        hull = QPainterPath()
        hull.moveTo(-62, 8)
        hull.lineTo(62, 8)
        hull.lineTo(46, 28)
        hull.lineTo(-50, 28)
        hull.closeSubpath()
        painter.drawPath(hull)
        painter.drawLine(QPointF(0, 8), QPointF(0, -48))
        sail = QPainterPath()
        sail.moveTo(0, -44)
        sail.lineTo(36, -8)
        sail.lineTo(0, -8)
        sail.closeSubpath()
        painter.setBrush(QColor(244, 230, 196, 210))
        painter.drawPath(sail)


def _star(painter: QPainter, cx: float, cy: float, outer: float, inner: float) -> None:
    path = QPainterPath()
    for index in range(10):
        angle = -math.pi / 2 + index * math.pi / 5
        radius = outer if index % 2 == 0 else inner
        x = cx + math.cos(angle) * radius
        y = cy + math.sin(angle) * radius
        if index == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    path.closeSubpath()
    pen = QPen(QColor("#2b1e12"))
    pen.setWidthF(1.1)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(QColor("#ffe7a0"))
    painter.drawPath(path)


def _check(painter: QPainter, x: float, y: float) -> None:
    path = QPainterPath()
    path.moveTo(x, y)
    path.lineTo(x + 7, y + 8)
    path.lineTo(x + 20, y - 10)
    pen = QPen(QColor("#2f8a45"))
    pen.setWidthF(3.4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)
