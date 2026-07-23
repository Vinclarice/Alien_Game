import math

import arcade


class Bullet:
    """A class to manage bullets fired from the ship.

    Kept as a plain float-position object rather than an arcade.Sprite
    -- like the original pygame version, it draws itself every frame
    with a soft glow and a bright highlight core instead of going
    through a texture, so there's no benefit to the sprite/SpriteList
    machinery here.
    """

    def __init__(self, ai_game, angle, speed, width, height, color,
            weapon_name, piercing=False, pierce_count=1):
        """Create a bullet at the ship's current position.

        angle, speed, width, height, color, and weapon_name are always
        supplied by the caller from a settings.WeaponType -- there's no
        sensible standalone default for a bullet's own look and feel, so
        this deliberately doesn't duplicate weapon_types['single'] here.

        angle is measured in degrees from straight up, with positive
        values angled to the right -- used for spread/fan shots.

        piercing bullets survive hitting an alien instead of being
        destroyed on impact, and can go on to hit up to pierce_count
        aliens total before they're removed.
        """
        self.width = width
        self.height = height
        self.color = color
        # A brighter tint of the base color, used for the highlight core.
        self.highlight_color = tuple(min(255, c + 90) for c in color)

        self.piercing = piercing
        self.pierces_left = pierce_count
        self.weapon_name = weapon_name

        # Spawn with the bullet's leading edge (its top, since bullets
        # fly toward increasing y in arcade's y-up world) flush with the
        # ship's muzzle -- the arcade analog of the original's
        # `rect.midtop = ship.rect.midtop`.
        self.center_x = ai_game.ship.center_x
        self.center_y = ai_game.ship.top - height / 2

        # Break speed into x/y components based on the firing angle.
        # dy is positive (arcade's up direction) since straight-up is
        # the default firing direction, the opposite sign from the
        # pygame version's y-down world.
        radians = math.radians(angle)
        self.dx = speed * math.sin(radians)
        self.dy = speed * math.cos(radians)

    @property
    def left(self):
        return self.center_x - self.width / 2

    @property
    def right(self):
        return self.center_x + self.width / 2

    @property
    def bottom(self):
        return self.center_y - self.height / 2

    @property
    def top(self):
        return self.center_y + self.height / 2

    def update(self, dt=1.0):
        """Move the bullet along its angle.

        dt is a normalized delta-time factor, where 1.0 means "one frame
        at 60fps" -- see Alien.update() for why.
        """
        self.center_x += self.dx * dt
        self.center_y += self.dy * dt

    @staticmethod
    def _draw_capsule(cx, cy, width, height, color):
        """A rect with fully-rounded ends (a 'stadium' shape) -- the
        arcade equivalent of pygame's `border_radius=width // 2`."""
        radius = width / 2
        half_h = max(0.0, height / 2 - radius)
        if half_h > 0:
            arcade.draw_lrbt_rectangle_filled(
                cx - radius, cx + radius, cy - half_h, cy + half_h, color)
        arcade.draw_circle_filled(cx, cy + half_h, radius, color)
        arcade.draw_circle_filled(cx, cy - half_h, radius, color)

    def draw_bullet(self):
        """Draw the bullet with a soft glow and a bright highlight core."""
        # Soft glow behind the bullet body.
        self._draw_capsule(self.center_x, self.center_y,
            self.width + 10, self.height + 10, (*self.color, 80))

        # Main bullet body.
        self._draw_capsule(self.center_x, self.center_y,
            self.width, self.height, self.color)

        # Bright highlight stripe down the middle for a bit of shine.
        highlight_width = max(1, self.width - 2)
        highlight_height = max(1, int(self.height * 0.6))
        self._draw_capsule(self.center_x, self.center_y,
            highlight_width, highlight_height, self.highlight_color)
