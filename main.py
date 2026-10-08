"""Start the desktop mascot application."""

import json
import argparse
import sys
from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog

from config.settings import load_settings
from core.application import MascotApplication
from ui.launcher import Launcher


def main() -> int:
    root = Path(__file__).resolve().parent
    settings_path = root / "config/settings.json"
    saved = load_settings(settings_path)
    try:
        engine_settings = json.loads(settings_path.read_text(encoding="utf-8"))
        interval = engine_settings.get("update_interval_ms", 16)
        if type(interval) is not int or interval <= 0:
            interval = 16
    except (OSError, ValueError, AttributeError):
        interval = 16
    parser = argparse.ArgumentParser(description="Run a desktop mascot")
    parser.add_argument("--character", default=None,
                        help="Preselect a character folder in the startup menu")
    args = parser.parse_args()
    app = QApplication(sys.argv)
    # Closing the launcher must not quit during the handoff to the mascot window.
    app.setQuitOnLastWindowClosed(False)
    if args.character is not None:
        saved = replace(saved, character=args.character)
    launcher = Launcher(root / "characters", initial_settings=saved)
    if launcher.exec() != QDialog.DialogCode.Accepted:
        return 0
    startup = launcher.settings()
    manager = MascotApplication(app, root, startup, interval)
    manager.save_defaults(startup)
    if manager.spawn() is None and not manager.tray_available:
        manager.shutdown()
        return 1
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
