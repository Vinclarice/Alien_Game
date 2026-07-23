class Settings:
    """A class to store all settings for Alien Invasion."""

    def __init__(self):
        """Initialize the game's static settings."""
        self.screen_width = 1200
        self.screen_height = 800
        self.bg_color = (230, 230, 230)

        # Ship settings.
        self.ship_limit = 3

        # Bullet settings.
        self.bullets_allowed = 10

        # Weapon presets: base speed/size/color/spread for each weapon type.
        # bullet_count is how many bullets one shot fires; spread_angle is
        # the angle (in degrees) between adjacent bullets in a multi-shot.
        self.weapon_types = {
            'single': {
                'speed': 4.0, 'width': 3, 'height': 15,
                'color': (60, 60, 60), 'bullet_count': 1, 'spread_angle': 0,
            },
            'spread': {
                'speed': 5.0, 'width': 3, 'height': 12,
                'color': (60, 140, 220), 'bullet_count': 3, 'spread_angle': 15,
            },
            'heavy': {
                'speed': 2.5, 'width': 8, 'height': 22,
                'color': (200, 60, 60), 'bullet_count': 1, 'spread_angle': 0,
                # Slow, but punches through and can kill up to 3 aliens
                # in a line instead of being destroyed on the first hit.
                'piercing': True, 'pierce_count': 3,
                # At most 3 heavy bullets can be in the air at once, so
                # the pierce power can't be stacked into unlimited kills.
                'max_active': 3,
            },
        }

        # Alien settings.
        self.fleet_drop_speed = 10

        # How quickly the game speeds up.
        self.speedup_scale = 1.1

        # How quickly the alien point values increase.
        self.score_scale = 1.5

        self.initialize_dynamic_settings()

    def initialize_dynamic_settings(self):
        """Initialize settings that change throughout the game."""
        self.ship_speed = 3.0
        self.alien_speed = 1.0

        # Multiplies every weapon's base speed; scales up as levels increase.
        self.bullet_speed_multiplier = 1.0

        # fleet_direction of 1 represents right; -1 represents left.
        self.fleet_direction = 1

        # Scoring.
        self.alien_points = 50

    def increase_speed(self):
        """Increase speed settings and alien point values."""
        self.ship_speed *= self.speedup_scale
        self.bullet_speed_multiplier *= self.speedup_scale
        self.alien_speed *= self.speedup_scale

        self.alien_points = int(self.alien_points * self.score_scale)
