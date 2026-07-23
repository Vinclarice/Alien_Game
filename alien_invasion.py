import sys
import random
from time import sleep

import pygame
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

class AlienInvasion:
    """Overall class to manage game assets and behavior."""

    def __init__(self):
        """Initialize the game, and create game resources."""
        pygame.init()
        self.clock = pygame.time.Clock()
        self.settings = Settings()
        self.stats = GameStats(self)

        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.settings.screen_width = self.screen.get_rect().width
        self.settings.screen_height = self.screen.get_rect().height
        pygame.display.set_caption("Alien Invasion")

        # Set the background color.
        self.bg_color = self.settings.bg_color
        self.starfield = Starfield(
            self.settings.screen_width, self.settings.screen_height)

        self.audio = AudioManager(self.settings.sfx_volume)

        # Physics (ship momentum/knockback, debris) -- created before the
        # ship, since Ship.__init__ needs it to build its physics body.
        self.physics = PhysicsWorld(
            self.settings.screen_width, self.settings.screen_height)

        self.ship = Ship(self)
        self.bullets = pygame.sprite.Group()
        self.aliens = pygame.sprite.Group()
        self.particles = ParticleSystem(self.screen)

        self._create_fleet()

        # The weapon currently in use; switch with the 1/2/3 keys.
        self.current_weapon = 'single'

        # Create the scoreboard.
        self.sb = Scoreboard(self)

        # Start Alien Invasion at the main menu.
        self.state = GameState.MENU

        # Make the Play button and the game-over headline fonts.
        self.play_button = Button(self, "Play")
        self.game_over_font = pygame.font.SysFont(None, 64)
        self.game_over_sub_font = pygame.font.SysFont(None, 36)

    def run_game(self):
        """Start the main loop for the game."""
        while True:
            dt = self._tick()
            self._check_events()

            if self.state == GameState.PLAYING:
                self.ship.update(dt)
                self._update_bullets(dt)
                self._update_aliens(dt)
                self._emit_engine_trail()

            # Physics (ship momentum/wall collision, debris tumbling) and
            # particles keep advancing even off PLAYING, so a knockback
            # or explosion already in progress finishes playing out on
            # the menu/game-over screen instead of freezing mid-animation.
            self.physics.step(dt)
            self.ship.sync_from_body()
            self.particles.update(dt)
            self.starfield.update(dt)  # drifts on the menu too, not just PLAYING

            self.update_screen()

    def _tick(self):
        """Advance the clock and return a normalized delta-time factor.

        1.0 means "exactly one frame at 60fps" elapsed, so the existing
        speed constants (tuned assuming 60fps) still feel the same, but
        movement now scales with actual elapsed time instead of assuming
        a fixed frame rate. Clamped so a stall (e.g. dragging the window)
        can't fling everything across the screen in one jump.
        """
        elapsed_ms = self.clock.tick(60)  # also caps the frame rate at 60
        dt = elapsed_ms / (1000 / 60)
        return min(dt, 3.0)

    def _quit_game(self):
        """Shut pygame down cleanly and exit."""
        pygame.quit()
        sys.exit()

    def _check_events(self):
        """Respond to keypresses and mouse events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit_game()
            elif event.type == pygame.KEYDOWN:
                self._check_keydown_events(event)
            elif event.type == pygame.KEYUP:
                self._check_keyup_events(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                self._check_play_button(mouse_pos)

    def _check_play_button(self, mouse_pos):
        """Start a new game when the player clicks Play."""
        button_clicked = self.play_button.rect.collidepoint(mouse_pos)
        if button_clicked and self.state != GameState.PLAYING:
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
        pygame.mouse.set_visible(False)

    def _check_keydown_events(self, event):
        """Respond to keypresses."""
        if event.key == pygame.K_RIGHT:
            self.ship.moving_right = True
        elif event.key == pygame.K_LEFT:
            self.ship.moving_left = True
        elif event.key == pygame.K_q:
            self._quit_game()
        elif event.key == pygame.K_p and self.state != GameState.PLAYING:
            self._start_game()
        elif self.state == GameState.PLAYING and event.key == pygame.K_SPACE:
            self._fire_bullet()
        elif self.state == GameState.PLAYING and event.key == pygame.K_1:
            self.current_weapon = 'single'
            self.sb.prep_weapon()
        elif self.state == GameState.PLAYING and event.key == pygame.K_2:
            self.current_weapon = 'spread'
            self.sb.prep_weapon()
        elif self.state == GameState.PLAYING and event.key == pygame.K_3:
            self.current_weapon = 'heavy'
            self.sb.prep_weapon()

    def _check_keyup_events(self, event):
        """Respond to key releases."""
        if event.key == pygame.K_RIGHT:
            self.ship.moving_right = False
        elif event.key == pygame.K_LEFT:
            self.ship.moving_left = False

    def _emit_engine_trail(self):
        """Release one puff of exhaust behind the ship this frame; called
        every frame while playing so the puffs build into a trail."""
        x = self.ship.rect.centerx + random.uniform(-4, 4)
        y = self.ship.rect.bottom - 4
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
            self.bullets.add(new_bullet)

        # One flash/sound per trigger pull, regardless of how many
        # bullets that shot fires.
        gun_x, gun_y = self.ship.rect.midtop
        self.particles.spawn_muzzle_flash(gun_x, gun_y, weapon.color)
        self.audio.play(f'laser_{self.current_weapon}')

    def _update_bullets(self, dt):
        """Update position of bullets and get rid of old bullets."""
        self.bullets.update(dt)

        # Get rid of bullets that have disappeared off any edge of the
        # screen (spread shots can drift off the sides, not just the top).
        for bullet in self.bullets.copy():
            if (bullet.rect.bottom <= 0 or bullet.rect.right <= 0 or
                    bullet.rect.left >= self.settings.screen_width):
                self.bullets.remove(bullet)

        self._check_bullet_alien_collisions()

    def _check_bullet_alien_collisions(self):
        """Respond to bullet-alien collisions."""
        # Check each bullet against the fleet individually, since piercing
        # bullets need to survive a hit, and tougher aliens can survive
        # one too -- neither is destroyed automatically on contact.
        points_earned = 0
        for bullet in self.bullets.copy():
            hit_aliens = pygame.sprite.spritecollide(bullet, self.aliens, False)
            if not hit_aliens:
                continue

            for alien in hit_aliens:
                if alien.take_hit():
                    points_earned += self.settings.alien_points * alien.points_multiplier
                    self.particles.spawn_explosion(alien.rect.centerx,
                        alien.rect.centery, alien.explosion_color)
                    self.physics.spawn_debris(alien.rect.centerx,
                        alien.rect.centery, alien.explosion_color)
                    self.audio.play('explosion_alien')
                    self.aliens.remove(alien)
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
            self.bullets.empty()
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
        alien_width, alien_height = alien.rect.size
        available_space_x = self.settings.screen_width - (2 * alien_width)
        number_aliens_x = available_space_x // (2 * alien_width)

        # Determine the number of rows of aliens that fit on the screen.
        ship_height = self.ship.rect.height
        available_space_y = (self.settings.screen_height -
                                (3 * alien_height) - ship_height)
        number_rows = available_space_y // (2 * alien_height)

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
        """
        alien_types = self.settings.alien_types
        alien_type = random.choices(
            list(alien_types.keys()),
            weights=[t.weight for t in alien_types.values()],
        )[0]
        alien = Alien(self, alien_type=alien_type)

        jitter_x = random.randint(-grid_width // 4, grid_width // 4)
        jitter_y = random.randint(-grid_height // 4, grid_height // 4)

        alien.x = (grid_width + 2 * grid_width * alien_number) + jitter_x
        alien.rect.x = alien.x
        alien.rect.y = (grid_height +
            2 * grid_height * row_number) + jitter_y
        self.aliens.add(alien)

    def _update_aliens(self, dt):
        """Check if the fleet is at an edge, then update alien positions."""
        self._check_fleet_edges()
        self.aliens.update(dt)
        self._maybe_start_dive(dt)

        # Look for alien-ship collisions.
        colliding_alien = pygame.sprite.spritecollideany(self.ship, self.aliens)
        if colliding_alien:
            self._ship_hit(colliding_alien)

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
            diver.start_dive(self.ship.rect.centerx)

        self.dive_cooldown = random.randint(*self.settings.dive_cooldown_range)

    def _ship_hit(self, source=None):
        """Respond to the ship being hit. source is the alien that hit
        it, when there is one -- the fleet reaching the bottom of the
        screen counts the same way, but has no single alien to point to."""
        self._apply_ship_knockback(source)
        self.particles.spawn_explosion(self.ship.rect.centerx,
            self.ship.rect.centery, (255, 210, 90), count=55,
            speed_range=(2, 8), lifespan_range=(25, 50), radius_range=(3, 7))
        self.audio.play('explosion_ship')
        # Metallic gray hull fragments, distinct from the warm particle
        # burst above and from any alien's own tinted debris.
        self.physics.spawn_debris(self.ship.rect.centerx,
            self.ship.rect.centery, (190, 195, 205), count=8)

        if self.stats.ships_left > 0:
            # Decrement ships_left, and update scoreboard.
            self.stats.ships_left -= 1
            self.sb.prep_ships()

            self._start_fresh_fleet()

            # Pause.
            sleep(0.5)
        else:
            self.state = GameState.GAME_OVER
            pygame.mouse.set_visible(True)

    def _apply_ship_knockback(self, source):
        """Shove the ship's physics body away from whatever hit it, so a
        hit has a tangible physical reaction instead of the ship just
        staying put. Decays back to normal control through the same
        drag applied every frame in Ship.update()."""
        if source is not None and source.rect.centerx != self.ship.rect.centerx:
            direction = 1 if self.ship.rect.centerx > source.rect.centerx else -1
        else:
            direction = random.choice((-1, 1))

        knockback_speed = self.settings.ship_speed * 2.5
        _, vy = self.ship.body.velocity
        self.ship.body.velocity = (direction * knockback_speed, vy)

    def _start_fresh_fleet(self):
        """Clear the board and start a new fleet, with the ship centered."""
        self.aliens.empty()
        self.bullets.empty()
        self._create_fleet()
        self.ship.center_ship()

    def _check_aliens_bottom(self):
        """Check if any aliens have reached the bottom of the screen.

        Diving aliens are expected to reach the bottom (they despawn on
        their own in Alien._update_dive) and shouldn't count as the fleet
        breaking through -- only the formation itself reaching the ship's
        row should end the round.
        """
        screen_rect = self.screen.get_rect()
        for alien in self.aliens.sprites():
            if alien.diving:
                continue
            if alien.rect.bottom >= screen_rect.bottom:
                # Treat this the same as if the ship got hit.
                self._ship_hit()
                break

    def _check_fleet_edges(self):
        """Respond appropriately if any (non-diving) alien hits an edge."""
        for alien in self.aliens.sprites():
            if alien.diving:
                continue
            if alien.check_edges():
                self._change_fleet_direction()
                break

    def _change_fleet_direction(self):
        """Drop the formation and change the fleet's direction."""
        for alien in self.aliens.sprites():
            if not alien.diving:
                alien.rect.y += self.settings.fleet_drop_speed
        self.settings.fleet_direction *= -1

    def update_screen(self):
        """Update images on the screen, and flip to the new screen."""
        self.screen.fill(self.settings.bg_color)
        self.starfield.draw(self.screen)
        for bullet in self.bullets.sprites():
            bullet.draw_bullet()
        self.ship.blitme()
        self.aliens.draw(self.screen)
        self.physics.draw_debris(self.screen)
        self.particles.draw()

        # Draw the score information.
        self.sb.show_score()

        # Draw the play button whenever the game isn't actively running.
        if self.state != GameState.PLAYING:
            self.play_button.draw_button()

        # On top of that, show a game-over headline and final score.
        if self.state == GameState.GAME_OVER:
            self._draw_game_over()

        pygame.display.flip()

    def _draw_game_over(self):
        """Render a game-over headline and final score above the button."""
        # Brighter red/off-white than before -- the old (150,20,20) and
        # (30,30,30) were tuned for the game's old light-gray background
        # and would barely register against the dark starfield now.
        heading = self.game_over_font.render("GAME OVER", True, (255, 70, 70))
        heading_rect = heading.get_rect()
        heading_rect.centerx = self.screen.get_rect().centerx
        heading_rect.bottom = self.play_button.rect.top - 40

        score_str = f"Final Score: {self.stats.score:,}"
        score_image = self.game_over_sub_font.render(score_str, True,
            (220, 225, 235))
        score_rect = score_image.get_rect()
        score_rect.centerx = heading_rect.centerx
        score_rect.top = heading_rect.bottom + 10

        self.screen.blit(heading, heading_rect)
        self.screen.blit(score_image, score_rect)


if __name__ == '__main__':
    # Make a game instance, and run the game.
    ai = AlienInvasion()
    ai.run_game()
