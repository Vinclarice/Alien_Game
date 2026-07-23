import math
from pathlib import Path

import arcade
from PIL import Image

IMAGE_DIR = Path(__file__).resolve().parent / 'images'


class Alien(arcade.Sprite):
    """A class to represent a single alien in the fleet.

    Arcade's coordinate system has y increasing upward with (0, 0) at
    the bottom-left of the screen, the opposite of pygame's y-down/
    top-left. Rather than rewrite every formation/drop/dive formula in
    terms of "up", this class keeps tracking position exactly the way
    the original did -- self.x (left edge) and self.dist_from_top
    (distance down from the top of the screen, what used to be
    rect.y/rect.x directly) -- and only converts to real screen
    coordinates in _sync_sprite_position(), the one place that actually
    needs to know which way is up.
    """

    # The unmodified sprite, loaded once (as a PIL Image so it can be
    # tinted per-pixel) and reused as the base for every alien type.
    _base_image = None

    # Built (tinted + scaled) texture per alien_type, cached the first
    # time that type is built so every alien of that type shares one
    # Texture instead of re-tinting/re-scaling on every spawn.
    _built_textures = {}

    def __init__(self, ai_game, alien_type='basic'):
        """Initialize the alien and set its starting position."""
        type_settings = ai_game.settings.alien_types[alien_type]
        texture = self._get_texture_for_type(alien_type, type_settings)
        super().__init__(texture)

        self.screen_width = ai_game.settings.screen_width
        self.screen_height = ai_game.settings.screen_height
        self.settings = ai_game.settings
        self.alien_type = alien_type

        self.hits_required = type_settings.hits_required
        self.hits_taken = 0
        self.points_multiplier = type_settings.points_multiplier
        self.speed_multiplier = type_settings.speed_multiplier
        # Untinted types (e.g. 'basic') have no tint color, so fall back
        # to a neutral gray for their explosion burst.
        self.explosion_color = type_settings.tint or (200, 200, 200)

        # Start each new alien near the top left of the screen -- these
        # get overwritten immediately by _create_alien's grid placement
        # for every alien except the disposable one _create_fleet makes
        # just to measure alien_width/alien_height.
        self.x = float(self.width)
        self.dist_from_top = float(self.height)

        # Dive-attack state; set up by start_dive().
        self.diving = False
        self.dive_timer = 0
        self.y = self.dist_from_top

        # Hit-reaction stagger: a small damped-spring offset layered on
        # top of the alien's real position, kicked by stagger() whenever
        # it survives a hit (see take_hit()/its caller), so multi-hit
        # types like 'tank' visibly react to damage instead of just
        # silently absorbing it until the hit that finally kills them.
        self.stagger_offset = [0.0, 0.0]
        self.stagger_velocity = [0.0, 0.0]

        self._sync_sprite_position()

    @classmethod
    def _load_base_image(cls):
        """Load images/alien.png once (as RGBA) and cache it for every
        alien -- PIL, not arcade's texture loader, since we need
        per-pixel access to tint it below."""
        if cls._base_image is None:
            cls._base_image = Image.open(
                str(IMAGE_DIR / 'alien.png')).convert('RGBA')
        return cls._base_image

    @classmethod
    def _get_texture_for_type(cls, alien_type, type_settings):
        """Return the (tinted + scaled) texture for this alien type,
        building and caching it the first time that type is requested."""
        if alien_type not in cls._built_textures:
            cls._built_textures[alien_type] = cls._build_texture(type_settings)
        return cls._built_textures[alien_type]

    @classmethod
    def _build_texture(cls, type_settings):
        """Build this type's texture: recolored and scaled per its
        AlienType settings."""
        image = cls._load_base_image().copy()

        if type_settings.tint:
            image = cls._colorize(image, type_settings.tint)

        scale = type_settings.scale
        if scale != 1.0:
            new_size = (max(1, int(image.width * scale)),
                max(1, int(image.height * scale)))
            image = image.resize(new_size, Image.LANCZOS)

        return arcade.Texture(image)

    @staticmethod
    def _colorize(image, tint):
        """Recolor image using its own luminance as a brightness mask,
        so the tint's hue actually shows up while the sprite's shading
        still reads through.

        A plain multiply blend can only darken channels that already
        have signal in them -- multiplying this green-dominant base
        sprite by a red tint left the 'tank' type a muddy dark olive
        instead of red, since there was little red there to begin with.
        Scaling the tint color by luminance instead means the output hue
        always matches the tint, regardless of the base sprite's colors.
        """
        colorized = Image.new('RGBA', image.size, (0, 0, 0, 0))
        src = image.load()
        dst = colorized.load()
        tr, tg, tb = tint
        for x in range(image.width):
            for y in range(image.height):
                r, g, b, a = src[x, y]
                if a == 0:
                    continue
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                dst[x, y] = (
                    int(tr * luminance), int(tg * luminance),
                    int(tb * luminance), a)
        return colorized

    def check_edges(self):
        """Return True if alien is at edge of screen."""
        return (self.right >= self.screen_width) or (self.left <= 0)

    def place(self, x, dist_from_top):
        """Set this alien's logical grid position directly -- used once
        by _create_alien() when building the fleet -- and immediately
        sync the sprite to match."""
        self.x = x
        self.dist_from_top = dist_from_top
        self.y = dist_from_top
        self._sync_sprite_position()

    def drop(self, amount):
        """Drop the formation down by amount -- used by
        _change_fleet_direction() when the fleet hits a screen edge.

        Also keeps self.y (the dive's vertical starting point) in sync
        with dist_from_top, so a dive that starts after the formation
        has dropped a few rows begins from the alien's actual current
        depth instead of snapping back to its spawn position.
        """
        self.dist_from_top += amount
        self.y = self.dist_from_top

    def update(self, dt=1.0, *args, **kwargs):
        """Move the alien: either its normal fleet drift, or its dive.

        dt is a normalized delta-time factor, where 1.0 means "one frame
        at 60fps" -- this keeps speed constants tuned for 60fps correct
        while making movement frame-rate independent.
        """
        if self.diving:
            self._update_dive(dt)
        else:
            self.x += (self.settings.alien_speed *
                self.settings.fleet_direction * self.speed_multiplier * dt)

        self._update_stagger(dt)
        self._sync_sprite_position()

    def _sync_sprite_position(self):
        """Push self.x/self.dist_from_top (plus the current stagger
        offset) into this sprite's actual screen coordinates, flipping
        into arcade's bottom-left/y-up frame, and despawn a dive that's
        fully scrolled off the bottom of the screen."""
        self.center_x = self.x + self.width / 2 + self.stagger_offset[0]
        self.top = (self.screen_height - self.dist_from_top +
            self.stagger_offset[1])

        if self.diving and self.top < 0:
            self.remove_from_sprite_lists()

    def stagger(self, dx, dy, strength=6.0):
        """Give this alien a brief physical kick in the (dx, dy)
        direction -- called when it survives a hit, so taking damage has
        a visible reaction. Purely a rendering/hitbox wobble; it doesn't
        touch self.x/self.dist_from_top, so formation/dive logic is
        unaffected. dx/dy use arcade's up-positive y convention, same as
        Bullet's own dx/dy, so a bullet's direction of travel and the
        stagger it imparts always agree without any extra sign-flipping
        here."""
        length = math.hypot(dx, dy) or 1.0
        self.stagger_velocity[0] += (dx / length) * strength
        self.stagger_velocity[1] += (dy / length) * strength

    def _update_stagger(self, dt):
        """Advance the stagger offset one frame as a damped spring that
        always settles back toward (0, 0)."""
        spring_k, damping_c = 0.09, 0.3
        for i in range(2):
            accel = (-spring_k * self.stagger_offset[i]
                - damping_c * self.stagger_velocity[i])
            self.stagger_velocity[i] += accel * dt
            self.stagger_offset[i] += self.stagger_velocity[i] * dt

    def start_dive(self, target_x):
        """Break from formation and swoop down toward target_x."""
        self.diving = True
        self.dive_timer = 0
        self.dive_start_x = self.x
        self.dive_target_x = target_x

    def _update_dive(self, dt):
        """Advance one frame of a dive: swoop toward the target with a
        sine-wave wiggle, then despawn once fully off the bottom (see
        _sync_sprite_position)."""
        self.dive_timer += dt

        progress = min(1.0, self.dive_timer / self.settings.dive_duration)
        wiggle = (math.sin(self.dive_timer * self.settings.dive_wiggle_rate)
            * self.settings.dive_amplitude)
        self.x = (self.dive_start_x +
            (self.dive_target_x - self.dive_start_x) * progress) + wiggle
        self.y += self.settings.dive_speed * dt
        self.dist_from_top = self.y

    def take_hit(self):
        """Register a bullet hit; return True if this destroys the alien."""
        self.hits_taken += 1
        return self.hits_taken >= self.hits_required
