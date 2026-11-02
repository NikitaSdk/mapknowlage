"""Сцена карты: плавный зум к курсору, перетаскивание, зоны и портреты."""

from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QGraphicsScene, QGraphicsView, QMenu

from mapknowlage.audio import Sounds
from mapknowlage.catalog import Catalog
from mapknowlage.database import ProgressDB
from mapknowlage.geometry import SCENE_H, SCENE_W, build_zone_shapes, place_authors
from mapknowlage.items import (
    AuthorItem,
    MarkerItem,
    RoadItem,
    ZoneItem,
    ZoneLabel,
)
from mapknowlage.portraits import load_portrait

MIN_ZOOM = 0.08
MAX_ZOOM = 2.2
PORTRAIT_ZOOM = 0.16
NAME_ZOOM = 0.55


class MapView(QGraphicsView):
    open_author_requested = Signal(str)
    view_changed = Signal()
    progress_changed = Signal()

    def __init__(self, catalog: Catalog, db: ProgressDB, sounds: Sounds) -> None:
        super().__init__()
        self.catalog = catalog
        self.db = db
        self.sounds = sounds
        self.author_items: dict[str, AuthorItem] = {}
        self.marker_items: dict[int, MarkerItem] = {}
        self.zone_items: list[ZoneItem] = []
        self.group_labels: list[ZoneLabel] = []
        self._fitted = False
        self._panning = False
        self._pan_pos = QPoint()
        self._drag_pixmap: QPixmap | None = None
        self._drag_delta = QPoint()
        self._press_author: AuthorItem | None = None
        self._press_pos = QPoint()
        self._cx = SCENE_W / 2
        self._cy = SCENE_H / 2
        self._scale = 0.72
        self._min_scale = MIN_ZOOM

        place_authors(catalog.zones, catalog.authors)
        self.shapes = build_zone_shapes(catalog.zones, catalog.authors)

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, SCENE_W, SCENE_H)
        self.setScene(self.scene)
        self._build_scene()

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)
        self.setBackgroundBrush(QColor("#d9cdb8"))
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)

    def _build_scene(self) -> None:
        zone_by_id = {zone.id: zone for zone in self.catalog.zones}
        for shape in self.shapes:
            zone = zone_by_id[shape.zone_id]
            item = ZoneItem(zone, shape.loops)
            self.scene.addItem(item)
            self.zone_items.append(item)
            label = ZoneLabel(zone.name, zone.radius)
            label.setPos(zone.cx, zone.cy)
            self.scene.addItem(label)

        self.labels: list[ZoneLabel] = [
            item for item in self.scene.items() if item.data(0) == "label" and item not in self.group_labels
        ]

        economy = zone_by_id.get("economy")
        economy_points: list[tuple[float, float]] = []
        for author in self.catalog.authors:
            if (
                author.zone == "economy"
                and economy is not None
                and economy.layout == "road"
            ):
                economy_points.append((author.x, author.y))
            zone = zone_by_id[author.zone]
            portrait = load_portrait(author.id, author.name, zone.color)
            item = AuthorItem(author, portrait)
            progress = self.db.author(author.id)
            done = self.db.done_count([book.id for book in author.books])
            item.apply_progress(progress.acquainted, progress.stars, done)
            self.scene.addItem(item)
            self.author_items[author.id] = item

        if len(economy_points) > 1:
            self.scene.addItem(RoadItem(economy_points))

        for marker in self.db.markers():
            self._add_marker_item(marker.id, marker.x, marker.y, marker.icon, marker.label)

    def portrait_of(self, author_id: str) -> object:
        return self.author_items[author_id].portrait

    def refresh_author(self, author_id: str) -> None:
        author = self.catalog.author(author_id)
        item = self.author_items[author_id]
        progress = self.db.author(author_id)
        done = self.db.done_count([book.id for book in author.books])
        item.apply_progress(progress.acquainted, progress.stars, done)
        self.progress_changed.emit()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._fitted:
            self._fitted = True
            self._scale = 0.85
            self._cx = 1680
            self._cy = 700
            self._apply()
            self._update_lod()
            self.view_changed.emit()

    def fit_all(self, animate: bool = True) -> None:
        del animate
        rect = self.scene.sceneRect().adjusted(36, 28, -36, -28)
        vw = max(1, self.viewport().width())
        vh = max(1, self.viewport().height() - 52)
        scale = min(vw / rect.width(), vh / rect.height()) * 0.98
        self._min_scale = max(MIN_ZOOM, scale * 0.92)
        self._scale = min(MAX_ZOOM, max(self._min_scale, scale))
        center = rect.center()
        self._cx = center.x()
        self._cy = center.y()
        self.settle()

    def settle(self) -> None:
        self._apply()
        self._update_lod()
        self.view_changed.emit()

    def focus_author(self, author_id: str) -> None:
        item = self.author_items[author_id]
        self._cx = item.scenePos().x()
        self._cy = item.scenePos().y()
        if self._scale < 0.95:
            self._scale = 0.95
        self.settle()

    def glide_to(self, point: QPointF) -> None:
        self._cx = point.x()
        self._cy = point.y()
        self.settle()

    def visible_scene_rect(self) -> QRectF:
        return self.mapToScene(self.viewport().rect()).boundingRect()

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        painter.fillRect(rect, QColor("#d3c6b0"))
        scene = self.sceneRect()
        gradient = QLinearGradient(scene.topLeft(), scene.bottomRight())
        gradient.setColorAt(0.0, QColor("#e7dcc8"))
        gradient.setColorAt(1.0, QColor("#d4c6af"))
        painter.fillRect(scene, gradient)

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            return
        steps = delta / 120.0
        factor = 1.14 ** steps
        view_pos = event.position()
        anchor = self.mapToScene(QPoint(int(view_pos.x()), int(view_pos.y())))
        new_scale = min(MAX_ZOOM, max(self._min_scale, self._scale * factor))
        if abs(new_scale - self._scale) < 1e-5:
            return
        self._scale = new_scale
        self._cx, self._cy = self._center_for(anchor, view_pos, new_scale)
        self._apply()
        self._update_lod()
        self.view_changed.emit()
        event.accept()

    def _center_for(self, anchor: QPointF, view_pos, scale: float) -> tuple[float, float]:
        width = self.viewport().width()
        height = self.viewport().height()
        return (
            anchor.x() - (view_pos.x() - width / 2) / scale,
            anchor.y() - (view_pos.y() - height / 2) / scale,
        )

    def _apply(self) -> None:
        self.resetTransform()
        self.scale(self._scale, self._scale)
        self.centerOn(self._cx, self._cy)

    def paintEvent(self, event) -> None:
        if self._panning and self._drag_pixmap is not None and not self._drag_pixmap.isNull():
            painter = QPainter(self.viewport())
            painter.fillRect(self.viewport().rect(), QColor("#d3c6b0"))
            painter.drawPixmap(self._drag_delta, self._drag_pixmap)
            painter.end()
            return
        super().paintEvent(event)

    def mousePressEvent(self, event) -> None:
        self.setFocus()
        view_pos = event.position().toPoint()
        kind, item = self._hit(view_pos)
        if event.button() == Qt.MouseButton.LeftButton and kind == "author":
            self._press_author = item
            self._press_pos = view_pos
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pixmap = self.viewport().grab()
            self._drag_delta = QPoint()
            self._pan_pos = view_pos
            self._panning = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            self._drag_delta = event.position().toPoint() - self._pan_pos
            self.viewport().update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._press_author is not None:
            pos = event.position().toPoint()
            if (pos - self._press_pos).manhattanLength() < 6:
                self.open_author_requested.emit(self._press_author.author.id)
            self._press_author = None
            event.accept()
            return
        if self._panning:
            delta = self._drag_delta
            self._panning = False
            self._drag_pixmap = None
            self._cx -= delta.x() / self._scale
            self._cy -= delta.y() / self._scale
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._apply()
            self.view_changed.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        step = 140.0 / max(self._scale, 0.2)
        if key in (Qt.Key.Key_A, Qt.Key.Key_Left):
            self._cx -= step
        elif key in (Qt.Key.Key_D, Qt.Key.Key_Right):
            self._cx += step
        elif key in (Qt.Key.Key_W, Qt.Key.Key_Up):
            self._cy -= step
        elif key in (Qt.Key.Key_S, Qt.Key.Key_Down):
            self._cy += step
        elif key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self._zoom_center(1.14)
            event.accept()
            return
        elif key == Qt.Key.Key_Minus:
            self._zoom_center(1 / 1.14)
            event.accept()
            return
        elif key == Qt.Key.Key_Home:
            self.fit_all()
            event.accept()
            return
        else:
            super().keyPressEvent(event)
            return
        self._apply()
        self.view_changed.emit()
        event.accept()

    def _zoom_center(self, factor: float) -> None:
        center = self.viewport().rect().center()
        view_pos = QPointF(center.x(), center.y())
        anchor = self.mapToScene(center)
        new_scale = min(MAX_ZOOM, max(self._min_scale, self._scale * factor))
        self._scale = new_scale
        self._cx, self._cy = self._center_for(anchor, view_pos, new_scale)
        self._apply()
        self._update_lod()
        self.view_changed.emit()

    def contextMenuEvent(self, event) -> None:
        view_pos = self.viewport().mapFromGlobal(event.globalPos())
        kind, item = self._hit(view_pos)
        if kind == "author":
            self._author_menu(item, event.globalPos())
        elif kind == "marker":
            self._marker_menu(item, event.globalPos())
        else:
            self._map_menu(self.mapToScene(view_pos), event.globalPos())
        event.accept()

    def _hit(self, view_pos: QPoint):
        for item in self.items(view_pos):
            kind = item.data(0)
            if kind in ("author", "marker", "zone"):
                return kind, item
        return None, None

    def _author_menu(self, item: AuthorItem, global_pos) -> None:
        author = item.author
        menu = QMenu(self)
        acquainted = menu.addAction("Ознакомлен")
        acquainted.setCheckable(True)
        acquainted.setChecked(item.acquainted)
        stars = menu.addMenu("Звёзды")
        star_actions = []
        for count, title in ((1, "★"), (2, "★★"), (3, "★★★"), (0, "Убрать звёзды")):
            action = stars.addAction(title)
            action.setData(count)
            star_actions.append(action)
        menu.addSeparator()
        open_journal = menu.addAction("Открыть журнал")
        chosen = menu.exec(global_pos)
        if chosen is None:
            return
        if chosen is acquainted:
            self.db.set_author(author.id, acquainted=chosen.isChecked())
            self.sounds.play("click")
            self.refresh_author(author.id)
        elif chosen in star_actions:
            self.db.set_author(author.id, stars=int(chosen.data()))
            self.sounds.play("click")
            self.refresh_author(author.id)
        elif chosen is open_journal:
            self.open_author_requested.emit(author.id)

    def _marker_menu(self, item: MarkerItem, global_pos) -> None:
        menu = QMenu(self)
        remove = menu.addAction("Убрать метку")
        if menu.exec(global_pos) is remove:
            self.db.delete_marker(item.marker_id)
            self.scene.removeItem(item)
            self.marker_items.pop(item.marker_id, None)
            self.sounds.play("click")

    def _map_menu(self, scene_pos: QPointF, global_pos) -> None:
        menu = QMenu(self)
        place = menu.addMenu("Поставить метку")
        flags = [
            (place.addAction("Флаг"), "flag"),
            (place.addAction("Свиток"), "scroll"),
            (place.addAction("Череп"), "skull"),
        ]
        chosen = menu.exec(global_pos)
        for action, icon in flags:
            if chosen is action:
                marker = self.db.add_marker(scene_pos.x(), scene_pos.y(), icon)
                self._add_marker_item(marker.id, marker.x, marker.y, marker.icon, marker.label)
                self.sounds.play("click")
                return

    def _add_marker_item(self, marker_id: int, x: float, y: float, icon: str, label: str) -> None:
        item = MarkerItem(marker_id, x, y, icon, label)
        self.scene.addItem(item)
        self.marker_items[marker_id] = item

    def _update_lod(self) -> None:
        scale = self.transform().m11()
        show_portraits = scale >= PORTRAIT_ZOOM
        show_names = scale >= NAME_ZOOM
        show_groups = scale >= 0.85
        for item in self.author_items.values():
            if item.isVisible() != show_portraits:
                item.setVisible(show_portraits)
            if item.show_name != show_names:
                item.show_name = show_names
                item.update()
        for label in self.group_labels:
            label.setVisible(show_groups)

