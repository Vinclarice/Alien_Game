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

    def __init__(self, x, y, angle, speed, width, height, color,
            weapon_name, piercing=False, pierce_count=1):
        """Create a bullet at (x, y), the ship's current nose position.

        angle, speed, width, height, color, and weapon_name are always
        supplied by the caller from a settings.WeaponType -- there's no
        sensible standalone default for a bullet's own look and feel, so
        this deliberately doesn't duplicate weapon_types['single'] here.

        angle is measured in degrees clockwise from straight up (the
        same convention as Ship.facing_angle) -- 0 with the ship facing
        its spawn orientation, but any value once the ship's been
        rotated, since the caller passes the ship's actual current
        facing_angle (plus any spread offset) rather than always 0.

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
        self.angle = angle

        # Break speed into x/y components based on the firing angle.
        # dy is positive (arcade's up direction) since straight-up is
        # the default firing direction, the opposite sign from the
        # pygame version's y-down world.
        radians = math.radians(angle)
        self.dx = speed * math.sin(radians)
        self.dy = speed * math.cos(radians)

        # Spawn with the bullet's leading edge (not its center) flush
        # with (x, y) -- the ship's nose point -- by nudging forward
        # half the bullet's own height along its firing angle, the same
        # way the original always nudged "up" when every bullet fired
        # straight up. Reuses dx/dy's unit direction rather than
        # recomputing sin/cos again.
        forward_x, forward_y = math.sin(radians), math.cos(radians)
        self.center_x = x + forward_x * (height / 2)
        self.center_y = y + forward_y * (height / 2)

    # left/right/top/bottom are an axis-aligned box using width/height
    # as if the bullet were still always vertical -- an approximation
    # now that bullets can fire at any angle, not the bullet's true
    # rotated footprint. Close enough for both collision and the
    # off-screen despawn check at this size/speed; a precise rotated
    # hitbox would need real rect-vs-rect-at-an-angle math for a gain
    # that's not visible on sprites this small.
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

    def _draw_capsule(self, cx, cy, width, height, color):
        """A rect with fully-rounded ends (a 'stadium' shape), rotated
        to this bullet's own firing angle -- the arcade equivalent of
        pygame's `border_radius=width // 2`, plus rotation so a bullet
        fired sideways or at a diagonal actually looks like it's
        pointing the way it's traveling instead of always standing
        upright regardless of its real direction."""
        radius = width / 2
        half_h = max(0.0, height / 2 - radius)
        rad = math.radians(self.angle)
        # Unit vector along the capsule's long axis (same convention as
        # dx/dy: 0 degrees is straight up) and the perpendicular unit
        # vector for its short axis.
        along_x, along_y = math.sin(rad), math.cos(rad)
        perp_x, perp_y = math.cos(rad), -math.sin(rad)

        if half_h > 0:
            corners = [
                (cx + along_x * half_h + perp_x * radius,
                    cy + along_y * half_h + perp_y * radius),
                (cx + along_x * half_h - perp_x * radius,
                    cy + along_y * half_h - perp_y * radius),
                (cx - along_x * half_h - perp_x * radius,
                    cy - along_y * half_h - perp_y * radius),
                (cx - along_x * half_h + perp_x * radius,
                    cy - along_y * half_h + perp_y * radius),
            ]
            arcade.draw_polygon_filled(corners, color)

        arcade.draw_circle_filled(
            cx + along_x * half_h, cy + along_y * half_h, radius, color)
        arcade.draw_circle_filled(
            cx - along_x * half_h, cy - along_y * half_h, radius, color)

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
