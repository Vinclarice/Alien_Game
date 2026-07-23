"""One-time generator for Alien Invasion's sound effects.

There's no licensed audio in this project, so these are simple
synthesized retro SFX -- frequency sweeps and enveloped noise bursts --
built with nothing but the standard library (wave/math/random/struct).
No extra dependency, no licensing question.

Run this again after tweaking the parameters below to regenerate
sounds/*.wav, or just drop your own same-named WAV file into sounds/ to
replace any one of them with something higher-fidelity later -- audio.py
doesn't care how a file was made, only its name.

Usage: python generate_sounds.py
"""

import math
import random
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 44100
OUT_DIR = Path(__file__).resolve().parent / 'sounds'


def _envelope(i, n, attack=0.02, release=0.7):
    """Amplitude multiplier (0..1): a quick linear attack, then a decay
    whose steepness is controlled by release (smaller = snappier)."""
    t = i / n
    if t < attack:
        return t / attack
    release_t = (t - attack) / max(1e-9, 1 - attack)
    return max(0.0, (1 - release_t) ** (1 / max(release, 0.001)))


def sweep(duration, f_start, f_end, shape='sine', volume=0.5):
    """A tone that slides from f_start to f_end Hz -- the classic
    laser/"pew" sound is just a fast downward sine sweep."""
    n = int(SAMPLE_RATE * duration)
    samples = []
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = f_start + (f_end - f_start) * t
        phase += freq / SAMPLE_RATE
        if shape == 'square':
            val = 1.0 if (phase % 1.0) < 0.5 else -1.0
        else:
            val = math.sin(2 * math.pi * phase)
        samples.append(val * volume * _envelope(i, n))
    return samples


def noise_burst(duration, volume=0.6, low_rumble=True):
    """White noise with a fast decay -- an explosion. Mixing in a low
    sine underneath gives it some weight instead of sounding like static."""
    n = int(SAMPLE_RATE * duration)
    samples = []
    phase = 0.0
    rumble_freq = 90
    for i in range(n):
        env = _envelope(i, n, attack=0.005, release=0.5)
        s = random.uniform(-1, 1) * 0.6
        if low_rumble:
            phase += rumble_freq / SAMPLE_RATE
            s += math.sin(2 * math.pi * phase) * 0.5
        samples.append(s * volume * env)
    return samples


def blip(freqs, duration=0.12, volume=0.4):
    """A quick ascending chirp through a few notes -- UI feedback."""
    samples = []
    per_note = duration / len(freqs)
    n = int(SAMPLE_RATE * per_note)
    for f in freqs:
        for i in range(n):
            samples.append(math.sin(2 * math.pi * f * i / SAMPLE_RATE)
                * volume * _envelope(i, n, attack=0.05, release=0.6))
    return samples


def _write_wav(name, samples):
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / f'{name}.wav'
    with wave.open(str(path), 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        frames = b''.join(
            struct.pack('<h', max(-32767, min(32767, int(s * 32767))))
            for s in samples)
        f.writeframes(frames)
    print(f'wrote {path}')


def main():
    _write_wav('laser_single', sweep(0.14, 1300, 500, 'sine', volume=0.5))
    _write_wav('laser_spread', sweep(0.10, 1600, 800, 'sine', volume=0.4))
    _write_wav('laser_heavy', sweep(0.22, 550, 120, 'square', volume=0.6))
    _write_wav('explosion_alien', noise_burst(0.30, volume=0.55))
    _write_wav('explosion_ship', noise_burst(0.60, volume=0.7))
    _write_wav('hit_stagger', noise_burst(0.08, volume=0.4, low_rumble=False))
    _write_wav('ui_select', blip([500, 750, 1000]))


if __name__ == '__main__':
    main()
