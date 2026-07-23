import math

import pygame
from pygame.sprite import Sprite

class Bullet(Sprite):
    """A class to manage bullets fired from the ship."""

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
        super().__init__()
        self.screen = ai_game.screen
        self.color = color
        # A brighter tint of the base color, used for the highlight core.
        self.highlight_color = tuple(min(255, c + 90) for c in color)

        self.piercing = piercing
        self.pierces_left = pierce_count
        self.weapon_name = weapon_name

        # Create a bullet rect at (0, 0) and then set correct position.
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.midtop = ai_game.ship.rect.midtop

        # Store the bullet's position as floats for smooth movement.
        self.x = float(self.rect.x)
        self.y = float(self.rect.y)

        # Break speed into x/y components based on the firing angle.
        radians = math.radians(angle)
        self.dx = speed * math.sin(radians)
        self.dy = -speed * math.cos(radians)

    def update(self, dt=1.0):
        """Move the bullet along its angle.

        dt is a normalized delta-time factor, where 1.0 means "one frame
        at 60fps" -- see Alien.update() for why.
        """
        self.x += self.dx * dt
        self.y += self.dy * dt
        self.rect.x = self.x
        self.rect.y = self.y

    def draw_bullet(self):
        """Draw the bullet with a soft glow and a bright highlight core."""
        # Soft glow behind the bullet body.
        glow_size = (self.rect.width + 10, self.rect.height + 10)
        glow_surface = pygame.Surface(glow_size, pygame.SRCALPHA)
        pygame.draw.rect(glow_surface, (*self.color, 80),
            glow_surface.get_rect(), border_radius=glow_size[0] // 2)
        glow_rect = glow_surface.get_rect(center=self.rect.center)
        self.screen.blit(glow_surface, glow_rect)

        # Main bullet body.
        pygame.draw.rect(self.screen, self.color, self.rect,
            border_radius=self.rect.width // 2)

        # Bright highlight stripe down the middle for a bit of shine.
        highlight_width = max(1, self.rect.width - 2)
        highlight_height = max(1, int(self.rect.height * 0.6))
        highlight_rect = pygame.Rect(0, 0, highlight_width, highlight_height)
        highlight_rect.center = self.rect.center
        pygame.draw.rect(self.screen, self.highlight_color, highlight_rect,
            border_radius=highlight_width // 2)
