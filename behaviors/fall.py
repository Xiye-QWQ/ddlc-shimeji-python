from behaviors.base_behavior import BaseBehavior


class FallBehavior(BaseBehavior):
    state = "fall"

    def enter(self, mascot):
        # Falling inherits throw/walk momentum; BaseBehavior.enter stops vx.
        mascot.animation.play("fall")


class LandingBehavior(BaseBehavior):
    """Brief crouch/recovery poses after landing or sitting."""
    state = "landing"
