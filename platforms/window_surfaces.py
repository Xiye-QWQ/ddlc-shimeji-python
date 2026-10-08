"""Experimental one-way window tops. No window detection belongs in Physics."""

from dataclasses import dataclass
import time

from platforms.windows import windows


@dataclass(frozen=True)
class WindowSurface:
    handle: int
    display: str
    left: float
    right: float
    top: float
    origin_x: float


class WindowSurfaces:
    def __init__(self, desktop, provider=windows):
        self.desktop = desktop
        self.provider = provider
        self.surfaces = []
        self._next_poll = 0.0

    def refresh(self, force=False):
        now = time.monotonic()
        if not force and now < self._next_poll:
            return
        self._next_poll = now + .2
        surfaces, above = [], []
        for window in self.provider():
            left, top, right, bottom = window.rect
            segments = [(left, right)] if window.eligible else []
            # Covered portions of a top edge cannot support a mascot.
            for al, at, ar, ab in above:
                if at <= top < ab:
                    segments = [(a, b) for l, r in segments
                                for a, b in ((l, min(r, al)), (max(l, ar), r)) if b > a]
            for display in self.desktop.displays:
                a = display.available
                work_left, work_top = display.to_native(a.x(), a.y())
                work_right, work_bottom = display.to_native(a.x() + a.width(), a.y() + a.height())
                if not work_top <= top < work_bottom:
                    continue
                for l, r in segments:
                    l, r = max(l, work_left), min(r, work_right)
                    if r <= l:
                        continue
                    x, y = display.from_native(l, top)
                    end, _ = display.from_native(r, top)
                    origin, _ = display.from_native(left, top)
                    surfaces.append(WindowSurface(window.handle, display.name, x, end, y, origin))
            above.append(window.rect)
        self.surfaces = surfaces

    @staticmethod
    def fits(surface, display, x, width, height):
        return (surface.display == display.name and surface.left <= x
                and x + width <= surface.right and surface.top - height >= display.available.y())

    def follow(self, support, display, physics, width, height):
        """Carry a resting mascot with its window; release missing/covered supports."""
        self.refresh()
        if support is None or physics.vy < 0:
            return None
        for surface in self.surfaces:
            if surface.handle != support.handle or surface.display != display.name:
                continue
            x = physics.x + surface.origin_x - support.origin_x
            if self.fits(surface, display, x, width, height):
                physics.x, physics.y = x, surface.top - height
                physics.grounded = True
                physics.vy = 0.0
                return surface
        physics.grounded = False
        return None

    def land(self, display, physics, previous_bottom, width, height):
        self.refresh()
        if physics.vy < 0:
            return None
        candidates = [s for s in self.surfaces
                      if self.fits(s, display, physics.x, width, height)
                      and previous_bottom <= s.top + .5 and physics.y + height >= s.top]
        if not candidates:
            return None
        surface = min(candidates, key=lambda s: s.top)
        physics.y = surface.top - height
        physics.vy = 0.0
        physics.grounded = True
        return surface
