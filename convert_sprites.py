"""One-time conversion of images/*.bmp -> images/*.png with real alpha
transparency.

The original .bmp sprites were made against the game's old light-gray
background (230, 230, 230) baked directly into the pixels -- BMP has no
transparency, so that only worked because the game's own fill color
matched exactly. Now that the background is a starfield instead of a
flat fill, that baked-in gray would show up as an ugly box around each
sprite.

This keys out that background color, with a short distance-based
feather so anti-aliased edge pixels fade out smoothly instead of
leaving a hard gray fringe. Run again if you replace either .bmp.

Usage: python convert_sprites.py
"""

import math
from pathlib import Path

from PIL import Image

IMAGE_DIR = Path(__file__).resolve().parent / 'images'
BG = (230, 230, 230)
FULLY_TRANSPARENT_BELOW = 8   # distance from BG at/under which alpha = 0
FULLY_OPAQUE_ABOVE = 45       # distance from BG at/over which alpha = 255


def convert(name):
    src = IMAGE_DIR / f'{name}.bmp'
    dst = IMAGE_DIR / f'{name}.png'

    img = Image.open(src).convert('RGBA')
    pixels = img.load()
    width, height = img.size

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            dist = math.sqrt(
                (r - BG[0]) ** 2 + (g - BG[1]) ** 2 + (b - BG[2]) ** 2)
            if dist <= FULLY_TRANSPARENT_BELOW:
                alpha = 0
            elif dist >= FULLY_OPAQUE_ABOVE:
                alpha = 255
            else:
                span = FULLY_OPAQUE_ABOVE - FULLY_TRANSPARENT_BELOW
                alpha = int(255 * (dist - FULLY_TRANSPARENT_BELOW) / span)
            pixels[x, y] = (r, g, b, alpha)

    img.save(dst)
    print(f'wrote {dst}')


def main():
    convert('ship')
    convert('alien')


if __name__ == '__main__':
    main()
