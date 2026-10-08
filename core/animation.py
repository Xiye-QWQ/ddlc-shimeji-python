"""Ordered PNG playback, independent of movement and physics."""

from dataclasses import dataclass
import math
from pathlib import Path
import re

from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap, QTransform


@dataclass
class Animation:
    frames: list[QPixmap]
    fps: float = 8.0
    loop: bool = True
    allow_horizontal: bool = False

    def __post_init__(self):
        if not self.frames or any(frame.isNull() for frame in self.frames):
            raise ValueError("Animation requires valid PNG frames")
        if not math.isfinite(self.fps) or self.fps <= 0:
            raise ValueError("Animation FPS must be finite and positive")


def load_frames(path: Path) -> list[QPixmap]:
    """Natural filename order: 1.png, 2.png, 10.png (also supports 001.png)."""
    path = Path(path)
    paths = [path] if path.is_file() else [p for p in path.glob('*') if p.suffix.lower() == '.png']
    paths.sort(key=lambda p: [int(part) if part.isdigit() else part.lower()
                             for part in re.split(r"(\d+)", p.name)])
    frames = []
    for png in paths:
        frame = QPixmap(str(png))
        if frame.isNull():
            raise ValueError(f"Cannot load PNG frame: {png}")
        frames.append(frame)
    return frames


class AnimationController:
    def __init__(self, animations: dict[str, Animation], initial: str = "idle",
                 playback_speed: float = 1.0, sprite_facing: str = "right"):
        if not math.isfinite(playback_speed) or playback_speed <= 0:
            raise ValueError("Animation playback speed must be finite and positive")
        self.playback_speed = playback_speed
        if sprite_facing not in ("left", "right"):
            raise ValueError("sprite_facing must be 'left' or 'right'")
        self.source_direction = -1 if sprite_facing == "left" else 1
        self._mirrored_frames = {}
        self.animations = animations
        if initial not in animations:
            raise ValueError(f"Missing initial animation: {initial}")
        self.name = initial
        self.frame_index = 0
        self._elapsed = 0.0
        # Stable canvas prevents frames changing the collision footprint.
        frames = [frame for clip in animations.values() for frame in clip.frames]
        self.size = QSize(max(f.width() for f in frames), max(f.height() for f in frames))

    @classmethod
    def from_character(cls, character_dir: Path, config: dict):
        animations = {}
        names = dict.fromkeys(["idle", "fall", *config.get("animations", {})])
        for name in names:
            spec = config.get("animations", {}).get(name, {})
            path = character_dir / spec.get("path", f"sprites/{name}")
            frames = []
            if "frames" in spec:
                for filename in spec["frames"]:
                    frame_path = character_dir / filename
                    if not frame_path.is_file():
                        raise ValueError(f"Missing animation frame: {frame_path}")
                    frames.extend(load_frames(frame_path))
            else:
                frames = load_frames(path)
            if name == "idle" and not frames and config.get("sprite"):
                frames = load_frames(character_dir / config["sprite"])
            if frames:
                animations[name] = Animation(frames, float(spec.get("fps", 8)),
                                              spec.get("loop", True),
                                              bool(spec.get("allow_horizontal", name == "walk")))
        if "idle" not in animations:
            raise ValueError(f"Add PNG frames in {character_dir / 'sprites/idle'} "
                             "or set a valid 'sprite' path in config.json")
        animations.setdefault("fall", animations["idle"])
        return cls(animations, playback_speed=float(config.get("animation_speed", 1.0)),
                   sprite_facing=config.get("sprite_facing", "right"))

    @property
    def current_frame(self) -> QPixmap:
        return self.animations[self.name].frames[self.frame_index]

    def mirror_frame(self, frame: QPixmap) -> QPixmap:
        """Mirror at render time, preserving PNG alpha, dimensions, and source files."""
        key = frame.cacheKey()
        if key not in self._mirrored_frames:
            self._mirrored_frames[key] = frame.transformed(QTransform().scale(-1, 1))
        return self._mirrored_frames[key]

    def oriented_frame(self, direction: int) -> QPixmap:
        frame = self.current_frame
        return frame if direction == self.source_direction else self.mirror_frame(frame)

    def play(self, name: str) -> None:
        if name == self.name:
            return
        if name not in self.animations:
            raise ValueError(f"Unknown animation: {name}")
        if self.animations[name] is not self.animations[self.name]:
            self.frame_index = 0
            self._elapsed = 0.0
        self.name = name

    def update(self, dt: float) -> None:
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("Animation dt must be finite and nonnegative")
        clip = self.animations[self.name]
        self._elapsed += dt * self.playback_speed
        steps = int(self._elapsed * clip.fps + 1e-9)
        self._elapsed = max(0.0, self._elapsed - steps / clip.fps)
        if clip.loop:
            self.frame_index = (self.frame_index + steps) % len(clip.frames)
        else:
            self.frame_index = min(self.frame_index + steps, len(clip.frames) - 1)
