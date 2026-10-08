"""Discover character data for launcher, context, and tray menus."""

import json
from pathlib import Path


def available_characters(characters_dir: Path) -> dict[str, str]:
    characters = {}
    for folder in sorted(Path(characters_dir).iterdir()):
        path = folder / "config.json"
        if folder.is_dir() and path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            characters[folder.name] = data.get("name", folder.name)
    return characters
