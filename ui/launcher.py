"""Compact startup menu and editor for saved defaults."""
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout,
    QLabel, QPushButton, QVBoxLayout,
)

from config.settings import StartupSettings
from config.characters import available_characters


class Launcher(QDialog):
    def __init__(self, characters_dir: Path, default_character: str = "monika",
                 initial_settings: StartupSettings | None = None, editing: bool = False):
        super().__init__()
        self.setWindowTitle("Desktop Mascot")
        self.setFixedWidth(360)
        self.controls = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        title = QLabel("New mascot defaults" if editing else "Choose your mascot")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)
        form = QFormLayout()
        form.setVerticalSpacing(10)
        layout.addLayout(form)

        characters = [(label, name) for name, label in available_characters(characters_dir).items()]

        def combo(key, label, items, default):
            widget = QComboBox()
            for text, value in items:
                widget.addItem(text, value)
            index = widget.findData(default)
            if index >= 0:
                widget.setCurrentIndex(index)
            self.controls[key] = widget
            form.addRow(label, widget)
            return widget

        def checkbox(key, label):
            widget = QCheckBox("Enabled")
            widget.setChecked(True)
            self.controls[key] = widget
            form.addRow(label, widget)
            return widget

        speeds = [("Slow", "slow"), ("Normal", "normal"), ("Fast", "fast")]
        combo("character", "Character", characters, default_character)
        combo("action_speed", "Random action speed", speeds, "normal").setToolTip(
            "Changes how long timed actions last. Hop height is controlled by physics.")
        start_behavior = combo("starting_behavior", "Starting behavior",
                              [("Random", "random"), ("Idle", "idle"), ("Walk", "walk")], "random")
        start_behavior.setToolTip("Airborne mascots fall before beginning this behavior.")
        checkbox("throwing", "Throwing physics").setToolTip(
            "Inherit mouse motion on release. Dragging and gravity remain available when disabled.")
        combo("physics_feel", "Physics feel",
              [("Light", "light"), ("Normal", "normal"), ("Heavy", "heavy")], "normal")
        checkbox("always_on_top", "Always on top")
        combo("start_position", "Start position",
              [("Random", "random"), ("Bottom-left", "bottom_left"),
               ("Bottom-right", "bottom_right"), ("Center", "center")], "random")
        combo("animation_speed", "Animation speed", speeds, "normal")
        autonomous = checkbox("autonomous", "Autonomous behavior")
        autonomous.setToolTip("When disabled, stay idle after landing. You can still drag and throw.")
        autonomous.toggled.connect(start_behavior.setEnabled)
        window_interaction = checkbox("window_interaction", "Window tops (experimental)")
        window_interaction.setChecked(False)
        window_interaction.setToolTip("Windows only: land and walk on visible application window tops.")

        if initial_settings is not None:
            for name, widget in self.controls.items():
                value = getattr(initial_settings, name)
                if isinstance(widget, QCheckBox):
                    widget.setChecked(value)
                else:
                    index = widget.findData(value)
                    if index >= 0:
                        widget.setCurrentIndex(index)
        if editing:
            note = QLabel("Used for new mascots. Existing mascots keep their settings.")
            note.setWordWrap(True)
            layout.addWidget(note)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.quit_button = QPushButton("Cancel" if editing else "Quit")
        self.start_button = QPushButton("Apply" if editing else "Start")
        self.start_button.setDefault(True)
        self.start_button.setEnabled(bool(characters))
        self.quit_button.clicked.connect(self.reject)
        self.start_button.clicked.connect(self.accept)
        buttons.addWidget(self.quit_button)
        buttons.addWidget(self.start_button)
        layout.addLayout(buttons)

    def settings(self) -> StartupSettings:
        values = {name: widget.isChecked() if isinstance(widget, QCheckBox) else widget.currentData()
                  for name, widget in self.controls.items()}
        return StartupSettings(**values)
