import math
from pathlib import Path

import arcade

IMAGE_DIR = Path(__file__).resolve().parent / 'images'


class Ship(arcade.Sprite):
    """A class to manage the ship.

    Controls are Asteroids-style: LEFT/RIGHT rotate the ship (turning
    facing_angle, which is also which way it fires), and UP/DOWN thrust
    forward/backward relative to whichever way it's currently facing --
    not fixed screen directions. Movement is physics-driven (via
    ai_game.physics): thrust sets velocity, and drag brings the ship to
    a coast rather than an instant stop, so it has real momentum. The
    actual position integration and wall collision happens once per
    frame in PhysicsWorld.step(); sync_from_body() then copies the
    result into this sprite's center_x/center_y for drawing.

    facing_angle uses "degrees clockwise from straight up", the same
    convention as Bullet's own angle parameter, so nose_position()/
    tail_position() and a bullet's own dx/dy math agree without any
    extra sign-flipping at the call site.

    Arcade's coordinate system has y increasing upward with (0, 0) at
    the bottom-left of the screen, the opposite of pygame's y-down/
    top-left, so "start at the bottom of the screen" here means pinning
    the sprite's bottom edge to y = 0 instead of y = screen_height.
    """

    def __init__(self, ai_game, create_physics_body=True):
        """Initialize the ship, its physics body, and starting position.

        create_physics_body=False is for Scoreboard's life-icon sprites
        -- those only ever get drawn as a static HUD image, never moved
        or collided, so giving each one its own body/shape in the
        shared physics space would just leak: every life lost calls
        prep_ships() again, which would otherwise add 3 more orphaned
        bodies to the simulation that nothing ever removes.
        """
        super().__init__(str(IMAGE_DIR / 'ship.png'))
        self.settings = ai_game.settings
        self.screen_width = ai_game.settings.screen_width
        self.screen_height = ai_game.settings.screen_height

        # Start each new ship at the bottom center of the screen.
        self.center_x = self.screen_width / 2
        self.bottom = 0

        # Physics body driving horizontal movement (see class docstring).
        if create_physics_body:
            self.body = ai_game.physics.make_ship_body(
                self.width, self.height, self.center_x, self.center_y)
        else:
            self.body = None

        # Control flags, set by keydown/keyup handling in AlienInvasion.
        # LEFT/RIGHT rotate; UP/DOWN thrust forward/backward relative to
        # facing_angle, not fixed screen directions.
        self.rotating_left = False
        self.rotating_right = False
        self.thrusting_forward = False
        self.thrusting_backward = False

        # 0 is straight up, matching the sprite's native orientation, so
        # no rotation is needed at spawn.
        self.facing_angle = 0.0

    def update(self, dt=1.0, *args, **kwargs):
        """Set the ship's desired velocity from its control flags.

        This only sets intent -- PhysicsWorld.step() (called once per
        frame from the main loop, after every object has had a chance to
        set its velocity) does the actual position integration and wall
        collision. dt is the game's normalized delta-time factor, where
        1.0 means "one frame at 60fps".
        """
        if self.rotating_left:
            self.facing_angle -= self.settings.ship_rotation_speed * dt
        if self.rotating_right:
            self.facing_angle += self.settings.ship_rotation_speed * dt
        self.facing_angle %= 360.0

        # arcade.Sprite.angle rotates the drawn texture clockwise for
        # positive degrees -- the same convention facing_angle already
        # uses -- so the sprite always visibly points the way it fires.
        self.angle = self.facing_angle

        vx, vy = self.body.velocity
        max_speed = self.settings.ship_speed
        thrust_accel = max_speed * self.settings.ship_thrust_ratio

        # Thrust is along the ship's current facing, not a fixed screen
        # axis -- the same unit vector nose_position() uses.
        rad = math.radians(self.facing_angle)
        forward_x, forward_y = math.sin(rad), math.cos(rad)

        # Only add thrust while still under top speed *in that
        # direction* -- the projection of current velocity onto the
        # thrust axis -- which is what actually makes max_speed the
        # real cruising speed. (Letting thrust keep adding past it and
        # relying on drag alone to find an equilibrium works, but that
        # equilibrium depends on the thrust/drag ratio, not on
        # max_speed directly, which makes ship_speed lie about what top
        # speed actually is.)
        forward_speed = vx * forward_x + vy * forward_y
        if self.thrusting_forward and forward_speed < max_speed:
            vx += forward_x * thrust_accel * dt
            vy += forward_y * thrust_accel * dt
        if self.thrusting_backward and -forward_speed < max_speed:
            vx -= forward_x * thrust_accel * dt
            vy -= forward_y * thrust_accel * dt

        # Drag: bleeds off speed continuously, so releasing the key
        # coasts to a stop instead of snapping.
        vx *= self.settings.ship_drag ** dt
        vy *= self.settings.ship_drag ** dt

        # Belt-and-suspenders cap (well above max_speed) so a lag spike,
        # or a knockback impulse from _apply_ship_knockback, can still
        # briefly exceed max_speed and decay back down through drag
        # instead of being clamped away instantly. Thrust isn't
        # axis-aligned anymore, so this clamps the velocity vector's
        # magnitude instead of each axis independently.
        safety_cap = max_speed * 3
        speed = math.hypot(vx, vy)
        if speed > safety_cap:
            scale = safety_cap / speed
            vx *= scale
            vy *= scale

        self.body.velocity = (vx, vy)

    def nose_position(self, offset=None):
        """World (x, y) of the ship's nose -- where bullets spawn and
        aim from. Defaults to half the sprite's own height out from
        center, i.e. right at the drawn tip regardless of facing_angle."""
        if offset is None:
            offset = self.height / 2
        rad = math.radians(self.facing_angle)
        return (
            self.center_x + math.sin(rad) * offset,
            self.center_y + math.cos(rad) * offset,
        )

    def tail_position(self, offset=None):
        """World (x, y) of the ship's tail -- where the engine trail/
        glow anchors, always opposite the nose regardless of
        facing_angle."""
        if offset is None:
            offset = self.height / 2
        rad = math.radians(self.facing_angle)
        return (
            self.center_x - math.sin(rad) * offset,
            self.center_y - math.cos(rad) * offset,
        )

    def right_vector(self):
        """Unit vector pointing out the ship's right side (perpendicular
        to facing_angle) -- used to jitter the engine trail side-to-side
        relative to the ship's own orientation instead of the screen's."""
        rad = math.radians(self.facing_angle)
        return (math.cos(rad), -math.sin(rad))

    def sync_from_body(self):
        """Pull the physics body's simulated position into this sprite.
        Called once per frame, after PhysicsWorld.step()."""
        self.center_x = self.body.position.x
        self.center_y = self.body.position.y

    def center_ship(self):
        """Recenter the ship for a new life/round, and kill its
        velocity so a knockback or drift from a moment ago doesn't
        carry over into the fresh start."""
        self.center_x = self.screen_width / 2
        self.bottom = 0
        self.body.position = (self.center_x, self.center_y)
        self.body.velocity = (0, 0)
