"""Registered, unlabelled watercolor used by both the online and printed atlas.

The painted source follows the original terrain guide. Its full frame maps to
x=0..100 west to east, y=0..100 north to south; never crop it to fit a viewport.
The tiny rescale restores the exact aspect of the 1902 × 1041 printed plot.
"""
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "build/artwork/atlas-ink.png"
FIELD_SIZE = (1902, 1041)
DEST = ROOT / "site/static/assets/atlas.webp"


def atlas_image():
    with Image.open(MASTER) as art:
        return art.convert("RGB").resize(FIELD_SIZE, Image.Resampling.LANCZOS)


def main():
    DEST.parent.mkdir(parents=True, exist_ok=True)
    atlas_image().save(DEST, quality=94, method=6)


if __name__ == "__main__":
    main()
