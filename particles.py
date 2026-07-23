"""Particle effects: alien/ship explosions, muzzle flashes, and the
ship's engine trail.

Each particle is a real arcade.Sprite drawn from a small, shared,
soft-edged radial-gradient texture (built once with PIL, the same way
alien.py builds its tinted alien textures) rather than a flat
arcade.draw_circle_filled disc. Tinting a white gradient with
sprite.color gives each particle its color while keeping the soft
glow falloff; sprite.alpha handles the fade-out. Routing every
particle through one shared SpriteList also means the GPU batches the
whole burst into one draw call instead of one draw_circle_filled call
per particle per frame.

ParticleSystem is still the single object AlienInvasion talks to --
everywhere else in the game just calls one of its spawn_* methods.

Arcade's coordinate system has y increasing upward, the opposite of
pygame's y-down -- "up" here means positive dy, so the muzzle flash's
spread angle is centered on +90 degrees (math convention) instead of
pygame's -90, and the engine trail (which should still visibly drift
away from the ship, off the bottom of the screen) uses negative dy.
"""

import math
import random

import arcade
from PIL import Image

GLOW_TEXTURE_SIZE = 64

# Cached lazily -- building the texture needs an active arcade window/
# GL context, which doesn't exist yet at import time.
_glow_texture = None


def _get_glow_texture():
    """A soft white radial gradient, fully opaque at the center and
    fading to transparent at the edge. Tinted per-particle via
    sprite.color, so one texture serves every color in the game."""
    global _glow_texture
    if _glow_texture is not None:
        return _glow_texture

    size = GLOW_TEXTURE_SIZE
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    pixels = image.load()
    center = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            dist = math.hypot(x - center, y - center) / center
            if dist >= 1.0:
                alpha = 0
            else:
                # Squared falloff reads as a soft glow with a brighter
                # core, rather than a linear (flatter-looking) fade.
                alpha = int(255 * (1 - dist) ** 2)
            pixels[x, y] = (255, 255, 255, alpha)

    _glow_texture = arcade.Texture(image)
    return _glow_texture


class GlowParticle(arcade.Sprite):
    """A single short-lived glow sprite: flies along a velocity vector,
    shrinks and fades over its lifespan, then removes itself from
    whatever SpriteList it's in."""

    def __init__(self, x, y, dx, dy, color, radius, lifespan,
            gravity=0.0, fade=True, shrink=True):
        # scale is relative to the shared texture's native size, so a
        # scale of 1.0 fills the full GLOW_TEXTURE_SIZE box -- convert
        # the requested radius (matching the old draw_circle_filled
        # radius semantics) into that scale. Sprite.scale always reads
        # back as an (x, y) tuple even when set from a single float, so
        # the scalar we computed is kept separately rather than read
        # back from self.scale.
        scale = (radius * 2) / GLOW_TEXTURE_SIZE
        super().__init__(_get_glow_texture(),
            scale=scale, center_x=x, center_y=y)
        self.color = color
        self.dx = dx
        self.dy = dy
        self.gravity = gravity
        self.start_scale = scale
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

    def update_particle(self, dt=1.0):
        """Advance one tick. Named distinctly from arcade.Sprite's own
        update() so ParticleSystem's manual tick loop can't collide
        with any base-class update signature."""
        self.age += dt
        if self.dead:
            return

        # Gravity pulls toward the bottom of the screen, i.e. decreasing
        # y in arcade's y-up world -- the opposite sign from pygame.
        self.dy -= self.gravity * dt
        self.center_x += self.dx * dt
        self.center_y += self.dy * dt

        if self.shrink:
            self.scale = self.start_scale * max(0.02, 1 - self._alive_fraction)
        if self.fade:
            self.alpha = int(255 * (1 - self._alive_fraction))


class ParticleSystem:
    """Owns and updates every particle effect in the game. Kept separate
    from AlienInvasion so triggering an effect from wherever it happens
    (a collision, a keypress) is a single, self-contained call."""

    def __init__(self):
        self.sprite_list = arcade.SpriteList()

    def update(self, dt=1.0):
        for particle in self.sprite_list:
            particle.update_particle(dt)

        dead = [p for p in self.sprite_list if p.dead]
        for particle in dead:
            particle.remove_from_sprite_lists()

    def draw(self):
        self.sprite_list.draw()

    def spawn_explosion(self, x, y, color, count=32, speed_range=(1.5, 6.0),
            lifespan_range=(20, 45), radius_range=(2, 6)):
        """A burst flying outward in every direction -- alien/ship kills."""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(*speed_range)
            self.sprite_list.append(GlowParticle(
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
            self.sprite_list.append(GlowParticle(
                x, y,
                dx=math.cos(angle) * speed, dy=math.sin(angle) * speed,
                color=color, radius=random.uniform(2, 4),
                lifespan=random.uniform(6, 10),
            ))

    def spawn_engine_trail(self, x, y, color, count=3):
        """A few soft puffs of exhaust; called every frame the ship is
        active so the puffs accumulate into a dense, continuous trail."""
        for _ in range(count):
            self.sprite_list.append(GlowParticle(
                x + random.uniform(-3, 3), y,
                dx=random.uniform(-0.5, 0.5), dy=random.uniform(-1.4, -0.5),
                color=color, radius=random.uniform(2, 5),
                lifespan=random.uniform(14, 24),
            ))
