import random
import time

import arcade

from settings import Settings
from game_stats import GameStats
from game_state import GameState
from ship import Ship
from bullet import Bullet
from alien import Alien
from button import Button
from scoreboard import Scoreboard
from formations import random_formation
from particles import ParticleSystem
from physics import PhysicsWorld
from audio import AudioManager
from starfield import Starfield
from lighting import LightingSystem
from post_fx import PostFX


class AlienInvasion(arcade.Window):
    """Overall class to manage game assets and behavior.

    Ported from a pygame version -- see the pygame edition alongside
    this folder for the original. The biggest structural difference is
    arcade's coordinate system: y increases upward with (0, 0) at the
    bottom-left of the window, the opposite of pygame's y-down/top-left.
    Every place that mattered is called out in the relevant module's
    docstring/comments (ship, alien, bullet, particles, starfield).
    """

    def __init__(self):
        """Initialize the game, and create game resources."""
        display_width, display_height = arcade.get_display_size()
        super().__init__(display_width, display_height, "Alien Invasion",
            fullscreen=True, vsync=True, update_rate=1 / 60)

        self.settings = Settings()
        self.settings.screen_width = self.width
        self.settings.screen_height = self.height
        self.stats = GameStats(self)

        self.background_color = self.settings.bg_color
        self.starfield = Starfield(
            self.settings.screen_width, self.settings.screen_height)

        self.audio = AudioManager(self.settings.sfx_volume)

        # Physics (ship momentum/knockback, debris) -- created before the
        # ship, since Ship.__init__ needs it to build its physics body.
        self.physics = PhysicsWorld(
            self.settings.screen_width, self.settings.screen_height)

        self.ship = Ship(self)
        self.ship_list = arcade.SpriteList()
        self.ship_list.append(self.ship)

        self.bullets = []
        self.aliens = arcade.SpriteList()
        self.particles = ParticleSystem()
        self.lighting = LightingSystem(
            self.settings.screen_width, self.settings.screen_height,
            background_color=self.settings.bg_color)
        self.post_fx = PostFX(
            self.settings.screen_width, self.settings.screen_height)

        self._create_fleet()

        # The weapon currently in use; switch with the 1/2/3 keys.
        self.current_weapon = 'single'

        # Create the scoreboard.
        self.sb = Scoreboard(self)

        # Start Alien Invasion at the main menu.
        self.state = GameState.MENU

        # Make the Play button and the game-over headline text objects.
        self.play_button = Button(self, "Play")
        self.game_over_heading = arcade.Text(
            "GAME OVER", self.width / 2, 0, (255, 70, 70), font_size=32,
            anchor_x='center', anchor_y='bottom')
        self.game_over_score = arcade.Text(
            "", self.width / 2, 0, (220, 225, 235), font_size=18,
            anchor_x='center', anchor_y='top')

        self.set_mouse_visible(True)

    def on_update(self, delta_time):
        """Advance one frame of game logic.

        delta_time is real elapsed seconds (arcade's own convention).
        Convert it to the same normalized "1.0 == one frame at 60fps"
        factor the rest of the game's speed constants assume, clamped so
        a stall (e.g. dragging the window) can't fling everything across
        the screen in one jump.
        """
        dt = min(delta_time * 60, 3.0)

        if self.state == GameState.PLAYING:
            self.ship.update(dt)
            self._update_bullets(dt)
            self._update_aliens(dt)
            self._emit_engine_trail()
            self.lighting.set_engine_light(
                self.ship.center_x, self.ship.bottom + 4)
        else:
            self.lighting.clear_engine_light()

        # Physics (ship momentum/wall collision, debris tumbling) and
        # particles keep advancing even off PLAYING, so a knockback or
        # explosion already in progress finishes playing out on the
        # menu/game-over screen instead of freezing mid-animation.
        self.physics.step(dt)
        self.ship.sync_from_body()
        self.particles.update(dt)
        self.starfield.update(dt)  # drifts on the menu too, not just PLAYING
        self.lighting.sync_bullets(self.bullets)
        self.lighting.update(dt)

    def on_draw(self):
        """Render the current frame.

        Everything that should be lit and bloom draws into an offscreen
        buffer first: the world layer draws inside 'with self.lighting:'
        (so it gets real point lighting), which composites into
        self.post_fx's input framebuffer instead of straight to the
        window. self.post_fx.draw() then runs the full-screen bloom
        shader and writes the final image to the actual window. HUD and
        menu UI are drawn last, straight onto the window, so neither
        lighting nor bloom ever affects text/button legibility.
        """
        self.post_fx.use()
        self.post_fx.clear()

        with self.lighting:
            self.starfield.draw()
            for bullet in self.bullets:
                bullet.draw_bullet()
            self.ship_list.draw()
            self.aliens.draw()
            self.physics.draw_debris()
            self.particles.draw()
        self.lighting.draw(target=self.post_fx.fbo)

        self.use()  # rebind the window so bloom's output lands on screen
        self.post_fx.draw()

        # Draw the score information.
        self.sb.show_score()

        # Draw the play button whenever the game isn't actively running.
        if self.state != GameState.PLAYING:
            self.play_button.draw_button()

        # On top of that, show a game-over headline and final score.
        if self.state == GameState.GAME_OVER:
            self._draw_game_over()

    def on_mouse_press(self, x, y, button, modifiers):
        """Start a new game when the player clicks Play."""
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        if (self.play_button.collides_with_point(x, y) and
                self.state != GameState.PLAYING):
            self._start_game()

    def _start_game(self):
        """Reset game state and begin a new game."""
        self.audio.play('ui_select')

        # Reset the game settings.
        self.settings.initialize_dynamic_settings()

        # Reset the game statistics.
        self.stats.reset_stats()
        self.state = GameState.PLAYING
        self.sb.prep_score()
        self.sb.prep_level()
        self.sb.prep_ships()
        self.current_weapon = 'single'
        self.sb.prep_weapon()

        self._start_fresh_fleet()

        # Hide the mouse cursor.
        self.set_mouse_visible(False)

    def on_key_press(self, key, modifiers):
        """Respond to keypresses."""
        if key == arcade.key.RIGHT:
            self.ship.moving_right = True
        elif key == arcade.key.LEFT:
            self.ship.moving_left = True
        elif key == arcade.key.UP:
            self.ship.moving_up = True
        elif key == arcade.key.DOWN:
            self.ship.moving_down = True
        elif key == arcade.key.Q:
            self.close()
        elif key == arcade.key.P and self.state != GameState.PLAYING:
            self._start_game()
        elif self.state == GameState.PLAYING and key == arcade.key.SPACE:
            self._fire_bullet()
        elif self.state == GameState.PLAYING and key == arcade.key.KEY_1:
            self.current_weapon = 'single'
            self.sb.prep_weapon()
        elif self.state == GameState.PLAYING and key == arcade.key.KEY_2:
            self.current_weapon = 'spread'
            self.sb.prep_weapon()
        elif self.state == GameState.PLAYING and key == arcade.key.KEY_3:
            self.current_weapon = 'heavy'
            self.sb.prep_weapon()

    def on_key_release(self, key, modifiers):
        """Respond to key releases."""
        if key == arcade.key.RIGHT:
            self.ship.moving_right = False
        elif key == arcade.key.LEFT:
            self.ship.moving_left = False
        elif key == arcade.key.UP:
            self.ship.moving_up = False
        elif key == arcade.key.DOWN:
            self.ship.moving_down = False

    def _emit_engine_trail(self):
        """Release one puff of exhaust behind the ship this frame; called
        every frame while playing so the puffs build into a trail."""
        x = self.ship.center_x + random.uniform(-4, 4)
        # The ship's rear, tucked slightly inward from its very bottom
        # edge -- the arcade analog of the pygame version's
        # `ship.rect.bottom - 4` (there, subtracting moved the point up
        # into the ship since pygame's y increases downward).
        y = self.ship.bottom + 4
        self.particles.spawn_engine_trail(x, y, (255, 170, 60))

    def _fire_bullet(self):
        """Fire the current weapon, respecting the total bullet cap."""
        weapon = self.settings.weapon_types[self.current_weapon]

        # Don't fire if this shot would push past the overall bullet limit.
        if len(self.bullets) + weapon.bullet_count > self.settings.bullets_allowed:
            return

        # Some weapons (e.g. the piercing heavy bullet) also cap how many
        # of that specific weapon can be active at once.
        if weapon.max_active is not None:
            active_of_type = sum(1 for bullet in self.bullets
                if bullet.weapon_name == self.current_weapon)
            if active_of_type + weapon.bullet_count > weapon.max_active:
                return

        speed = weapon.speed * self.settings.bullet_speed_multiplier

        if weapon.bullet_count == 1:
            angles = [0]
        else:
            # Fan the bullets out evenly around straight up.
            half = (weapon.bullet_count - 1) / 2
            angles = [(i - half) * weapon.spread_angle
                for i in range(weapon.bullet_count)]

        for angle in angles:
            new_bullet = Bullet(self, angle=angle, speed=speed,
                width=weapon.width, height=weapon.height,
                color=weapon.color, weapon_name=self.current_weapon,
                piercing=weapon.piercing, pierce_count=weapon.pierce_count)
            self.bullets.append(new_bullet)

        # One flash/sound per trigger pull, regardless of how many
        # bullets that shot fires.
        gun_x, gun_y = self.ship.center_x, self.ship.top
        self.particles.spawn_muzzle_flash(gun_x, gun_y, weapon.color)
        self.lighting.spawn_muzzle_flash(gun_x, gun_y, weapon.color)
        self.audio.play(f'laser_{self.current_weapon}')

    def _update_bullets(self, dt):
        """Update position of bullets and get rid of old bullets."""
        for bullet in self.bullets:
            bullet.update(dt)

        # Get rid of bullets that have disappeared off any edge of the
        # screen (spread shots can drift off the sides, not just the
        # top -- "top" here meaning increasing y, arcade's up).
        for bullet in self.bullets[:]:
            if (bullet.bottom >= self.settings.screen_height or
                    bullet.right <= 0 or bullet.left >= self.settings.screen_width):
                self.bullets.remove(bullet)

        self._check_bullet_alien_collisions()

    @staticmethod
    def _bullet_hits_alien(bullet, alien):
        """Axis-aligned bounding-box overlap test between a (plain,
        non-sprite) bullet and an alien sprite -- the arcade equivalent
        of pygame's Rect.colliderect()."""
        return not (bullet.right < alien.left or bullet.left > alien.right or
            bullet.top < alien.bottom or bullet.bottom > alien.top)

    def _check_bullet_alien_collisions(self):
        """Respond to bullet-alien collisions."""
        # Check each bullet against the fleet individually, since piercing
        # bullets need to survive a hit, and tougher aliens can survive
        # one too -- neither is destroyed automatically on contact.
        points_earned = 0
        for bullet in self.bullets[:]:
            hit_aliens = [alien for alien in self.aliens
                if self._bullet_hits_alien(bullet, alien)]
            if not hit_aliens:
                continue

            for alien in hit_aliens:
                if alien.take_hit():
                    points_earned += self.settings.alien_points * alien.points_multiplier
                    self.particles.spawn_explosion(alien.center_x,
                        alien.center_y, alien.explosion_color)
                    self.lighting.spawn_explosion(alien.center_x,
                        alien.center_y, alien.explosion_color)
                    self.physics.spawn_debris(alien.center_x,
                        alien.center_y, alien.explosion_color)
                    self.audio.play('explosion_alien')
                    alien.remove_from_sprite_lists()
                else:
                    # Survived the hit (e.g. a tank alien) -- give it a
                    # visible reaction, shoved along the bullet's own
                    # direction of travel, instead of silently no-selling
                    # the damage until the hit that finally kills it.
                    alien.stagger(bullet.dx, bullet.dy)
                    self.audio.play('hit_stagger')

            if bullet.piercing:
                bullet.pierces_left -= len(hit_aliens)
                if bullet.pierces_left <= 0:
                    self.bullets.remove(bullet)
            else:
                self.bullets.remove(bullet)

        if points_earned:
            self.stats.score += int(points_earned)
            self.sb.prep_score()
            self.sb.check_high_score()

        if not self.aliens:
            # Destroy existing bullets and create new fleet.
            self.bullets.clear()
            self._create_fleet()
            self.settings.increase_speed()

            # Increase level.
            self.stats.level += 1
            self.sb.prep_level()

    def _create_fleet(self):
        """Create the fleet of aliens using a randomly chosen formation."""
        # Create an alien and find the number of aliens in a row.
        # Spacing between each alien is equal to one alien width.
        alien = Alien(self)
        alien_width, alien_height = alien.width, alien.height
        available_space_x = self.settings.screen_width - (2 * alien_width)
        number_aliens_x = int(available_space_x // (2 * alien_width))

        # Determine the number of rows of aliens that fit on the screen.
        ship_height = self.ship.height
        available_space_y = (self.settings.screen_height -
                                (3 * alien_height) - ship_height)
        number_rows = int(available_space_y // (2 * alien_height))

        # Pick a formation shape and create an alien at each of its cells.
        cells, formation_name = random_formation(number_aliens_x, number_rows)
        self.fleet_formation = formation_name
        for alien_number, row_number in cells:
            self._create_alien(alien_number, row_number, alien_width,
                alien_height)

        # Give the player a moment before the first dive attack starts.
        self.dive_cooldown = 120

    def _create_alien(self, alien_number, row_number, grid_width, grid_height):
        """Create an alien and place it in the formation, with slight
        random jitter so aliens aren't perfectly grid-aligned.

        grid_width/grid_height are the base (unscaled) alien size used to
        space out the grid, so bigger/smaller alien types still line up
        on the same cells instead of drifting based on their own size.

        Positions are tracked in the same "distance from the top of the
        screen" terms the pygame version used (see alien.py) so this grid
        math didn't need to change for arcade's flipped y-axis.
        """
        alien_types = self.settings.alien_types
        alien_type = random.choices(
            list(alien_types.keys()),
            weights=[t.weight for t in alien_types.values()],
        )[0]
        alien = Alien(self, alien_type=alien_type)

        jitter_x = random.randint(-int(grid_width) // 4, int(grid_width) // 4)
        jitter_y = random.randint(-int(grid_height) // 4, int(grid_height) // 4)

        x = (grid_width + 2 * grid_width * alien_number) + jitter_x
        dist_from_top = (grid_height + 2 * grid_height * row_number) + jitter_y
        alien.place(x, dist_from_top)
        self.aliens.append(alien)

    def _update_aliens(self, dt):
        """Check if the fleet is at an edge, then update alien positions."""
        self._check_fleet_edges()
        self.aliens.update(dt)
        self._maybe_start_dive(dt)

        # Look for alien-ship collisions.
        colliding_aliens = arcade.check_for_collision_with_list(
            self.ship, self.aliens)
        if colliding_aliens:
            self._ship_hit(colliding_aliens[0])

        # Look for aliens hitting the bottom of the screen.
        self._check_aliens_bottom()

    def _maybe_start_dive(self, dt):
        """Occasionally send a random alien diving toward the ship."""
        self.dive_cooldown -= dt
        if self.dive_cooldown > 0:
            return

        diving_count = sum(1 for alien in self.aliens if alien.diving)
        if diving_count >= self.settings.max_concurrent_dives:
            self.dive_cooldown = 15  # check again soon
            return

        candidates = [alien for alien in self.aliens if not alien.diving]
        if candidates:
            diver = random.choice(candidates)
            diver.start_dive(self.ship.center_x)

        self.dive_cooldown = random.randint(*self.settings.dive_cooldown_range)

    def _ship_hit(self, source=None):
        """Respond to the ship being hit. source is the alien that hit
        it, when there is one -- the fleet reaching the bottom of the
        screen counts the same way, but has no single alien to point to."""
        self._apply_ship_knockback(source)
        self.particles.spawn_explosion(self.ship.center_x,
            self.ship.center_y, (255, 210, 90), count=55,
            speed_range=(2, 8), lifespan_range=(25, 50), radius_range=(3, 7))
        self.lighting.spawn_ship_explosion(self.ship.center_x,
            self.ship.center_y, (255, 210, 90))
        self.audio.play('explosion_ship')
        # Metallic gray hull fragments, distinct from the warm particle
        # burst above and from any alien's own tinted debris.
        self.physics.spawn_debris(self.ship.center_x,
            self.ship.center_y, (190, 195, 205), count=8)

        if self.stats.ships_left > 0:
            # Decrement ships_left, and update scoreboard.
            self.stats.ships_left -= 1
            self.sb.prep_ships()

            self._start_fresh_fleet()

            # Pause. Blocks the event loop for half a second, same as
            # the pygame version's time.sleep(0.5) -- a deliberate
            # freeze-frame beat on death, not a smooth animation.
            time.sleep(0.5)
        else:
            self.state = GameState.GAME_OVER
            self.set_mouse_visible(True)

    def _apply_ship_knockback(self, source):
        """Shove the ship's physics body away from whatever hit it, so a
        hit has a tangible physical reaction instead of the ship just
        staying put. Decays back to normal control through the same
        drag applied every frame in Ship.update()."""
        if source is not None and source.center_x != self.ship.center_x:
            direction = 1 if self.ship.center_x > source.center_x else -1
        else:
            direction = random.choice((-1, 1))

        knockback_speed = self.settings.ship_speed * 2.5
        _, vy = self.ship.body.velocity
        self.ship.body.velocity = (direction * knockback_speed, vy)

    def _start_fresh_fleet(self):
        """Clear the board and start a new fleet, with the ship centered."""
        self.aliens.clear()
        self.bullets.clear()
        self._create_fleet()
        self.ship.center_ship()

    def _check_aliens_bottom(self):
        """Check if any aliens have reached the bottom of the screen.

        Diving aliens are expected to reach the bottom (they despawn on
        their own in Alien._sync_sprite_position) and shouldn't count as
        the fleet breaking through -- only the formation itself reaching
        the ship's row should end the round.
        """
        for alien in self.aliens:
            if alien.diving:
                continue
            if alien.bottom <= 0:
                # Treat this the same as if the ship got hit.
                self._ship_hit()
                break

    def _check_fleet_edges(self):
        """Respond appropriately if any (non-diving) alien hits an edge."""
        for alien in self.aliens:
            if alien.diving:
                continue
            if alien.check_edges():
                self._change_fleet_direction()
                break

    def _change_fleet_direction(self):
        """Drop the formation and change the fleet's direction."""
        for alien in self.aliens:
            if not alien.diving:
                alien.drop(self.settings.fleet_drop_speed)
        self.settings.fleet_direction *= -1

    def _draw_game_over(self):
        """Render a game-over headline and final score above the button."""
        heading_bottom = self.play_button.top + 40
        self.game_over_heading.y = heading_bottom

        self.game_over_score.text = f"Final Score: {self.stats.score:,}"
        self.game_over_score.y = heading_bottom - 10

        self.game_over_heading.draw()
        self.game_over_score.draw()


def main():
    AlienInvasion()
    arcade.run()


if __name__ == '__main__':
    main()
