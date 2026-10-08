from behaviors.walk import WalkBehavior


class CrawlBehavior(WalkBehavior):
    """Slow floor movement using the character's mapped crouched poses."""
    state = "crawl"

    def _set_velocity(self, mascot):
        speed = mascot.behaviors.settings.get("crawl_speed", 25.0)
        mascot.physics.vx = mascot.direction * float(speed)
