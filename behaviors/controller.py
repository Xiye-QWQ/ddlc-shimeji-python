"""Shared autonomous loop; choices depend on each character's available art."""

import random

from behaviors.drag import DragBehavior
from behaviors.fall import FallBehavior, LandingBehavior
from behaviors.idle import IdleBehavior
from behaviors.sit import SitBehavior
from behaviors.walk import WalkBehavior
from behaviors.crawl import CrawlBehavior
from behaviors.hop import HopBehavior
from behaviors.look_around import LookAroundBehavior
from behaviors.sleep import SleepBehavior


# class, default duration range, selection weight, cooldown seconds
ACTIONS = {
    "walk": (WalkBehavior, (2, 5), 5, 4),
    "sit": (SitBehavior, (3, 6), 3, 10),
    "sleep": (SleepBehavior, (8, 14), 1, 35),
    "crawl": (CrawlBehavior, (2, 4), 2, 12),
    "hop": (HopBehavior, (0, 0), 2, 10),
    "look_around": (LookAroundBehavior, (3, 5), 3, 8),
}


class BehaviorController:
    def __init__(self, mascot, settings: dict):
        self.mascot = mascot
        self.settings = settings
        self.random = random.Random()
        self.current = None
        self._starting = True
        self._time = 0.0
        self._cooldowns = {}
        self._last_action = None
        self._forced = False

    def duration(self, name, default):
        low, high = self.settings.get(f"{name}_duration", default)
        return self.random.uniform(float(low), float(high))

    def set(self, behavior):
        if self.current is not None and self.current.state in ACTIONS:
            name = self.current.state
            cooldown = self.settings.get("cooldowns", {}).get(name, ACTIONS[name][3])
            self._cooldowns[name] = self._time + max(0.0, float(cooldown))
        self.current = behavior
        if behavior.state in ACTIONS:
            self._last_action = behavior.state
        behavior.enter(self.mascot)

    def choose_action(self):
        weights = self.settings.get("choices", {})
        choices = [name for name, spec in ACTIONS.items()
                   if name in self.mascot.animation.animations
                   and weights.get(name, spec[2]) > 0
                   and self._cooldowns.get(name, 0) <= self._time]
        # Avoid consecutive repeats when another eligible action exists.
        alternatives = [name for name in choices if name != self._last_action]
        choices = alternatives or choices
        return self.random.choices(choices, [weights.get(name, ACTIONS[name][2]) for name in choices])[0] if choices else None

    def start_action(self, name):
        cls, duration, _, _ = ACTIONS[name]
        self.set(cls(self.duration(name, duration)))

    def force_action(self, name):
        valid = name == "idle" or name in ACTIONS and name in self.mascot.animation.animations
        if not valid or self.dragging or not self.mascot.grounded:
            return
        self._starting = False
        self._forced = True
        if name == "idle":
            self.idle()
        elif name in ACTIONS and name in self.mascot.animation.animations:
            self.start_action(name)

    def set_autonomous(self, enabled):
        self.settings["autonomous"] = bool(enabled)
        self._starting = self._forced = False
        if not self.dragging:
            if self.mascot.grounded:
                self.idle()
            else:
                self.set(FallBehavior())

    @property
    def dragging(self):
        return isinstance(self.current, DragBehavior)

    def idle(self):
        self.set(IdleBehavior(self.duration("idle", (2.0, 5.0))))

    def begin(self):
        """Use the selected starting behavior once, after the initial fall if needed."""
        self._starting = False
        choice = self.settings.get("starting_behavior", "idle")
        if not self.settings.get("autonomous", True):
            choice = "idle"
        if choice == "random":
            choice = self.choose_action()
        if choice in ACTIONS and choice in self.mascot.animation.animations:
            self.start_action(choice)
        else:
            self.idle()

    def settle(self):
        if self._starting:
            self.begin()
        else:
            self.idle()

    def recover(self):
        if "landing" in self.mascot.animation.animations:
            clip = self.mascot.animation.animations["landing"]
            self.set(LandingBehavior(len(clip.frames) / (clip.fps * self.mascot.animation.playback_speed)))
        else:
            self.idle()

    def release(self):
        self._starting = False
        self._forced = False
        self.set(FallBehavior())

    def update(self, dt):
        self._time += dt
        if self.dragging:
            return
        if not self.mascot.grounded:
            if isinstance(self.current, HopBehavior):
                self.current.update(self.mascot, dt)
                return
            if not isinstance(self.current, FallBehavior):
                self.set(FallBehavior())
            return
        if isinstance(self.current, FallBehavior):
            if self.mascot.physics.settled:
                self.settle()
            return
        if not self.settings.get("autonomous", True) and not self._forced:
            return
        if self.current.update(self.mascot, dt):
            if self._forced:
                self._forced = False
                self.idle()
                return
            if isinstance(self.current, IdleBehavior):
                selected = self.choose_action()
                if selected is None:
                    self.idle()
                    return
                self.start_action(selected)
            elif isinstance(self.current, (SitBehavior, HopBehavior)):
                self.recover()
            else:
                self.idle()
