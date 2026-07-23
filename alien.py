import math
from pathlib import Path

import pygame
from pygame.sprite import Sprite

IMAGE_DIR = Path(__file__).resolve().parent / 'images'

class Alien(Sprite):
    """A class to represent a single alien in the fleet."""

    # The unmodified sprite, loaded once and reused as the base for
    # every recolored/rescaled alien type.
    _base_image = None

    # Built (tinted + scaled) sprite per alien_type, cached the first
    # time that type is built so every alien of that type shares one
    # Surface instead of re-tinting/re-scaling on every spawn.
    _built_images = {}

    def __init__(self, ai_game, alien_type='basic'):
        """Initialize the alien and set its starting position."""
        super().__init__()
        self.screen = ai_game.screen
        self.settings = ai_game.settings
        self.alien_type = alien_type

        type_settings = self.settings.alien_types[alien_type]
        self.hits_required = type_settings.hits_required
        self.hits_taken = 0
        self.points_multiplier = type_settings.points_multiplier
        self.speed_multiplier = type_settings.speed_multiplier
        # Untinted types (e.g. 'basic') have no tint color, so fall back
        # to a neutral gray for their explosion burst.
        self.explosion_color = type_settings.tint or (200, 200, 200)

        self.image = self._get_image_for_type(alien_type, type_settings)
        self.rect = self.image.get_rect()

        # Start each new alien near the top left of the screen.
        self.rect.x = self.rect.width
        self.rect.y = self.rect.height

        # Store the alien's exact position as floats for smooth movement.
        self.x = float(self.rect.x)
        self.y = float(self.rect.y)

        # Dive-attack state; set up by start_dive().
        self.diving = False
        self.dive_timer = 0

        # Hit-reaction stagger: a small damped-spring offset layered on
        # top of the alien's real position, kicked by stagger() whenever
        # it survives a hit (see take_hit()/its caller), so multi-hit
        # types like 'tank' visibly react to damage instead of just
        # silently absorbing it until the hit that finally kills them.
        self.stagger_offset = [0.0, 0.0]
        self.stagger_velocity = [0.0, 0.0]

    @classmethod
    def _load_base_image(cls):
        """Load images/alien.png once and cache it for every alien.

        convert_alpha() (not convert()) since alien.png has real
        per-pixel transparency -- see convert_sprites.py.
        """
        if cls._base_image is None:
            cls._base_image = pygame.image.load(
                str(IMAGE_DIR / 'alien.png')).convert_alpha()
        return cls._base_image

    @classmethod
    def _get_image_for_type(cls, alien_type, type_settings):
        """Return the (tinted + scaled) sprite for this alien type,
        building and caching it the first time that type is requested."""
        if alien_type not in cls._built_images:
            cls._built_images[alien_type] = cls._build_image(type_settings)
        return cls._built_images[alien_type]

    @classmethod
    def _build_image(cls, type_settings):
        """Build this type's sprite: recolored and scaled per its
        AlienType settings."""
        image = cls._load_base_image().copy()

        if type_settings.tint:
            image = cls._colorize(image, type_settings.tint)

        scale = type_settings.scale
        if scale != 1.0:
            new_size = (max(1, int(image.get_width() * scale)),
                max(1, int(image.get_height() * scale)))
            image = pygame.transform.scale(image, new_size)

        return image

    @staticmethod
    def _colorize(image, tint):
        """Recolor image using its own luminance as a brightness mask,
        so the tint's hue actually shows up while the sprite's shading
        still reads through.

        A plain multiply blend (the old approach: image.fill(tint,
        special_flags=BLEND_MULT)) can only darken channels that already
        have signal in them -- multiplying this green-dominant base
        sprite by a red tint left the 'tank' type a muddy dark olive
        instead of red, since there was little red there to begin with.
        Scaling the tint color by luminance instead means the output hue
        always matches the tint, regardless of the base sprite's colors.
        """
        colorized = pygame.Surface(image.get_size(), pygame.SRCALPHA)
        tr, tg, tb = tint
        for x in range(image.get_width()):
            for y in range(image.get_height()):
                r, g, b, a = image.get_at((x, y))
                if a == 0:
                    continue
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                colorized.set_at((x, y), (
                    int(tr * luminance), int(tg * luminance),
                    int(tb * luminance), a))
        return colorized

    def check_edges(self):
        """Return True if alien is at edge of screen."""
        screen_rect = self.screen.get_rect()
        return (self.rect.right >= screen_rect.right) or (self.rect.left <= 0)

    def update(self, dt=1.0):
        """Move the alien: either its normal fleet drift, or its dive.

        dt is a normalized delta-time factor, where 1.0 means "one frame
        at 60fps" -- this keeps speed constants tuned for 60fps correct
        while making movement frame-rate independent.
        """
        # Pull out last frame's stagger offset so the drift/dive logic
        # below works from the alien's true logical position, not a
        # position that already has an old offset baked into it.
        self.rect.x -= round(self.stagger_offset[0])
        self.rect.y -= round(self.stagger_offset[1])

        if self.diving:
            self._update_dive(dt)
        else:
            self.x += (self.settings.alien_speed *
                self.settings.fleet_direction * self.speed_multiplier * dt)
            self.rect.x = self.x

        self._update_stagger(dt)
        self.rect.x += round(self.stagger_offset[0])
        self.rect.y += round(self.stagger_offset[1])

    def stagger(self, dx, dy, strength=6.0):
        """Give this alien a brief physical kick in the (dx, dy)
        direction -- called when it survives a hit, so taking damage has
        a visible reaction. Purely a rendering/hitbox wobble; it doesn't
        touch self.x/self.y, so formation/dive logic is unaffected."""
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
        sine-wave wiggle, then despawn once fully off the bottom."""
        self.dive_timer += dt

        progress = min(1.0, self.dive_timer / self.settings.dive_duration)
        wiggle = (math.sin(self.dive_timer * self.settings.dive_wiggle_rate)
            * self.settings.dive_amplitude)
        self.x = (self.dive_start_x +
            (self.dive_target_x - self.dive_start_x) * progress) + wiggle
        self.y += self.settings.dive_speed * dt

        self.rect.x = self.x
        self.rect.y = self.y

        if self.rect.top > self.screen.get_rect().bottom:
            self.kill()

    def take_hit(self):
        """Register a bullet hit; return True if this destroys the alien."""
        self.hits_taken += 1
        return self.hits_taken >= self.hits_required
