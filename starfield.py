"""Scrolling parallax starfield background for Alien Invasion.

Purely decorative -- stars have no gameplay effect, just depth and a
sense of motion behind everything else. Three layers (far/mid/near) at
different speeds, sizes, and brightness create a cheap parallax effect;
stars drift toward the bottom of the screen (the same direction diving
aliens and the fleet's forward pressure read as) and wrap back to the
top once they scroll off.

Arcade's coordinate system has y increasing upward with (0, 0) at the
bottom-left of the screen, the opposite of pygame's y-down/top-left --
so "drifting down the screen" here means decreasing y, and stars wrap
by jumping back up to y = height once they fall below y = 0.
"""

import math
import random

import arcade

# (star count, speed range, radius range, brightness range) per layer,
# far to near. Slower/dimmer/smaller reads as farther away.
LAYERS = (
    {'count': 90, 'speed': (0.15, 0.4), 'radius': (1, 1), 'brightness': (60, 110)},
    {'count': 50, 'speed': (0.4, 0.9), 'radius': (1, 2), 'brightness': (110, 175)},
    {'count': 22, 'speed': (0.9, 1.7), 'radius': (1, 3), 'brightness': (175, 255)},
)


class Star:
    __slots__ = (
        'x', 'y', 'speed', 'radius', 'base_brightness',
        'twinkle_phase', 'twinkle_rate',
    )

    def __init__(self, x, y, speed, radius, brightness):
        self.x = x
        self.y = y
        self.speed = speed
        self.radius = radius
        self.base_brightness = brightness
        self.twinkle_phase = random.uniform(0, 2 * math.pi)
        self.twinkle_rate = random.uniform(0.02, 0.06)


class Starfield:
    """Owns, updates, and draws every star layer."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.stars = [
            Star(
                x=random.uniform(0, width),
                y=random.uniform(0, height),
                speed=random.uniform(*layer['speed']),
                radius=random.randint(*layer['radius']),
                brightness=random.randint(*layer['brightness']),
            )
            for layer in LAYERS
            for _ in range(layer['count'])
        ]

    def update(self, dt=1.0):
        for star in self.stars:
            star.y -= star.speed * dt
            if star.y < 0:
                star.y += self.height
                star.x = random.uniform(0, self.width)
            star.twinkle_phase += star.twinkle_rate * dt

    def draw(self):
        for star in self.stars:
            twinkle = 0.75 + 0.25 * math.sin(star.twinkle_phase)
            b = max(0, min(255, int(star.base_brightness * twinkle)))
            color = (b, b, b)
            x = min(self.width - 1, max(0, star.x))
            y = min(self.height - 1, max(0, star.y))
            if star.radius <= 1:
                arcade.draw_point(x, y, color, 1.5)
            else:
                arcade.draw_circle_filled(x, y, star.radius, color)
