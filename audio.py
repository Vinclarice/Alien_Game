"""Sound effects for Alien Invasion, via pygame.mixer.

Every effect referenced here is a short WAV file in sounds/ (see
generate_sounds.py for how they were made). AudioManager loads them all
once up front and exposes a single play(name) call for the rest of the
game to use -- callers don't touch pygame.mixer directly.

If the mixer can't initialize (no audio device on this machine, audio
disabled, etc.), every play() call silently no-ops instead of crashing
the game -- sound is a nice-to-have, not something gameplay depends on.
"""

from pathlib import Path

import pygame

SOUND_DIR = Path(__file__).resolve().parent / 'sounds'

# One entry per named effect the game plays. Add a new event by adding
# its name here and calling audio.play('that_name') where it happens.
SOUND_NAMES = (
    'laser_single', 'laser_spread', 'laser_heavy',
    'explosion_alien', 'explosion_ship', 'hit_stagger', 'ui_select',
)


class AudioManager:
    """Loads every sound effect once and plays them by name."""

    def __init__(self, volume=0.6):
        self.enabled = self._init_mixer()
        self.sounds = {}
        if self.enabled:
            self._load_sounds(volume)

    def _init_mixer(self):
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=1)
            return True
        except pygame.error:
            # No audio device, driver issue, etc. -- play() becomes a
            # no-op rather than taking down the game over sound.
            return False

    def _load_sounds(self, volume):
        for name in SOUND_NAMES:
            path = SOUND_DIR / f'{name}.wav'
            try:
                sound = pygame.mixer.Sound(str(path))
                sound.set_volume(volume)
                self.sounds[name] = sound
            except (pygame.error, FileNotFoundError):
                pass  # missing/broken file -- that one event stays silent

    def play(self, name):
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()
