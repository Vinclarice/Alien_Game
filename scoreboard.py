import pygame.font
from pygame.sprite import Group

from ship import Ship

class Scoreboard:
    """A class to report scoring information."""

    def __init__(self, ai_game):
        """Initialize scorekeeping attributes."""
        self.ai_game = ai_game
        self.screen = ai_game.screen
        self.screen_rect = self.screen.get_rect()
        self.settings = ai_game.settings
        self.stats = ai_game.stats

        # Font settings for scoring information. Rendered with a
        # transparent background (see _render_label()) so the starfield
        # shows through instead of each label sitting in an opaque box.
        self.text_color = (230, 235, 245)
        self.font = pygame.font.SysFont(None, 48)

        # Prepare the initial score images.
        self.prep_score()
        self.prep_high_score()
        self.prep_level()
        self.prep_ships()
        self.prep_weapon()

    def _render_label(self, text):
        """Render text with a transparent background and a soft dark
        shadow, so it stays readable even when a bright star ends up
        directly behind a letter."""
        shadow = self.font.render(text, True, (0, 0, 0))
        label = self.font.render(text, True, self.text_color)
        surface = pygame.Surface(
            (label.get_width() + 2, label.get_height() + 2), pygame.SRCALPHA)
        surface.blit(shadow, (2, 2))
        surface.blit(label, (0, 0))
        return surface

    def prep_score(self):
        """Turn the score into a rendered image."""
        rounded_score = round(self.stats.score, -1)
        self.score_image = self._render_label(f"Score: {rounded_score:,}")

        # Display the score at the top right of the screen.
        self.score_rect = self.score_image.get_rect()
        self.score_rect.right = self.screen_rect.right - 20
        self.score_rect.top = 20

    def prep_high_score(self):
        """Turn the high score into a rendered image."""
        high_score = round(self.stats.high_score, -1)
        self.high_score_image = self._render_label(
            f"High Score: {high_score:,}")

        # Center the high score at the top of the screen.
        self.high_score_rect = self.high_score_image.get_rect()
        self.high_score_rect.centerx = self.screen_rect.centerx
        self.high_score_rect.top = self.score_rect.top

    def check_high_score(self):
        """Check to see if there's a new high score."""
        if self.stats.score > self.stats.high_score:
            self.stats.high_score = self.stats.score
            self.prep_high_score()
            self.stats.save_high_score()

    def prep_level(self):
        """Turn the level into a rendered image."""
        self.level_image = self._render_label(f"Level: {self.stats.level}")

        # Position the level below the score.
        self.level_rect = self.level_image.get_rect()
        self.level_rect.right = self.score_rect.right
        self.level_rect.top = self.score_rect.bottom + 10

    def prep_ships(self):
        """Show how many ships are left."""
        self.ships = Group()
        for ship_number in range(self.stats.ships_left):
            # These are static HUD icons -- never moved, never collided
            # -- so skip giving each one its own physics body (see
            # Ship.__init__ for why that matters).
            ship = Ship(self.ai_game, create_physics_body=False)
            ship.rect.x = 10 + ship_number * ship.rect.width
            ship.rect.y = 10
            self.ships.add(ship)

    def prep_weapon(self):
        """Turn the current weapon name into a rendered image."""
        weapon_str = f"Weapon: {self.ai_game.current_weapon.title()} (1/2/3)"
        self.weapon_image = self._render_label(weapon_str)

        # Position at the bottom left of the screen.
        self.weapon_rect = self.weapon_image.get_rect()
        self.weapon_rect.left = 20
        self.weapon_rect.bottom = self.screen_rect.bottom - 20

    def show_score(self):
        """Draw scores, level, ships, and the current weapon to the screen."""
        self.screen.blit(self.score_image, self.score_rect)
        self.screen.blit(self.high_score_image, self.high_score_rect)
        self.screen.blit(self.level_image, self.level_rect)
        self.screen.blit(self.weapon_image, self.weapon_rect)
        self.ships.draw(self.screen)
