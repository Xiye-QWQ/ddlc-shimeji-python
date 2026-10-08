from behaviors.base_behavior import BaseBehavior


class LookAroundBehavior(BaseBehavior):
    state = "look_around"

    def update(self, mascot, dt):
        previous_turn = int(self.elapsed / 0.8)
        done = super().update(mascot, dt)
        if int(self.elapsed / 0.8) != previous_turn:
            mascot.direction *= -1
        return done
