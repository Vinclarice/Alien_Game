"""Lightweight particle effects: alien/ship explosions, muzzle flashes,
and the ship's engine trail.

Particles are plain objects, not arcade.Sprites -- they're small,
numerous, and need per-particle alpha fading/shrinking, so they draw
themselves directly with arcade's primitive draw calls each frame
rather than going through a texture/SpriteList. ParticleSystem is the
single object AlienInvasion talks to; everywhere else in the game just
calls one of its spawn_* methods.

Arcade's coordinate system has y increasing upward, the opposite of
pygame's y-down -- "up" here means positive dy, so the muzzle flash's
spread angle is centered on +90 degrees (math convention) instead of
pygame's -90, and the engine trail (which should still visibly drift
away from the ship, off the bottom of the screen) uses negative dy.
"""

import math
import random

import arcade


class Particle:
    """A single short-lived dot: flies along a velocity vector, shrinks
    and fades over its lifespan, then removes itself from its system."""

    def __init__(self, x, y, dx, dy, color, radius, lifespan,
            gravity=0.0, fade=True, shrink=True):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.gravity = gravity
        self.color = color
        self.start_radius = radius
        self.radius = radius
        self.lifespan = lifespan  # in the same "frames at 60fps" units as dt
        self.age = 0.0
        self.fade = fade
        self.shrink = shrink

    @property
    def _alive_fraction(self):
        """0.0 when just spawned, 1.0 right before it dies."""
        return min(1.0, self.age / self.lifespan)

    @property
    def dead(self):
        return self.age >= self.lifespan

    def update(self, dt=1.0):
        self.age += dt
        if self.dead:
            return

        # Gravity pulls toward the bottom of the screen, i.e. decreasing
        # y in arcade's y-up world -- the opposite sign from pygame.
        self.dy -= self.gravity * dt
        self.x += self.dx * dt
        self.y += self.dy * dt

        if self.shrink:
            self.radius = max(0.5,
                self.start_radius * (1 - self._alive_fraction))

    def draw(self):
        """Draw this particle as a soft, alpha-faded circle."""
        if self.radius < 0.5:
            return
        alpha = int(255 * (1 - self._alive_fraction)) if self.fade else 255
        arcade.draw_circle_filled(self.x, self.y, self.radius,
            (*self.color, max(0, alpha)))


class ParticleSystem:
    """Owns and updates every particle effect in the game. Kept separate
    from AlienInvasion so triggering an effect from wherever it happens
    (a collision, a keypress) is a single, self-contained call."""

    def __init__(self):
        self.particles = []

    def update(self, dt=1.0):
        for particle in self.particles:
            particle.update(dt)
        self.particles = [p for p in self.particles if not p.dead]

    def draw(self):
        for particle in self.particles:
            particle.draw()

    def spawn_explosion(self, x, y, color, count=32, speed_range=(1.5, 6.0),
            lifespan_range=(20, 45), radius_range=(2, 6)):
        """A burst flying outward in every direction -- alien/ship kills."""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(*speed_range)
            self.particles.append(Particle(
                x, y,
                dx=math.cos(angle) * speed, dy=math.sin(angle) * speed,
                color=color, radius=random.uniform(*radius_range),
                lifespan=random.uniform(*lifespan_range),
            ))

    def spawn_muzzle_flash(self, x, y, color, count=12):
        """A tight, fast, short-lived burst at the gun's tip -- one shot."""
        for _ in range(count):
            # Spread narrowly around "straight up" (90 degrees in
            # arcade's y-up world).
            angle = math.pi / 2 + random.uniform(-math.pi / 5, math.pi / 5)
            speed = random.uniform(2.0, 5.0)
            self.particles.append(Particle(
                x, y,
                dx=math.cos(angle) * speed, dy=math.sin(angle) * speed,
                color=color, radius=random.uniform(2, 4),
                lifespan=random.uniform(6, 10),
            ))

    def spawn_engine_trail(self, x, y, color, count=3):
        """A few soft puffs of exhaust; called every frame the ship is
        active so the puffs accumulate into a dense, continuous trail."""
        for _ in range(count):
            self.particles.append(Particle(
                x + random.uniform(-3, 3), y,
                dx=random.uniform(-0.5, 0.5), dy=random.uniform(-1.4, -0.5),
                color=color, radius=random.uniform(2, 5),
                lifespan=random.uniform(14, 24),
            ))
