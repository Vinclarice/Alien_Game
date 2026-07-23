"""Lightweight particle effects: alien/ship explosions, muzzle flashes,
and the ship's engine trail.

Particles are deliberately not full pygame Sprites managed through the
normal image/rect/Group.draw() pipeline -- they're small, numerous, and
need per-particle alpha fading, so they draw themselves onto the screen
directly rather than going through a spritesheet. ParticleSystem is the
single object AlienInvasion talks to; everywhere else in the game just
calls one of its spawn_* methods.
"""

import math
import random

import pygame
from pygame.sprite import Sprite


class Particle(Sprite):
    """A single short-lived dot: flies along a velocity vector, shrinks
    and fades over its lifespan, then removes itself from any group."""

    def __init__(self, screen, x, y, dx, dy, color, radius, lifespan,
            gravity=0.0, fade=True, shrink=True):
        super().__init__()
        self.screen = screen
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

    def update(self, dt=1.0):
        self.age += dt
        if self.age >= self.lifespan:
            self.kill()
            return

        self.dy += self.gravity * dt
        self.x += self.dx * dt
        self.y += self.dy * dt

        if self.shrink:
            self.radius = max(0.5,
                self.start_radius * (1 - self._alive_fraction))

    def draw(self, surface_cache=None):
        """Blit this particle as a soft, alpha-faded circle.

        surface_cache (from ParticleSystem) reuses pre-rendered circle
        surfaces across particles/frames instead of allocating one and
        re-rasterizing a circle into it every single frame -- at the
        particle counts this game now spawns, that adds up fast.
        """
        if self.radius < 0.5:
            return

        alpha = int(255 * (1 - self._alive_fraction)) if self.fade else 255
        size = max(1, int(self.radius * 2))
        # Quantize size/alpha so near-identical particles share a cache
        # entry -- a couple of alpha levels of difference is invisible
        # frame-to-frame, but keeps the cache from growing unbounded.
        cache_key = (self.color, size, (alpha // 16) * 16)

        surface = surface_cache.get(cache_key) if surface_cache else None
        if surface is None:
            surface = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(surface, (*self.color, cache_key[2]),
                (size // 2, size // 2), max(1, size // 2))
            if surface_cache is not None:
                surface_cache[cache_key] = surface

        rect = surface.get_rect(center=(self.x, self.y))
        self.screen.blit(surface, rect)


class ParticleSystem:
    """Owns and updates every particle effect in the game. Kept separate
    from AlienInvasion so triggering an effect from wherever it happens
    (a collision, a keypress) is a single, self-contained call."""

    def __init__(self, screen):
        self.screen = screen
        self.group = pygame.sprite.Group()
        # Shared cache of pre-rendered circle surfaces, keyed by
        # (color, size, quantized alpha) -- see Particle.draw().
        self._surface_cache = {}

    def update(self, dt=1.0):
        self.group.update(dt)

    def draw(self):
        for particle in self.group:
            particle.draw(self._surface_cache)

    def spawn_explosion(self, x, y, color, count=32, speed_range=(1.5, 6.0),
            lifespan_range=(20, 45), radius_range=(2, 6)):
        """A burst flying outward in every direction -- alien/ship kills."""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(*speed_range)
            particle = Particle(
                self.screen, x, y,
                dx=math.cos(angle) * speed, dy=math.sin(angle) * speed,
                color=color, radius=random.uniform(*radius_range),
                lifespan=random.uniform(*lifespan_range),
            )
            self.group.add(particle)

    def spawn_muzzle_flash(self, x, y, color, count=12):
        """A tight, fast, short-lived burst at the gun's tip -- one shot."""
        for _ in range(count):
            # Spread narrowly around "straight up" (-90 degrees).
            angle = -math.pi / 2 + random.uniform(-math.pi / 5, math.pi / 5)
            speed = random.uniform(2.0, 5.0)
            particle = Particle(
                self.screen, x, y,
                dx=math.cos(angle) * speed, dy=math.sin(angle) * speed,
                color=color, radius=random.uniform(2, 4),
                lifespan=random.uniform(6, 10),
            )
            self.group.add(particle)

    def spawn_engine_trail(self, x, y, color, count=3):
        """A few soft puffs of exhaust; called every frame the ship is
        active so the puffs accumulate into a dense, continuous trail."""
        for _ in range(count):
            particle = Particle(
                self.screen, x + random.uniform(-3, 3), y,
                dx=random.uniform(-0.5, 0.5), dy=random.uniform(0.5, 1.4),
                color=color, radius=random.uniform(2, 5),
                lifespan=random.uniform(14, 24),
            )
            self.group.add(particle)
