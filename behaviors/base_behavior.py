from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.mascot import Mascot


class BaseBehavior:
    state = "idle"

    def __init__(self, duration: float | None = None):
        self.duration = duration
        self.elapsed = 0.0

    def enter(self, mascot: "Mascot") -> None:
        mascot.physics.vx = 0.0
        animation = self.state if self.state in mascot.animation.animations else "idle"
        mascot.animation.play(animation)

    def update(self, mascot: "Mascot", dt: float) -> bool:
        """Return True when this timed behavior has completed."""
        self.elapsed += dt
        return self.duration is not None and self.elapsed >= self.duration
