"""Scrolling parallax starfield background for Alien Invasion, plus the
rest of the deep-space dressing: drifting nebula haze, a couple of
distant planets, and the occasional shooting star.

Every layer here is purely decorative -- none of it affects gameplay,
just depth, color, and a sense of scale behind everything else. Drawn
back-to-front: nebula haze, then planets, then the three star layers,
then any live shooting star.

Arcade's coordinate system has y increasing upward with (0, 0) at the
bottom-left of the screen, the opposite of pygame's y-down/top-left --
so "drifting down the screen" here means decreasing y, and anything
that wraps does so by jumping back up to y = height once it drifts
below y = 0 (or the equivalent margin-aware wrap for the much bigger
nebula/planet sprites).
"""

import math
import random

import arcade
from PIL import Image

# ---------------------------------------------------------------------
# Stars: three parallax layers, far to near. Slower/dimmer/smaller
# reads as farther away. The near layer's top brightness (255) is
# bright enough to cross post_fx's bloom threshold on its own, so the
# brightest twinkles occasionally catch a soft bloom flare -- a bit of
# sparkle instead of a flat twinkle in place.
# ---------------------------------------------------------------------

LAYERS = (
    {'count': 150, 'speed': (0.15, 0.4), 'radius': (1, 1), 'brightness': (60, 110)},
    {'count': 90, 'speed': (0.4, 0.9), 'radius': (1, 2), 'brightness': (110, 175)},
    {'count': 40, 'speed': (0.9, 1.7), 'radius': (1, 3), 'brightness': (175, 255)},
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


# ---------------------------------------------------------------------
# Nebula haze: a handful of big, soft, translucent color blobs that
# drift almost imperceptibly slowly behind everything else. Several
# overlapping blobs of different colors/sizes/positions read as an
# organic haze rather than visible flat circles -- no single blob is
# shaped like a "nebula," the overlap is what sells it.
# ---------------------------------------------------------------------

NEBULA_COLORS = (
    (130, 70, 190),   # violet
    (60, 100, 190),   # blue
    (190, 70, 140),   # magenta
    (60, 160, 160),   # teal
)

_nebula_texture = None


def _get_nebula_texture(size=256):
    """A very soft, wide white radial gradient -- far gentler falloff
    than particles.py's glow texture, and low enough peak alpha that
    tinting it and drawing several overlapping copies reads as haze,
    not a light source (kept safely under post_fx's bloom threshold)."""
    global _nebula_texture
    if _nebula_texture is not None:
        return _nebula_texture

    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    pixels = image.load()
    center = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            dist = math.hypot(x - center, y - center) / center
            alpha = 0 if dist >= 1.0 else int(70 * (1 - dist))
            pixels[x, y] = (255, 255, 255, alpha)

    _nebula_texture = arcade.Texture(image)
    return _nebula_texture


class NebulaBlob:
    """One soft haze blob; several together make up the nebula layer."""

    def __init__(self, x, y, color, scale, drift_x, drift_y):
        self.sprite = arcade.Sprite(_get_nebula_texture(), scale=scale,
            center_x=x, center_y=y)
        self.sprite.color = color
        self.drift_x = drift_x
        self.drift_y = drift_y

    def update(self, dt, width, height):
        self.sprite.center_x += self.drift_x * dt
        self.sprite.center_y += self.drift_y * dt

        # Generous margin before wrapping -- these are big enough that
        # popping them back the instant they touch the edge would be
        # visible.
        margin = self.sprite.width / 2
        if self.sprite.center_x < -margin:
            self.sprite.center_x = width + margin
        elif self.sprite.center_x > width + margin:
            self.sprite.center_x = -margin
        if self.sprite.center_y < -margin:
            self.sprite.center_y = height + margin
        elif self.sprite.center_y > height + margin:
            self.sprite.center_y = -margin


# ---------------------------------------------------------------------
# Distant planets: a couple of large, softly-shaded spheres, drifting
# almost imperceptibly slowly. Shading is a cheap fake normal/light
# calc -- brighter facing light_dir, darker toward the rim -- just
# enough falloff to read as a lit ball instead of a flat tinted disc.
# ---------------------------------------------------------------------

def _build_planet_texture(diameter, base_color, light_dir=(-0.5, 0.5)):
    image = Image.new('RGBA', (diameter, diameter), (0, 0, 0, 0))
    pixels = image.load()
    center = (diameter - 1) / 2
    light_len = math.hypot(*light_dir) or 1.0
    lx, ly = light_dir[0] / light_len, light_dir[1] / light_len

    for y in range(diameter):
        for x in range(diameter):
            dx = (x - center) / center
            dy = (y - center) / center
            dist = math.hypot(dx, dy)
            if dist >= 1.0:
                continue

            # Fake sphere normal (dx, -dy, nz) dotted with the light
            # direction -- image y grows downward but world y grows
            # upward, hence the flip -- blended with a flat ambient
            # term so the unlit side doesn't go fully black.
            nz = math.sqrt(max(0.0, 1 - dist * dist))
            facing = max(0.0, dx * lx + (-dy) * ly) * 0.6 + nz * 0.4
            shade = 0.35 + 0.65 * facing

            r = min(255, int(base_color[0] * shade))
            g = min(255, int(base_color[1] * shade))
            b = min(255, int(base_color[2] * shade))
            # Anti-alias the outer couple of pixels instead of a hard
            # circular edge.
            edge_fade = min(1.0, (1.0 - dist) * diameter / 3)
            pixels[x, y] = (r, g, b, int(255 * edge_fade))

    return arcade.Texture(image)


class Planet:
    def __init__(self, x, y, diameter, base_color, drift_x, drift_y,
            light_dir=(-0.5, 0.5)):
        texture = _build_planet_texture(diameter, base_color, light_dir)
        self.sprite = arcade.Sprite(texture, center_x=x, center_y=y)
        self.drift_x = drift_x
        self.drift_y = drift_y

    def update(self, dt, width, height):
        self.sprite.center_x += self.drift_x * dt
        self.sprite.center_y += self.drift_y * dt

        margin = self.sprite.width
        if self.sprite.center_x < -margin:
            self.sprite.center_x = width + margin
        elif self.sprite.center_x > width + margin:
            self.sprite.center_x = -margin
        if self.sprite.center_y < -margin:
            self.sprite.center_y = height + margin
        elif self.sprite.center_y > height + margin:
            self.sprite.center_y = -margin


# ---------------------------------------------------------------------
# Shooting stars: rare, fast, bright streaks with a fading trail.
# Bright white, so post_fx's bloom pass gives the streak a genuine
# glowing trail for free.
# ---------------------------------------------------------------------

# Frames between spawns, at 60fps -- roughly every 4 to 11 seconds.
SHOOTING_STAR_INTERVAL = (4.0 * 60, 11.0 * 60)


class ShootingStar:
    def __init__(self, x, y, dx, dy, length, lifespan):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.length = length
        self.age = 0.0
        self.lifespan = lifespan

    @property
    def dead(self):
        return self.age >= self.lifespan

    def update(self, dt):
        self.age += dt
        self.x += self.dx * dt
        self.y += self.dy * dt

    # How many short segments the trail is built from -- more reads as
    # a smoother taper, at the cost of a few extra draw calls.
    _TRAIL_SEGMENTS = 14

    def draw(self):
        """Draw the head as a bright dot, then the trail as several
        short segments that both fade AND narrow from head to tail --
        a single flat-alpha draw_line reads as a rigid gray bar, not a
        comet streak, since every point along it is equally bright."""
        remaining = max(0.0, 1 - self.age / self.lifespan)
        head_alpha = int(255 * remaining)
        if head_alpha <= 0:
            return

        speed = math.hypot(self.dx, self.dy) or 1.0
        ux, uy = self.dx / speed, self.dy / speed

        segments = self._TRAIL_SEGMENTS
        for i in range(segments):
            t0 = i / segments
            t1 = (i + 1) / segments
            # t=0 is at the head, t=1 at the far end of the trail --
            # an exponent > 1 on the fade keeps most of the trail dim
            # and lets only the portion nearest the head read as bright,
            # which is what actually sells the "streak" look.
            seg_alpha = int(head_alpha * (1 - t1) ** 1.8)
            if seg_alpha <= 0:
                continue
            x0 = self.x - ux * self.length * t0
            y0 = self.y - uy * self.length * t0
            x1 = self.x - ux * self.length * t1
            y1 = self.y - uy * self.length * t1
            width = max(0.5, 2.4 * (1 - t0))
            arcade.draw_line(x0, y0, x1, y1, (255, 255, 255, seg_alpha), width)

        arcade.draw_circle_filled(self.x, self.y, 2.5,
            (255, 255, 255, head_alpha))


class Starfield:
    """Owns, updates, and draws every background layer: nebula haze,
    distant planets, the three parallax star layers, and any live
    shooting star."""

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

        self.nebulae = [
            NebulaBlob(
                x=random.uniform(0, width), y=random.uniform(0, height),
                color=random.choice(NEBULA_COLORS),
                scale=random.uniform(1.2, 2.8),
                drift_x=random.uniform(-0.05, 0.05),
                drift_y=random.uniform(-0.03, 0.03),
            )
            for _ in range(6)
        ]
        # arcade.Sprite has no draw() of its own in arcade 3.x -- only
        # SpriteList does -- so every sprite-backed decoration needs a
        # (tiny) SpriteList purely to be drawable. Updating each blob's
        # sprite.center_x/y in place still keeps the list in sync.
        self.nebula_sprites = arcade.SpriteList()
        self.nebula_sprites.extend(blob.sprite for blob in self.nebulae)

        self.planets = [
            Planet(
                x=random.uniform(width * 0.1, width * 0.9),
                y=random.uniform(height * 0.55, height * 0.95),
                diameter=random.randint(90, 160),
                base_color=random.choice((
                    (150, 120, 90), (110, 130, 160), (170, 100, 90),
                )),
                drift_x=random.uniform(-0.02, 0.02),
                drift_y=random.uniform(-0.01, 0.01),
            )
            for _ in range(random.randint(1, 2))
        ]
        self.planet_sprites = arcade.SpriteList()
        self.planet_sprites.extend(planet.sprite for planet in self.planets)

        self.shooting_stars = []
        self._next_shooting_star = random.uniform(*SHOOTING_STAR_INTERVAL)

    def update(self, dt=1.0):
        for star in self.stars:
            star.y -= star.speed * dt
            if star.y < 0:
                star.y += self.height
                star.x = random.uniform(0, self.width)
            star.twinkle_phase += star.twinkle_rate * dt

        for blob in self.nebulae:
            blob.update(dt, self.width, self.height)

        for planet in self.planets:
            planet.update(dt, self.width, self.height)

        self._update_shooting_stars(dt)

    def _update_shooting_stars(self, dt):
        self._next_shooting_star -= dt
        if self._next_shooting_star <= 0:
            self._spawn_shooting_star()
            self._next_shooting_star = random.uniform(*SHOOTING_STAR_INTERVAL)

        for star in self.shooting_stars:
            star.update(dt)
        self.shooting_stars = [s for s in self.shooting_stars if not s.dead]

    def _spawn_shooting_star(self):
        # Start just above the top edge and streak down at a shallow
        # diagonal, in a random left/right direction -- the classic
        # shooting-star trajectory.
        direction = random.choice((-1, 1))
        self.shooting_stars.append(ShootingStar(
            x=random.uniform(0, self.width), y=self.height + 20,
            dx=direction * random.uniform(10, 18),
            dy=-random.uniform(8, 14),
            length=random.uniform(60, 110),
            lifespan=random.uniform(45, 70),
        ))

    def draw(self):
        self.nebula_sprites.draw()
        self.planet_sprites.draw()

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

        for star in self.shooting_stars:
            star.draw()
