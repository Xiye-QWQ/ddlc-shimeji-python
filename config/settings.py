"""Simple editable saved defaults and their runtime engine mappings."""

from copy import deepcopy
from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path


ACTION_DURATION = {"slow": 1.7, "normal": 1.0, "fast": 0.6}
ANIMATION_SPEED = {"slow": 0.7, "normal": 1.0, "fast": 1.5}
PHYSICS_PRESETS = {
    "light": dict(gravity=1800, max_fall_speed=1400, throw_strength=1.0,
                  max_throw_speed=1600, air_drag=0.35, ground_friction=8.0),
    "normal": dict(gravity=2400, max_fall_speed=1300, throw_strength=0.85,
                   max_throw_speed=1250, air_drag=0.65, ground_friction=12.0),
    "heavy": dict(gravity=3000, max_fall_speed=1400, throw_strength=0.7,
                  max_throw_speed=1000, air_drag=0.9, ground_friction=16.0),
}


@dataclass(frozen=True)
class StartupSettings:
    character: str = "monika"
    action_speed: str = "normal"
    starting_behavior: str = "random"
    throwing: bool = True
    physics_feel: str = "normal"
    always_on_top: bool = True
    start_position: str = "random"
    animation_speed: str = "normal"
    autonomous: bool = True
    window_interaction: bool = False

    def apply_to(self, character_config: dict) -> dict:
        """Copy character data; only this mascot instance receives the overrides."""
        config = deepcopy(character_config)
        config.setdefault("physics", {}).update(PHYSICS_PRESETS[self.physics_feel])
        behavior = config.setdefault("behaviors", {})
        multiplier = ACTION_DURATION[self.action_speed]
        for name, default in (("idle", (2, 5)), ("walk", (2, 5)), ("sit", (2, 4))):
            key = f"{name}_duration"
            behavior.setdefault(key, default)
        for key, duration in list(behavior.items()):
            if key.endswith("_duration"):
                behavior[key] = [value * multiplier for value in duration]
        behavior["autonomous"] = self.autonomous
        behavior["starting_behavior"] = self.starting_behavior
        config["throwing"] = self.throwing
        config["always_on_top"] = self.always_on_top
        config["start_position"] = self.start_position
        config["animation_speed"] = ANIMATION_SPEED[self.animation_speed]
        config["window_interaction"] = self.window_interaction
        return config


def load_settings(path: Path) -> StartupSettings:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    defaults = StartupSettings()
    allowed = {
        "action_speed": ACTION_DURATION, "animation_speed": ANIMATION_SPEED,
        "physics_feel": PHYSICS_PRESETS,
        "starting_behavior": ("random", "idle", "walk"),
        "start_position": ("random", "bottom_left", "bottom_right", "center"),
    }
    values = {}
    for field in fields(defaults):
        default = getattr(defaults, field.name)
        value = data.get(field.name, default)
        valid = type(value) is type(default)
        if field.name in allowed:
            valid = valid and value in allowed[field.name]
        if field.name == "character":
            valid = valid and bool(value) and Path(value).name == value and value not in (".", "..")
        values[field.name] = value if valid else default
    return StartupSettings(**values)


def save_settings(path: Path, settings: StartupSettings) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.update(asdict(settings))
    data.setdefault("update_interval_ms", 16)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
