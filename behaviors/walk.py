from behaviors.base_behavior import BaseBehavior


class WalkBehavior(BaseBehavior):
    state = "walk"

    def enter(self, mascot):
        super().enter(mascot)
        mascot.direction = mascot.behaviors.random.choice((-1, 1))
        self._set_velocity(mascot)

    def _set_velocity(self, mascot):
        speed = mascot.behaviors.settings.get("walk_speed", 65.0)
        mascot.physics.vx = mascot.direction * float(speed)

    def update(self, mascot, dt):
        left, right = mascot.horizontal_bounds()
        if (mascot.physics.x <= left and mascot.direction < 0
                or mascot.physics.x >= right and mascot.direction > 0):
            mascot.direction *= -1
        self._set_velocity(mascot)
        return super().update(mascot, dt)
