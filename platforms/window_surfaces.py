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
    native_rect: tuple[int, int, int, int]
    occluders: tuple[tuple[int, int, int, int], ...]


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
        self._next_poll = now + .05
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
                    if min(r, work_right) <= max(l, work_left):
                        continue
                    # Keep the complete edge: a sprite may straddle an open
                    # monitor seam while its center belongs to this display.
                    x, y = display.from_native(l, top)
                    end, _ = display.from_native(r, top)
                    surfaces.append(WindowSurface(window.handle, display.name, x, end, y,
                                                  window.rect, tuple(above)))
            above.append(window.rect)
        self.surfaces = surfaces

    def fits(self, surface, display, x, width, height):
        area = display.available
        y = surface.top - height
        if not (surface.display == display.name and surface.left <= x
                and x + width <= surface.right and y >= area.y()
                and area.x() <= x + width / 2 < area.x() + area.width()):
            return False
        for outside, side in ((x < area.x(), "left"),
                              (x + width > area.x() + area.width(), "right")):
            if outside and self.desktop.neighbor(display, side, x, y, width, height) is None:
                return False
        left, top = display.to_native(x, y)
        right, bottom = display.to_native(x + width, surface.top)
        # An edge can be exposed while another window covers the sprite above it.
        return not any(left < r and right > l and top < b and bottom > t
                       for l, t, r, b in surface.occluders)

    def follow(self, support, display, physics, width, height):
        """Carry across displays and resizes; release missing or unsafe supports.

        The caller adopts the returned surface's display after coordinates change.
        Resizing preserves the center's fraction across the full window width;
        walking on an unchanged window remains free to leave its edge.
        """
        self.refresh()
        if support is None or physics.vy < 0:
            return None
        center, _ = display.to_native(physics.x + width / 2, physics.y + height)
        old_left, _, old_right, _ = support.native_rect
        fraction = (center - old_left) / (old_right - old_left)
        for surface in self.surfaces:
            if surface.handle != support.handle:
                continue
            target = next((d for d in self.desktop.displays if d.name == surface.display), None)
            if target is None:
                continue
            left, top, right, _ = surface.native_rect
            resized = right - left != old_right - old_left
            native_center = left + fraction * (right - left)
            if resized:
                half_width = width * target.scale[0] / 2
                if right - left < 2 * half_width:
                    continue
                native_center = min(max(native_center, left + half_width), right - half_width)
            x, _ = target.from_native(native_center, top)
            x -= width / 2
            if self.fits(surface, target, x, width, height):
                physics.x, physics.y = x, surface.top - height
                if target != display:
                    physics.vx *= display.scale[0] / target.scale[0]
                    physics.vx = max(-physics.max_throw_speed, min(physics.max_throw_speed, physics.vx))
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
