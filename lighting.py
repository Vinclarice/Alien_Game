"""Dynamic, per-pixel point lighting for Alien Invasion.

Wraps arcade's GPU-based Light/LightLayer (arcade.future.light) so the
rest of the game only ever deals with simple spawn_*/sync_* calls, the
same shape as ParticleSystem. Everything meant to actually glow --
muzzle flashes, explosions, bullets in flight, the ship's engine --
gets a real additive light source instead of a faked alpha blob.

Ambient is left at full white (255, 255, 255), i.e. the combine shader
(diffuse * ambient/255 + diffuse * light) reduces to plain diffuse
wherever no light reaches -- nothing gets darker than today's render.
Lights only ever add brightness on top, so bright/colored pools appear
around lasers and explosions without risking a scene that's harder to
read. Lowering AMBIENT later is the natural next step if a moodier,
darker-with-light-pools look is wanted instead.
"""

import arcade
from arcade.future.light import Light, LightLayer

AMBIENT = (255, 255, 255)

MUZZLE_FLASH_RADIUS = 130
MUZZLE_FLASH_LIFESPAN = 8

EXPLOSION_RADIUS = 220
EXPLOSION_LIFESPAN = 30

SHIP_EXPLOSION_RADIUS = 320
SHIP_EXPLOSION_LIFESPAN = 40

BULLET_LIGHT_RADIUS = 70
ENGINE_LIGHT_RADIUS = 90


class _Pulse:
    """A one-shot light that shrinks to nothing over its lifespan -- the
    lighting equivalent of particles.Particle, for flashes/explosions
    that aren't tied to a game object that already updates every frame."""

    __slots__ = ('light', 'age', 'lifespan', 'start_radius')

    def __init__(self, light, lifespan):
        self.light = light
        self.age = 0.0
        self.lifespan = lifespan
        self.start_radius = light.radius

    @property
    def dead(self):
        return self.age >= self.lifespan

    def update(self, dt):
        self.age += dt
        remaining = max(0.0, 1 - self.age / self.lifespan)
        self.light.radius = self.start_radius * remaining


class LightingSystem:
    """Owns the LightLayer plus every transient/attached light in play.

    Usage from AlienInvasion:
        with self.lighting:
            <draw everything that should be lit>
        self.lighting.draw()
    """

    def __init__(self, width, height, background_color=(0, 0, 0)):
        self.layer = LightLayer(width, height)
        self.layer.set_background_color((*background_color, 255))
        self._pulses = []
        self._bullet_lights = {}  # id(bullet) -> Light, synced each frame
        self._engine_light = None

    def resize(self, width, height):
        self.layer.resize(width, height)

    def update(self, dt):
        """Advance every transient light pulse and drop expired ones."""
        for pulse in self._pulses:
            pulse.update(dt)

        expired = [p for p in self._pulses if p.dead]
        for pulse in expired:
            self.layer.remove(pulse.light)
        self._pulses = [p for p in self._pulses if not p.dead]

    def _spawn_pulse(self, x, y, color, radius, lifespan):
        light = Light(x, y, radius=radius, color=color, mode='soft')
        self.layer.add(light)
        self._pulses.append(_Pulse(light, lifespan))

    def spawn_muzzle_flash(self, x, y, color):
        """A quick, bright pop at the gun's tip -- one per trigger pull."""
        self._spawn_pulse(x, y, color, MUZZLE_FLASH_RADIUS,
            MUZZLE_FLASH_LIFESPAN)

    def spawn_explosion(self, x, y, color):
        """An alien (or other regular) kill's light burst."""
        self._spawn_pulse(x, y, color, EXPLOSION_RADIUS, EXPLOSION_LIFESPAN)

    def spawn_ship_explosion(self, x, y, color):
        """The ship's own, bigger death flash."""
        self._spawn_pulse(x, y, color, SHIP_EXPLOSION_RADIUS,
            SHIP_EXPLOSION_LIFESPAN)

    def sync_bullets(self, bullets):
        """Keep exactly one Light per live bullet, following its
        position -- lasers glow along their whole flight, not just on
        impact."""
        live_ids = set()
        for bullet in bullets:
            key = id(bullet)
            live_ids.add(key)
            light = self._bullet_lights.get(key)
            if light is None:
                light = Light(bullet.center_x, bullet.center_y,
                    radius=BULLET_LIGHT_RADIUS, color=bullet.color,
                    mode='soft')
                self.layer.add(light)
                self._bullet_lights[key] = light
            else:
                light.position = (bullet.center_x, bullet.center_y)

        stale = [key for key in self._bullet_lights if key not in live_ids]
        for key in stale:
            self.layer.remove(self._bullet_lights.pop(key))

    def set_engine_light(self, x, y, color=(255, 170, 60)):
        """Create (or move) the ship's single persistent engine glow."""
        if self._engine_light is None:
            self._engine_light = Light(x, y, radius=ENGINE_LIGHT_RADIUS,
                color=color, mode='soft')
            self.layer.add(self._engine_light)
        else:
            self._engine_light.position = (x, y)

    def clear_engine_light(self):
        """Turn the engine glow off, e.g. between rounds or on the menu."""
        if self._engine_light is not None:
            self.layer.remove(self._engine_light)
            self._engine_light = None

    def __enter__(self):
        self.layer.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.layer.__exit__(exc_type, exc_val, exc_tb)

    def draw(self):
        self.layer.draw(ambient_color=AMBIENT)
