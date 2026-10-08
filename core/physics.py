"""Desktop motion and collisions; independent of Qt and sprites."""

from dataclasses import dataclass
import math


@dataclass
class Physics:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    gravity: float = 2400.0
    max_fall_speed: float = 1300.0
    grounded: bool = False
    throw_strength: float = 0.85
    max_throw_speed: float = 1250.0
    air_drag: float = 0.65
    ground_friction: float = 12.0
    settle_speed: float = 8.0

    def __post_init__(self):
        if not math.isfinite(self.gravity) or self.gravity < 0:
            raise ValueError("Gravity must be finite and nonnegative")
        if not math.isfinite(self.max_fall_speed) or self.max_fall_speed <= 0:
            raise ValueError("Maximum fall speed must be finite and positive")
        for name in ("throw_strength", "air_drag", "ground_friction"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        for name in ("max_throw_speed", "settle_speed"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")

    @property
    def settled(self) -> bool:
        return self.grounded and abs(self.vx) <= self.settle_speed and self.vy == 0

    def throw(self, vx: float, vy: float) -> None:
        """Accept sampled cursor velocity in pixels/second; cap vector magnitude."""
        if not math.isfinite(vx) or not math.isfinite(vy):
            raise ValueError("Throw velocity must be finite")
        self.vx, self.vy = vx * self.throw_strength, vy * self.throw_strength
        speed = math.hypot(self.vx, self.vy)
        if speed > self.max_throw_speed:
            scale = self.max_throw_speed / speed
            self.vx *= scale
            self.vy *= scale
        if self.vy < 0:
            self.grounded = False

    def update(self, dt: float) -> None:
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("Physics dt must be finite and nonnegative")
        if self.grounded and self.vy >= 0:
            self.vx *= math.exp(-self.ground_friction * dt)
            if abs(self.vx) <= self.settle_speed:
                self.vx = 0.0
            self.vy = 0.0
        else:
            damping = math.exp(-self.air_drag * dt)
            self.vx *= damping
            self.vy = min(self.vy * damping + self.gravity * dt, self.max_fall_speed)
        self.x += self.vx * dt
        self.y += self.vy * dt

    def resolve_collisions(self, left: float, top: float, right: float,
                           bottom: float, width: int, height: int) -> None:
        """Bounds use exclusive right/bottom edges, unlike QRect.right()."""
        max_x = max(left, right - width)
        floor = max(top, bottom - height)
        if self.x < left or self.x > max_x:
            self.x = min(max(self.x, left), max_x)
            self.vx = 0.0
        if self.y < top:
            self.y = top
            self.vy = max(0.0, self.vy)
        self.grounded = self.y >= floor
        if self.grounded:
            self.y = floor
            self.vy = 0.0
