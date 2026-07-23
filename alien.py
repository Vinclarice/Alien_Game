import math

import pygame
from pygame.sprite import Sprite

class Alien(Sprite):
    """A class to represent a single alien in the fleet."""

    # The unmodified sprite, loaded once and reused as the base for
    # every recolored/rescaled alien type.
    _base_image = None

    def __init__(self, ai_game, alien_type='basic'):
        """Initialize the alien and set its starting position."""
        super().__init__()
        self.screen = ai_game.screen
        self.settings = ai_game.settings
        self.alien_type = alien_type

        type_settings = self.settings.alien_types[alien_type]
        self.hits_required = type_settings['hits_required']
        self.hits_taken = 0
        self.points_multiplier = type_settings['points_multiplier']
        self.speed_multiplier = type_settings['speed_multiplier']

        self.image = self._build_image(type_settings)
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

    @classmethod
    def _load_base_image(cls):
        """Load images/alien.bmp once and cache it for every alien."""
        if cls._base_image is None:
            cls._base_image = pygame.image.load('images/alien.bmp').convert()
        return cls._base_image

    def _build_image(self, type_settings):
        """Return this alien's image, tinted and scaled per its type."""
        image = self._load_base_image().copy()

        tint = type_settings.get('tint')
        if tint:
            image.fill(tint, special_flags=pygame.BLEND_MULT)

        scale = type_settings.get('scale', 1.0)
        if scale != 1.0:
            new_size = (max(1, int(image.get_width() * scale)),
                max(1, int(image.get_height() * scale)))
            image = pygame.transform.scale(image, new_size)

        return image

    def check_edges(self):
        """Return True if alien is at edge of screen."""
        screen_rect = self.screen.get_rect()
        return (self.rect.right >= screen_rect.right) or (self.rect.left <= 0)

    def update(self):
        """Move the alien: either its normal fleet drift, or its dive."""
        if self.diving:
            self._update_dive()
        else:
            self.x += (self.settings.alien_speed *
                self.settings.fleet_direction * self.speed_multiplier)
            self.rect.x = self.x

    def start_dive(self, target_x):
        """Break from formation and swoop down toward target_x."""
        self.diving = True
        self.dive_timer = 0
        self.dive_start_x = self.x
        self.dive_target_x = target_x

    def _update_dive(self):
        """Advance one frame of a dive: swoop toward the target with a
        sine-wave wiggle, then despawn once fully off the bottom."""
        self.dive_timer += 1

        progress = min(1.0, self.dive_timer / self.settings.dive_duration)
        wiggle = (math.sin(self.dive_timer * self.settings.dive_wiggle_rate)
            * self.settings.dive_amplitude)
        self.x = (self.dive_start_x +
            (self.dive_target_x - self.dive_start_x) * progress) + wiggle
        self.y += self.settings.dive_speed

        self.rect.x = self.x
        self.rect.y = self.y

        if self.rect.top > self.screen.get_rect().bottom:
            self.kill()

    def take_hit(self):
        """Register a bullet hit; return True if this destroys the alien."""
        self.hits_taken += 1
        return self.hits_taken >= self.hits_required
