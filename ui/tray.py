"""Windows notification-area controls using Qt's platform tray integration."""

from PySide6.QtWidgets import QMenu, QStyle, QSystemTrayIcon


class MascotTray(QSystemTrayIcon):
    def __init__(self, manager):
        icon = manager.app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        super().__init__(icon, manager)
        self.setToolTip("Desktop Mascots")
        self.menu = QMenu()
        self.settings_action = self.menu.addAction("Settings…")
        self.settings_action.triggered.connect(lambda _checked=False: manager.open_settings())
        spawn = self.menu.addMenu("Spawn mascot")
        spawn.addAction("Use saved settings").triggered.connect(lambda _checked=False: manager.spawn())
        spawn.addSeparator()
        for name, label in manager.characters.items():
            spawn.addAction(label).triggered.connect(lambda _checked=False, name=name: manager.spawn(name))
        self.visibility_action = self.menu.addAction("Hide mascots")
        self.visibility_action.triggered.connect(lambda _checked=False: manager.toggle_visibility())
        self.menu.addSeparator()
        self.quit_action = self.menu.addAction("Quit")
        self.quit_action.triggered.connect(lambda _checked=False: manager.quit())
        self.setContextMenu(self.menu)
        self.activated.connect(lambda reason: manager.open_settings()
                               if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
