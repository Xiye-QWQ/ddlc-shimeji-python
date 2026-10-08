"""Instance actions and application controls for the desktop context menu."""

from PySide6.QtWidgets import QApplication, QMenu
from behaviors.controller import ACTIONS


def create_context_menu(parent) -> QMenu:
    menu = QMenu(parent)
    manager = parent.manager
    if manager is not None:
        characters = menu.addMenu("Change character")
        for name, label in manager.characters.items():
            action = characters.addAction(label)
            action.setCheckable(True)
            action.setChecked(name == parent.character_dir.name)
            action.triggered.connect(lambda _checked=False, name=name: manager.change_character(parent, name))
    force = menu.addMenu("Force action")
    for name in ("idle", *ACTIONS):
        if name != "idle" and name not in parent.animation.animations:
            continue
        force.addAction(name.replace("_", " ").title()).triggered.connect(
            lambda _checked=False, name=name: parent.behaviors.force_action(name))
    autonomous = menu.addAction("Autonomous behavior")
    autonomous.setCheckable(True)
    autonomous.triggered.connect(parent.behaviors.set_autonomous)

    def refresh():
        autonomous.setChecked(parent.behaviors.settings.get("autonomous", True))
        force.setEnabled(parent.grounded and not parent.behaviors.dragging)
    menu.aboutToShow.connect(refresh)
    refresh()
    menu.addSeparator()
    if manager is not None:
        menu.addAction("Spawn another mascot").triggered.connect(
            lambda _checked=False: manager.spawn_another(parent))
        menu.addAction("Remove this mascot").triggered.connect(
            lambda _checked=False: manager.remove(parent))
        menu.addAction("Settings…").triggered.connect(lambda _checked=False: manager.open_settings())
    else:
        menu.addAction("Remove this mascot").triggered.connect(parent.close)
    menu.addSeparator()
    quit_action = menu.addAction("Quit")
    quit_action.triggered.connect(QApplication.instance().quit)
    return menu
