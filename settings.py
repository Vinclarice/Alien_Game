from game_config import AlienType, WeaponType

class Settings:
    """A class to store all settings for Alien Invasion."""

    def __init__(self):
        """Initialize the game's static settings."""
        self.screen_width = 1200
        self.screen_height = 800
        self.bg_color = (8, 10, 24)  # deep space navy, behind the starfield

        # Sound effect volume (0.0-1.0), applied to every loaded sound.
        self.sfx_volume = 0.6

        # Ship settings.
        self.ship_limit = 3

        # Ship movement is physics-driven (see physics.py / ship.py),
        # Asteroids-style: UP/DOWN thrust forward/backward relative to
        # facing_angle (not fixed screen directions) up to ship_speed
        # (in initialize_dynamic_settings(), below), and drag brings it
        # to a coast rather than an instant stop.
        self.ship_thrust_ratio = 0.35  # thrust accel, as a fraction of ship_speed
        self.ship_drag = 0.85  # per-frame velocity retention (lower = stops faster)

        # Rotation (LEFT/RIGHT) is independent of thrust -- it only
        # changes which way the ship is pointed/fires/thrusts, and
        # doesn't move it on its own. Degrees per frame at 60fps, so 3.5
        # is a full 360 turn in about 1.7 seconds -- brisk enough to
        # reorient quickly, not so fast it's twitchy to control.
        self.ship_rotation_speed = 3.5

        # Bullet settings.
        self.bullets_allowed = 10

        # Weapon presets: base speed/size/color/spread for each weapon type.
        self.weapon_types = {
            'single': WeaponType(
                speed=4.0, width=3, height=15,
                color=(60, 60, 60), bullet_count=1,
            ),
            'spread': WeaponType(
                speed=5.0, width=3, height=12,
                color=(60, 140, 220), bullet_count=3, spread_angle=15,
            ),
            'heavy': WeaponType(
                speed=2.5, width=8, height=22,
                color=(200, 60, 60), bullet_count=1,
                # Slow, but punches through and can kill up to 3 aliens
                # in a line instead of being destroyed on the first hit.
                piercing=True, pierce_count=3,
                # At most 3 heavy bullets can be in the air at once, so
                # the pierce power can't be stacked into unlimited kills.
                max_active=3,
            ),
        }

        # Alien settings.
        self.fleet_drop_speed = 10

        # Alien type variety, recolored/rescaled from the same base image.
        # hits_required is how many bullet hits destroy it; points_multiplier
        # scales alien_points; speed_multiplier scales alien_speed for that
        # alien specifically, so types drift at different rates. weight sets
        # the odds of that type being picked when the fleet is built.
        self.alien_types = {
            'basic': AlienType(
                scale=1.0, tint=None,
                hits_required=1, points_multiplier=1.0,
                speed_multiplier=1.0, weight=0.65,
            ),
            'tank': AlienType(
                scale=1.4, tint=(200, 70, 70),
                hits_required=2, points_multiplier=2.0,
                speed_multiplier=0.75, weight=0.15,
            ),
            'scout': AlienType(
                scale=0.7, tint=(70, 170, 230),
                hits_required=1, points_multiplier=1.5,
                speed_multiplier=1.5, weight=0.20,
            ),
        }

        # Dive-attack settings: random aliens periodically break formation
        # and swoop toward the ship, then curve back up and bank off to
        # one side instead of just falling straight down off the bottom
        # of the screen -- a full attack-run arc rather than a one-way
        # drop. dive_speed/dive_duration keep the same tuned pacing as
        # before (do not speed these back up -- they were deliberately
        # slowed down across a few passes to feel readable, not rushed).
        self.dive_speed = 0.6  # descend rate, px/frame
        self.dive_duration = 220  # frames to reach target_x horizontally
        self.dive_amplitude = 15  # pixels of side-to-side wiggle while diving
        self.dive_wiggle_rate = 0.05  # how fast the wiggle oscillates
        self.dive_depth_fraction = 0.82  # how far down the screen a dive reaches
        self.dive_ascend_speed = 0.9  # climb-back-out rate, px/frame -- a bit
                                       # snappier than the descend so the escape
                                       # reads as a deliberate peel-away
        self.dive_bank_speed = 1.6  # px/frame sideways drift while ascending
        self.max_concurrent_dives = 2
        self.dive_cooldown_range = (90, 200)  # frames between dive attempts

        # Formation "hover": a small, per-alien-phased vertical bob
        # applied to the normal march so the fleet ripples gently
        # instead of moving in perfectly rigid lockstep.
        self.alien_bob_amplitude = 5  # pixels
        self.alien_bob_rate = 0.035  # radians/frame

        # How quickly the game speeds up.
        self.speedup_scale = 1.1

        # How quickly the alien point values increase.
        self.score_scale = 1.5

        self.initialize_dynamic_settings()

    def initialize_dynamic_settings(self):
        """Initialize settings that change throughout the game."""
        self.ship_speed = 7.5
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
