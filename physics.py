"""Physics for Alien Invasion, powered by pymunk.

Only two things opt into real rigid-body physics: the ship (for momentum
and knockback) and alien debris chunks (for tumbling wreckage on death).
Everything else -- bullets, and the fleet's formation drift and dive
attacks -- stays on the existing simple float-position system, since
scripted, precisely-tuned motion is a better fit for them than handing
that control to a physics solver.

pymunk itself has no notion of "up" -- the walls are just two vertical
segments spanning the full y range at x=0 and x=width -- so none of this
needed to change when porting from pygame (y-down) to arcade (y-up).
Only draw_debris() (pygame.Surface rotation -> a rotated polygon) is
arcade-specific.
"""

import math
import random

import arcade
import pymunk

# Collision categories. Debris deliberately can't collide with the ship
# -- it's a visual flourish from a kill, not a hazard -- but both it and
# the ship collide with the screen's boundary walls, and debris pieces
# collide with each other for a bit of extra chaos as they scatter.
CATEGORY_SHIP = 0b001
CATEGORY_WALL = 0b010
CATEGORY_DEBRIS = 0b100


class Debris:
    """A small tumbling wreckage chunk left behind by a destroyed alien."""

    def __init__(self, body, shape, color, size, lifespan):
        self.body = body
        self.shape = shape
        self.color = color
        self.size = size
        self.lifespan = lifespan
        self.age = 0.0

    @property
    def alive_fraction(self):
        """0.0 when just spawned, 1.0 right before it's removed."""
        return min(1.0, self.age / self.lifespan)


class PhysicsWorld:
    """Owns the pymunk simulation: the screen's boundary walls, the
    ship's physics body, and every active debris chunk."""

    # Ambient drag applied only to debris (see step()) -- NOT set as
    # pymunk's own Space.damping, because that would apply to every
    # dynamic body in the space, including the ship, silently stacking
    # with the drag Ship.update() already applies and dragging its top
    # speed back down well below what settings.ship_speed says it is.
    DEBRIS_DAMPING = 0.96

    def __init__(self, screen_width, screen_height):
        self.space = pymunk.Space()
        self.space.gravity = (0, 0)  # top-down game -- no "down"
        self._debris = []
        self._add_walls(screen_width, screen_height)

    def _add_walls(self, width, height):
        """Static segments along all four screen edges so physics bodies
        (the ship, debris) stop or bounce there instead of sailing off
        past the visible play area -- the ship now moves freely on both
        axes, not just left/right, so it needs a top/bottom bound too."""
        static_body = self.space.static_body
        margin = max(width, height) * 2
        left = pymunk.Segment(static_body, (0, -margin), (0, height + margin), 2)
        right = pymunk.Segment(static_body, (width, -margin),
            (width, height + margin), 2)
        bottom = pymunk.Segment(static_body, (-margin, 0),
            (width + margin, 0), 2)
        top = pymunk.Segment(static_body, (-margin, height),
            (width + margin, height), 2)
        for wall in (left, right, bottom, top):
            wall.elasticity = 0.0
            wall.friction = 0.0
            wall.filter = pymunk.ShapeFilter(
                categories=CATEGORY_WALL, mask=CATEGORY_SHIP | CATEGORY_DEBRIS)
        self.space.add(left, right, bottom, top)

    def make_ship_body(self, width, height, x, y):
        """Build the ship's physics body/shape and add it to the space.
        Moment is infinite so collisions never spin the ship -- it should
        always stay upright, just like the pre-physics version did."""
        body = pymunk.Body(mass=1.0, moment=float('inf'))
        body.position = (x, y)
        shape = pymunk.Poly.create_box(body, (width, height))
        shape.elasticity = 0.0
        shape.friction = 0.0
        shape.filter = pymunk.ShapeFilter(
            categories=CATEGORY_SHIP, mask=CATEGORY_WALL)
        self.space.add(body, shape)
        return body

    def step(self, dt):
        """Advance the simulation one frame and age out expired debris.

        dt is the same normalized delta-time factor used everywhere else
        in the game (1.0 == one frame at 60fps), so every speed constant
        tuned for the rest of the game stays consistent here too.
        """
        for debris in self._debris:
            vx, vy = debris.body.velocity
            factor = self.DEBRIS_DAMPING ** dt
            debris.body.velocity = (vx * factor, vy * factor)
            debris.body.angular_velocity *= factor

        self.space.step(dt)

        for debris in list(self._debris):
            debris.age += dt
            if debris.age >= debris.lifespan:
                self._remove_debris(debris)

    def spawn_debris(self, x, y, color, count=None):
        """Fling a few small, tumbling wreckage chunks outward from
        (x, y) -- called when an alien is destroyed."""
        if count is None:
            count = random.randint(3, 5)

        for _ in range(count):
            size = random.uniform(4, 9)
            mass = 0.05
            moment = pymunk.moment_for_box(mass, (size, size))
            body = pymunk.Body(mass, moment)
            body.position = (x, y)

            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.5, 5.0)
            body.velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            body.angular_velocity = random.uniform(-8, 8)

            shape = pymunk.Poly.create_box(body, (size, size))
            shape.elasticity = 0.4
            shape.friction = 0.3
            shape.filter = pymunk.ShapeFilter(
                categories=CATEGORY_DEBRIS, mask=CATEGORY_WALL | CATEGORY_DEBRIS)

            self.space.add(body, shape)
            self._debris.append(Debris(body, shape, color, size,
                lifespan=random.uniform(30, 55)))

    def _remove_debris(self, debris):
        self.space.remove(debris.body, debris.shape)
        self._debris.remove(debris)

    def draw_debris(self):
        for debris in self._debris:
            alpha = max(0, int(255 * (1 - debris.alive_fraction)))
            half = debris.size / 2
            cx, cy = debris.body.position
            cos_a, sin_a = math.cos(debris.body.angle), math.sin(debris.body.angle)

            # Rotate the square's four corners by the body's own angle --
            # the pymunk-simulated tumble -- around its center.
            corners = []
            for lx, ly in ((-half, -half), (half, -half), (half, half), (-half, half)):
                corners.append((
                    cx + lx * cos_a - ly * sin_a,
                    cy + lx * sin_a + ly * cos_a,
                ))
            arcade.draw_polygon_filled(corners, (*debris.color, alpha))
