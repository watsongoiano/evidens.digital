import os
import sys
from PIL import Image

"""
Generate favicon.ico files from a PNG source for both locations:
- repo/favicon.ico
- repo/src/static/favicon.ico

Usage (Windows PowerShell):
    # Use default discovery (assets/new_logo or src/static/new_logo)
    python scripts/generate_favicon.py

    # Or pass a specific image path
    python scripts/generate_favicon.py assets/favicon_source.png

Requirements: Pillow (pip install Pillow)
"""

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PNG_PATHS = [
    # Preferred: explicit asset dropped by user
    os.path.join(ROOT, 'assets', 'favicon_source.png'),
    # Fallbacks
    os.path.join(ROOT, 'new_logo.png'),
    os.path.join(ROOT, 'src', 'static', 'new_logo.png'),
]
OUTPUTS = [
    os.path.join(ROOT, 'favicon.ico'),
    os.path.join(ROOT, 'src', 'static', 'favicon.ico'),
]

# Common ICO sizes; browsers pick the best match
ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

def find_logo_png() -> str:
    for p in PNG_PATHS:
        if os.path.exists(p):
            return p
    raise FileNotFoundError('Source PNG not found. Tried: assets/favicon_source.png, new_logo.png (root), src/static/new_logo.png')


def ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def generate_favicon(src_png: str, out_path: str):
    with Image.open(src_png) as im:
        # Convert to RGBA to preserve transparency, then to ICO
        im = im.convert('RGBA')
        # If image is not square, pad to square with transparent background
        w, h = im.size
        if w != h:
            size = max(w, h)
            bg = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            bg.paste(im, ((size - w) // 2, (size - h) // 2))
            im = bg
        # Save ICO with multiple sizes
        ensure_dir(out_path)
        im.save(out_path, format='ICO', sizes=ICO_SIZES)
        print(f'Wrote {out_path}')


def main():
    # Optional CLI arg: source image path
    if len(sys.argv) > 1:
        candidate = sys.argv[1]
        if not os.path.isabs(candidate):
            candidate = os.path.abspath(os.path.join(ROOT, candidate))
        if not os.path.exists(candidate):
            raise FileNotFoundError(f'Source image not found: {candidate}')
        src = candidate
    else:
        src = find_logo_png()
    for out in OUTPUTS:
        generate_favicon(src, out)


if __name__ == '__main__':
    main()
