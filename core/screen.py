"""Per-monitor work areas and transfers across connected desktop edges."""

import random
import math
from dataclasses import dataclass

from PySide6.QtCore import QObject, QPoint, QRect, QSize
from PySide6.QtGui import QGuiApplication
from platforms.windows import monitors


@dataclass(frozen=True)
class Display:
    name: str
    geometry: QRect
    available: QRect
    native: tuple[int, int, int, int]

    @property
    def scale(self):
        left, top, right, bottom = self.native
        return (right - left) / self.geometry.width(), (bottom - top) / self.geometry.height()

    def to_native(self, x, y):
        sx, sy = self.scale
        return self.native[0] + (x - self.geometry.x()) * sx, self.native[1] + (y - self.geometry.y()) * sy

    def from_native(self, x, y):
        sx, sy = self.scale
        return self.geometry.x() + (x - self.native[0]) / sx, self.geometry.y() + (y - self.native[1]) / sy

    def contains_native(self, x, y):
        left, top, right, bottom = self.native
        return left <= x < right and top <= y < bottom


class DesktopLayout(QObject):
    """Connected monitor topology, including Qt's mixed-DPI coordinate gaps."""

    def __init__(self, parent=None, displays=None):
        super().__init__(parent)
        self.displays = list(displays or [])
        self._watched = set()
        if displays is None:
            app = QGuiApplication.instance()
            app.screenAdded.connect(self.refresh)
            app.screenRemoved.connect(self.refresh)
            self.refresh()

    def refresh(self, *_):
        native = monitors()
        self.displays = []
        for screen in QGuiApplication.screens():
            geometry = screen.geometry()
            match = next((m for m in native if m.rect[:2] == (geometry.x(), geometry.y())), None)
            ratio = screen.devicePixelRatio()
            rect = match.rect if match else (geometry.x(), geometry.y(),
                geometry.x() + round(geometry.width() * ratio), geometry.y() + round(geometry.height() * ratio))
            self.displays.append(Display(screen.name(), geometry, screen.availableGeometry(), rect))
            if screen not in self._watched:
                self._watched.add(screen)
                screen.geometryChanged.connect(self.refresh)
                screen.availableGeometryChanged.connect(self.refresh)
                screen.logicalDotsPerInchChanged.connect(self.refresh)
                screen.destroyed.connect(lambda _=None, s=screen: self._watched.discard(s))
        if not self.displays:
            raise RuntimeError("No desktop screen is available")

    def at(self, position):
        return next((d for d in self.displays if d.geometry.contains(position)),
                    min(self.displays, key=lambda d: self._distance(d.geometry, position)))

    @staticmethod
    def _distance(rect, point):
        dx = max(rect.x() - point.x(), 0, point.x() - (rect.x() + rect.width()))
        dy = max(rect.y() - point.y(), 0, point.y() - (rect.y() + rect.height()))
        return dx * dx + dy * dy

    def current(self, display, position):
        return next((d for d in self.displays if d.name == display.name), self.at(position))

    def neighbor(self, display, side, x, y, width, height):
        """Open a seam only where the whole sprite can enter usable desktop."""
        g, a = display.geometry, display.available
        left, top, right, bottom = display.native
        nx, ny = display.to_native(x + width / 2, y + height / 2)
        edges = {"left": (a.x() == g.x(), left - .5, ny),
                 "right": (a.x() + a.width() == g.x() + g.width(), right + .5, ny),
                 "top": (a.y() == g.y(), nx, top - .5),
                 "bottom": (a.y() + a.height() == g.y() + g.height(), nx, bottom + .5)}
        open_edge, px, py = edges[side]
        if not open_edge:
            return None
        for other in self.displays:
            if other.name == display.name or not other.contains_native(px, py):
                continue
            ox, oy = other.from_native(px, py)
            area = other.available
            if side in ("left", "right"):
                fits = area.y() <= oy - height / 2 and oy + height / 2 <= area.y() + area.height()
                # A taskbar on the target's entering side blocks the seam.
                fits &= area.x() <= ox < area.x() + area.width()
            else:
                fits = area.x() <= ox - width / 2 and ox + width / 2 <= area.x() + area.width()
                fits &= area.y() <= oy < area.y() + area.height()
            if fits:
                return other
        return None

    def bounds(self, display, physics, width, height):
        a = display.available
        edges = [a.x(), a.y(), a.x() + a.width(), a.y() + a.height()]
        for i, side in enumerate(("left", "top", "right", "bottom")):
            if self.neighbor(display, side, physics.x, physics.y, width, height):
                edges[i] = -math.inf if i < 2 else math.inf
        return edges

    def resolve(self, display, physics, width, height):
        """Transfer through native seams, then resolve this monitor's outer edges."""
        position = QPoint(round(physics.x + width / 2), round(physics.y + height / 2))
        current = self.current(display, position)
        if current != display:
            physics.grounded = False
            # Geometry changes/unplugging recover into a valid work area.
            point = clamp_position(QPoint(round(physics.x), round(physics.y)), QSize(width, height), current.available)
            physics.x, physics.y = float(point.x()), float(point.y())
        else:
            nx, ny = display.to_native(physics.x + width / 2, physics.y + height / 2)
            target = next((d for d in self.displays if d.contains_native(nx, ny)), None)
            sides = []
            if nx < display.native[0]:
                sides.append("left")
            if nx >= display.native[2]:
                sides.append("right")
            if ny < display.native[1]:
                sides.append("top")
            if ny >= display.native[3]:
                sides.append("bottom")
            if target is None:
                # An unusually large step can overshoot a small neighboring display.
                target = next((neighbor for side in sides if
                               (neighbor := self.neighbor(display, side, physics.x, physics.y, width, height))), None)
            if target is not None and target.name != display.name:
                if any(self.neighbor(display, side, physics.x, physics.y, width, height) == target for side in sides):
                    cx, cy = target.from_native(nx, ny)
                    physics.x, physics.y = cx - width / 2, cy - height / 2
                    sx, sy = display.scale
                    tx, ty = target.scale
                    physics.vx = max(-physics.max_throw_speed, min(physics.max_throw_speed, physics.vx * sx / tx))
                    physics.vy = max(-physics.max_throw_speed, min(physics.max_fall_speed, physics.vy * sy / ty))
                    physics.grounded = False
                    current = target
        physics.resolve_collisions(*self.bounds(current, physics, width, height), width, height)
        return current


