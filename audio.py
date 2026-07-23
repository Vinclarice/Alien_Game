"""Sound effects for Alien Invasion, via arcade's sound API (pyglet under
the hood).

Every effect referenced here is a short WAV file in sounds/ (see
generate_sounds.py for how they were made). AudioManager loads them all
once up front and exposes a single play(name) call for the rest of the
game to use -- callers don't touch arcade.play_sound directly.

If a sound device can't be reached (no audio device on this machine,
driver issue, etc.), every play() call silently no-ops instead of
crashing the game -- sound is a nice-to-have, not something gameplay
depends on.
"""

from pathlib import Path

import arcade

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
        self.volume = volume
        self.sounds = self._load_sounds()

    def _load_sounds(self):
        sounds = {}
        for name in SOUND_NAMES:
            path = SOUND_DIR / f'{name}.wav'
            try:
                sounds[name] = arcade.load_sound(path)
            except Exception:
                pass  # missing/broken file, or no audio device -- stay silent
        return sounds

    def play(self, name):
        sound = self.sounds.get(name)
        if sound is None:
            return
        try:
            arcade.play_sound(sound, volume=self.volume)
        except Exception:
            pass
