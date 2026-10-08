from PySide6.QtCore import QPoint

from behaviors.base_behavior import BaseBehavior


class DragBehavior(BaseBehavior):
    state = "drag"

    def __init__(self, offset: QPoint):
        super().__init__()
        self.offset = offset

    def enter(self, mascot):
        super().enter(mascot)
        mascot.physics.vy = 0.0
