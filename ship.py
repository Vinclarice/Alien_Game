from pathlib import Path

import pygame
from pygame.sprite import Sprite

IMAGE_DIR = Path(__file__).resolve().parent / 'images'

class Ship(Sprite):
    """A class to manage the ship.

    Horizontal movement is physics-driven (via ai_game.physics): holding
    a direction key applies thrust, and drag brings the ship to a coast
    rather than an instant stop, so it has real momentum. The actual
    position integration and wall collision happens once per frame in
    PhysicsWorld.step(); sync_from_body() then copies the result into
    self.rect for drawing.
    """

    def __init__(self, ai_game, create_physics_body=True):
        """Initialize the ship, its physics body, and starting position.

        create_physics_body=False is for Scoreboard's life-icon sprites
        -- those only ever get blitted as a static HUD image, never
        moved or collided, so giving each one its own body/shape in the
        shared physics space would just leak: every life lost calls
        prep_ships() again, which used to add 3 more orphaned bodies to
        the simulation that nothing ever removed.
        """
        super().__init__()
        self.screen = ai_game.screen
        self.settings = ai_game.settings
        self.screen_rect = ai_game.screen.get_rect()

        # Load the ship image and get its rect. convert_alpha() (not
        # convert()) since ship.png has real per-pixel transparency --
        # see convert_sprites.py for why that matters against a
        # starfield background instead of a flat fill.
        self.image = pygame.image.load(
            str(IMAGE_DIR / 'ship.png')).convert_alpha()
        self.rect = self.image.get_rect()

        # Start each new ship at the bottom center of the screen.
        self.rect.midbottom = self.screen_rect.midbottom

        # Physics body driving horizontal movement (see class docstring).
        if create_physics_body:
            self.body = ai_game.physics.make_ship_body(
                self.rect.width, self.rect.height,
                self.rect.centerx, self.rect.centery)
        else:
            self.body = None

        # Movement flags, set by keydown/keyup handling in AlienInvasion.
        self.moving_right = False
        self.moving_left = False

    def update(self, dt=1.0):
        """Set the ship's desired velocity from its movement flags.

        This only sets intent -- PhysicsWorld.step() (called once per
        frame from the main loop, after every object has had a chance to
        set its velocity) does the actual position integration and wall
        collision. dt is the game's normalized delta-time factor, where
        1.0 means "one frame at 60fps".
        """
        vx, vy = self.body.velocity
        max_speed = self.settings.ship_speed
        thrust_accel = max_speed * self.settings.ship_thrust_ratio

        # Only add thrust while still under top speed -- this is what
        # actually makes max_speed the real cruising speed. (Letting
        # thrust keep adding past it and relying on drag alone to find
        # an equilibrium works, but that equilibrium depends on the
        # thrust/drag ratio, not on max_speed directly, which makes
        # ship_speed lie about what top speed actually is.)
        if self.moving_right and vx < max_speed:
            vx += thrust_accel * dt
        if self.moving_left and vx > -max_speed:
            vx -= thrust_accel * dt

        # Drag: bleeds off speed continuously, so releasing the key
        # coasts to a stop instead of snapping.
        vx *= self.settings.ship_drag ** dt

        # Belt-and-suspenders cap (well above max_speed) so a lag spike,
        # or a knockback impulse from _apply_ship_knockback, can still
        # briefly exceed max_speed and decay back down through drag
        # instead of being clamped away instantly.
        safety_cap = max_speed * 3
        vx = max(-safety_cap, min(safety_cap, vx))

        self.body.velocity = (vx, vy)

    def sync_from_body(self):
        """Pull the physics body's simulated position into self.rect.
        Called once per frame, after PhysicsWorld.step()."""
        self.rect.centerx = round(self.body.position.x)
        self.rect.centery = round(self.body.position.y)

    def blitme(self):
        """Draw the ship at its current location."""
        self.screen.blit(self.image, self.rect)

    def center_ship(self):
        """Recenter the ship for a new life/round, and kill its
        velocity so a knockback or drift from a moment ago doesn't
        carry over into the fresh start."""
        self.rect.midbottom = self.screen_rect.midbottom
        self.body.position = (self.rect.centerx, self.rect.centery)
        self.body.velocity = (0, 0)
