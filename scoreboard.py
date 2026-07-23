import arcade

from ship import Ship


class ShadowedText:
    """An arcade.Text with a soft dark shadow behind it, so it stays
    readable even when a bright star ends up directly behind a letter --
    the arcade equivalent of blitting the pygame version's text twice
    onto a transparent surface."""

    def __init__(self, text, x, y, color, font_size, anchor_x='left',
            anchor_y='baseline'):
        self.shadow = arcade.Text(text, x + 2, y - 2, (0, 0, 0, 255),
            font_size, anchor_x=anchor_x, anchor_y=anchor_y)
        self.label = arcade.Text(text, x, y, color, font_size,
            anchor_x=anchor_x, anchor_y=anchor_y)

    def set_text(self, text):
        self.shadow.text = text
        self.label.text = text

    def draw(self):
        self.shadow.draw()
        self.label.draw()


class Scoreboard:
    """A class to report scoring information."""

    def __init__(self, ai_game):
        """Initialize scorekeeping attributes."""
        self.ai_game = ai_game
        self.screen_width = ai_game.settings.screen_width
        self.screen_height = ai_game.settings.screen_height
        self.settings = ai_game.settings
        self.stats = ai_game.stats

        self.text_color = (230, 235, 245)
        self.font_size = 22

        # Prepare the initial score images.
        self.prep_score()
        self.prep_high_score()
        self.prep_level()
        self.prep_ships()
        self.prep_weapon()

    def prep_score(self):
        """Turn the score into a rendered label, at the top right."""
        rounded_score = round(self.stats.score, -1)
        text = f"Score: {rounded_score:,}"
        top = self.screen_height - 20
        right = self.screen_width - 20
        if hasattr(self, 'score_label'):
            self.score_label.set_text(text)
        else:
            self.score_label = ShadowedText(text, right, top, self.text_color,
                self.font_size, anchor_x='right', anchor_y='top')

    def prep_high_score(self):
        """Turn the high score into a rendered label, centered at top."""
        high_score = round(self.stats.high_score, -1)
        text = f"High Score: {high_score:,}"
        top = self.screen_height - 20
        center_x = self.screen_width / 2
        if hasattr(self, 'high_score_label'):
            self.high_score_label.set_text(text)
        else:
            self.high_score_label = ShadowedText(text, center_x, top,
                self.text_color, self.font_size,
                anchor_x='center', anchor_y='top')

    def check_high_score(self):
        """Check to see if there's a new high score."""
        if self.stats.score > self.stats.high_score:
            self.stats.high_score = self.stats.score
            self.prep_high_score()
            self.stats.save_high_score()

    def prep_level(self):
        """Turn the level into a rendered label, below the score."""
        text = f"Level: {self.stats.level}"
        right = self.screen_width - 20
        # Below the score row -- a fixed line-height offset, since
        # arcade's Text doesn't need a measured rect to position from.
        top = self.screen_height - 20 - (self.font_size + 18)
        if hasattr(self, 'level_label'):
            self.level_label.set_text(text)
        else:
            self.level_label = ShadowedText(text, right, top,
                self.text_color, self.font_size,
                anchor_x='right', anchor_y='top')

    def prep_ships(self):
        """Show how many ships are left."""
        self.ships = arcade.SpriteList()
        for ship_number in range(self.stats.ships_left):
            # These are static HUD icons -- never moved, never collided
            # -- so skip giving each one its own physics body (see
            # Ship.__init__ for why that matters).
            ship = Ship(self.ai_game, create_physics_body=False)
            ship.left = 10 + ship_number * ship.width
            ship.top = self.screen_height - 10
            self.ships.append(ship)

    def prep_weapon(self):
        """Turn the current weapon name into a rendered label, at the
        bottom left."""
        text = f"Weapon: {self.ai_game.current_weapon.title()} (1/2/3)"
        if hasattr(self, 'weapon_label'):
            self.weapon_label.set_text(text)
        else:
            self.weapon_label = ShadowedText(text, 20, 20, self.text_color,
                self.font_size, anchor_x='left', anchor_y='bottom')

    def show_score(self):
        """Draw scores, level, ships, and the current weapon to the screen."""
        self.score_label.draw()
        self.high_score_label.draw()
        self.level_label.draw()
        self.weapon_label.draw()
        self.ships.draw()