def available_area(position: QPoint | None = None) -> QRect:
    screen = QGuiApplication.screenAt(position) if position is not None else None
    screen = screen or QGuiApplication.primaryScreen()
    if screen is None:
        raise RuntimeError("No desktop screen is available")
    return screen.availableGeometry()


def clamp_position(position: QPoint, size: QSize, area: QRect) -> QPoint:
    # QRect.right()/bottom() are inclusive; width/height avoid an off-by-one.
    max_x = max(area.x(), area.x() + area.width() - size.width())
    max_y = max(area.y(), area.y() + area.height() - size.height())
    return QPoint(min(max(position.x(), area.x()), max_x),
                  min(max(position.y(), area.y()), max_y))


def initial_position(size: QSize, area: QRect, mode: str | None = None,
                     spawn_height: int = 220) -> QPoint:
    right = max(area.x(), area.x() + area.width() - size.width())
    floor = max(area.y(), area.y() + area.height() - size.height())
    center_x = (area.x() + right) // 2
    if mode == "random":
        position = QPoint(random.randint(area.x(), right), random.randint(area.y(), floor))
    elif mode == "bottom_left":
        position = QPoint(area.x() + 24, floor)
    elif mode == "bottom_right":
        position = QPoint(right - 24, floor)
    elif mode == "center":
        position = QPoint(center_x, (area.y() + floor) // 2)
    elif mode is None:
        position = QPoint(center_x, floor - spawn_height)
    else:
        raise ValueError(f"Unknown start position: {mode}")
    return clamp_position(position, size, area)
