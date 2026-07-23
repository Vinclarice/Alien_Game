import arcade


class Button:
    """A class to build buttons for the game."""

    def __init__(self, ai_game, msg):
        """Initialize button attributes."""
        screen_width = ai_game.settings.screen_width
        screen_height = ai_game.settings.screen_height

        # Set the dimensions and properties of the button.
        self.width, self.height = 200, 50
        self.button_color = (0, 135, 0)
        self.text_color = (255, 255, 255)

        # Center the button on screen.
        self.center_x = screen_width / 2
        self.center_y = screen_height / 2
        self.left = self.center_x - self.width / 2
        self.right = self.center_x + self.width / 2
        self.bottom = self.center_y - self.height / 2
        self.top = self.center_y + self.height / 2

        self.msg_text = arcade.Text(
            msg, self.center_x, self.center_y, self.text_color,
            font_size=22, anchor_x='center', anchor_y='center')

    def collides_with_point(self, x, y):
        """Return True if (x, y) -- e.g. a mouse click -- is inside the
        button's rectangle."""
        return (self.left <= x <= self.right and
            self.bottom <= y <= self.top)

    def draw_button(self):
        """Draw blank button and then draw message."""
        arcade.draw_lrbt_rectangle_filled(
            self.left, self.right, self.bottom, self.top, self.button_color)
        self.msg_text.draw()
