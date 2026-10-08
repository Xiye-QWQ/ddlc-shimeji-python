from behaviors.base_behavior import BaseBehavior


class HopBehavior(BaseBehavior):
    state = "hop"

    def enter(self, mascot):
        super().enter(mascot)
        mascot.physics.vy = -float(mascot.behaviors.settings.get("hop_speed", 480.0))
        mascot.physics.grounded = False

    def update(self, mascot, dt):
        self.elapsed += dt
        return mascot.grounded
