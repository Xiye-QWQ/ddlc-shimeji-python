"""Desktop character coordinating animation, physics, and interaction."""

import json
import random
import time
from collections import deque
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QTimer, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from core.animation import AnimationController
from core.physics import Physics
from core.screen import DesktopLayout, clamp_position, initial_position
from platforms.window_surfaces import WindowSurfaces
from config.settings import StartupSettings
from ui.context_menu import create_context_menu
from behaviors.controller import BehaviorController
from behaviors.drag import DragBehavior
from behaviors.fall import FallBehavior


class Mascot(QWidget):
    closed = Signal(object)

    def __init__(self, character_dir: Path, update_interval_ms: int = 16,
                 startup_settings: StartupSettings | None = None, manager=None):
        super().__init__()
        if not isinstance(update_interval_ms, int) or update_interval_ms <= 0:
            raise ValueError("Update interval must be a positive integer")
        character_dir = Path(character_dir)
        self.character_dir = character_dir
        self.startup_settings = startup_settings or StartupSettings(character=character_dir.name)
        self.manager = manager
        self.desktop = manager.desktop if manager else DesktopLayout(self)
        self.window_surfaces = manager.window_surfaces if manager else WindowSurfaces(self.desktop)
        self.support = None
        config = json.loads((character_dir / "config.json").read_text(encoding="utf-8"))
        if startup_settings is not None:
            config = startup_settings.apply_to(config)
        self.throwing_enabled = config.get("throwing", True)
        self.window_interaction = config.get("window_interaction", False)
        self.setWindowTitle(config.get("name", character_dir.name))
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if config.get("always_on_top", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.animation = AnimationController.from_character(character_dir, config)
        self.setFixedSize(self.animation.size)
        self.sprite_label = QLabel(self)
        self.sprite_label.setPixmap(self.animation.current_frame)
        self.sprite_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        self.sprite_label.setGeometry(self.rect())
        # Let the parent receive dragging events anywhere over the label.
        self.sprite_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.sprite_label.setStyleSheet("background: transparent;")
        self.direction = 1
        primary = self.desktop.at(QApplication.primaryScreen().geometry().center())
        self.display = random.choice(self.desktop.displays) if config.get("start_position") == "random" else primary
        self.screen_area = self.display.available
        self.move(initial_position(self.size(), self.screen_area, config.get("start_position"),
                                   int(config.get("spawn_height", 220))))
        physics_config = config.get("physics", {})
        self.physics = Physics(float(self.x()), float(self.y()),
                               gravity=float(physics_config.get("gravity", Physics.gravity)),
                               max_fall_speed=float(physics_config.get("max_fall_speed", Physics.max_fall_speed)),
                               throw_strength=float(physics_config.get("throw_strength", Physics.throw_strength)),
                               max_throw_speed=float(physics_config.get("max_throw_speed", Physics.max_throw_speed)),
                               air_drag=float(physics_config.get("air_drag", Physics.air_drag)),
                               ground_friction=float(physics_config.get("ground_friction", Physics.ground_friction)))
        self._mouse_history = deque(maxlen=64)
        self._velocity_window = 0.12
        self.resolve_collisions()
        self.behaviors = BehaviorController(self, config.get("behaviors", {}))
        if self.grounded:
            self.behaviors.begin()
        else:
            self.behaviors.set(FallBehavior())
        self.render_frame()
        self.context_menu = create_context_menu(self)
        self._last_update = time.monotonic()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(update_interval_ms)
        QApplication.instance().aboutToQuit.connect(self.timer.stop)

    @property
    def position(self) -> QPointF:
        return QPointF(self.physics.x, self.physics.y)

    @property
    def grounded(self) -> bool:
        return self.physics.grounded

    @property
    def current_behavior(self):
        return self.behaviors.current

    @property
    def state(self) -> str:
        return self.current_behavior.state

    def sync_motion_animation(self, horizontal_motion: float) -> None:
        """Only clips explicitly mapped for horizontal movement may display while moving."""
        if self.behaviors.dragging:
            return
        target = self.state if self.state in self.animation.animations else "idle"
        if abs(horizontal_motion) > 0.001:
            if not self.animation.animations[target].allow_horizontal:
                walk = self.animation.animations.get("walk")
                if walk is not None and walk.allow_horizontal:
                    target = "walk"
                else:
                    self.physics.vx = 0.0
        self.animation.play(target)

    def render_frame(self, horizontal_motion: float | None = None) -> None:
        motion = self.physics.vx if horizontal_motion is None else horizontal_motion
        self.sync_motion_animation(motion)
        self.face_motion(motion)
        self.sprite_label.setPixmap(self.animation.oriented_frame(self.direction))

    def face_motion(self, horizontal_motion: float) -> None:
        """Moving characters face their motion; stationary poses retain their direction."""
        if abs(horizontal_motion) > 0.001:
            self.direction = 1 if horizontal_motion > 0 else -1

    def resolve_collisions(self) -> None:
        previous = self.display
        self.display = self.desktop.resolve(self.display, self.physics, self.width(), self.height())
        self.screen_area = self.display.available
        if self.display != previous and previous not in self.desktop.displays:
            self.support = None

    def horizontal_bounds(self):
        left, _, right, _ = self.desktop.bounds(self.display, self.physics, self.width(), self.height())
        return left, right - self.width()

    def update_support(self):
        if self.support is not None:
            self.support = self.window_surfaces.follow(self.support, self.display, self.physics,
                                                       self.width(), self.height())
            if self.support is not None:
                self.display = next(d for d in self.desktop.displays if d.name == self.support.display)
                self.screen_area = self.display.available

    def tick(self) -> None:
        now = time.monotonic()
        # Cap stalled event-loop steps so debugger pauses cannot teleport us.
        dt = min(max(now - self._last_update, 0.0), 0.1)
        self._last_update = now
        old_native_x, _ = self.display.to_native(self.physics.x + self.width() / 2, self.physics.y)
        if not self.behaviors.dragging:
            # Revalidate changed/unplugged screens without cancelling an upward
            # throw at the floor before its first integration step.
            if self.desktop.current(self.display, self.frameGeometry().center()) != self.display:
                self.resolve_collisions()
            self.update_support()
        self.behaviors.update(dt)
        self.sync_motion_animation(self.physics.vx)
        self.animation.update(dt)
        horizontal_motion = 0.0
        if not self.behaviors.dragging:
            previous_foot = self.display.to_native(self.physics.x + self.width() / 2,
                                                   self.physics.y + self.height())
            # Hop/throw immediately detaches from a window platform.
            if self.physics.vy < 0:
                self.support = None
            self.physics.update(dt)
            self.resolve_collisions()
            self.update_support()
            if self.window_interaction and self.support is None:
                _, previous_bottom = self.display.from_native(*previous_foot)
                self.support = self.window_surfaces.land(self.display, self.physics, previous_bottom,
                                                        self.width(), self.height())
            native_x, _ = self.display.to_native(self.physics.x + self.width() / 2, self.physics.y)
            # Physical displacement also covers window carries across DPI seams.
            horizontal_motion = native_x - old_native_x
            self.move(round(self.physics.x), round(self.physics.y))
            # Keep throw momentum through landing; return to idle after friction settles it.
            if self.physics.settled and isinstance(self.current_behavior, FallBehavior):
                self.behaviors.settle()
        # A zero-length timer step must not flicker back to a stationary clip.
        self.render_frame(horizontal_motion if abs(horizontal_motion) > 0.001 else None)

    def record_mouse(self, cursor: QPoint, timestamp: float) -> None:
        display = self.desktop.at(cursor)
        x, y = display.to_native(cursor.x(), cursor.y())
        self._mouse_history.append((timestamp, x, y))
        while self._mouse_history and self._mouse_history[0][0] < timestamp - self._velocity_window:
            self._mouse_history.popleft()

    def release_velocity(self) -> tuple[float, float]:
        """Fit recent cursor motion over time, reducing single-event jitter."""
        samples = list(self._mouse_history)
        if len(samples) < 2 or samples[-1][0] - samples[0][0] < 0.01:
            return 0.0, 0.0
        times = [sample[0] - samples[-1][0] for sample in samples]
        mean_time = sum(times) / len(times)
        offsets = [t - mean_time for t in times]
        denominator = sum(t * t for t in offsets)
        return tuple(sum(t * sample[axis] for t, sample in zip(offsets, samples)) / denominator / scale
                     for axis, scale in zip((1, 2), self.display.scale))

    def drag_to(self, cursor: QPoint) -> None:
        """Keep mouse positioning here; behavior objects only select drag state."""
        self.display = self.desktop.at(cursor)
        self.screen_area = self.display.available
        position = clamp_position(cursor - self.current_behavior.offset, self.size(), self.screen_area)
        self.face_motion(position.x() - self.physics.x)
        self.physics.x, self.physics.y = float(position.x()), float(position.y())
        self.physics.vx = self.physics.vy = 0.0
        self.resolve_collisions()
        self.move(position)
        self.render_frame()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.support = None
            cursor = event.globalPosition().toPoint()
            self._mouse_history.clear()
            self.record_mouse(cursor, time.monotonic())
            self.behaviors.set(DragBehavior(cursor - self.pos()))
            self.render_frame()
            self.activateWindow()
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.behaviors.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            cursor = event.globalPosition().toPoint()
            self.record_mouse(cursor, time.monotonic())
            self.drag_to(cursor)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.behaviors.dragging:
            cursor = event.globalPosition().toPoint()
            now = time.monotonic()
            self.record_mouse(cursor, now)
            self.drag_to(cursor)
            self.resolve_collisions()
            self._last_update = now
            velocity = self.release_velocity() if self.throwing_enabled else (0.0, 0.0)
            self.physics.throw(*velocity)
            self._mouse_history.clear()
            self.face_motion(self.physics.vx)
            self.behaviors.release()
            self.render_frame()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            QApplication.instance().quit()
            event.accept()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event) -> None:
        self.context_menu.popup(event.globalPos())
        event.accept()

    def closeEvent(self, event) -> None:
        self.timer.stop()
        super().closeEvent(event)
        if event.isAccepted():
            self.closed.emit(self)

    def pause(self) -> None:
        if self.behaviors.dragging:
            self.behaviors.release()
        self._mouse_history.clear()
        self.timer.stop()
        self.hide()

    def resume(self) -> None:
        self._last_update = time.monotonic()
        self.show()
        self.timer.start()
