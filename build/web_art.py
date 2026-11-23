"""Pack printable campaign art into the small textures used by the shared board."""
import math
import random
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from art import mix, sprite
from maps import OUT, fields
from party import heroes
from world import pal

DEST = Path(__file__).resolve().parents[1] / "site/static/assets"
W, H = 1200, 750
LAYOUTS = [
    [(13, 72), (41, 72), (71, 70), (46, 30), (16, 28), (78, 30)],
    [(12, 52), (31, 52), (50, 77), (50, 29), (71, 52), (89, 52)],
    [(15, 53), (46, 53), (29, 78), (29, 27), (72, 76), (81, 30)],
]


def point(x, y):
    return round(W * x / 100), round(H * (1 - y / 100))


def field(index, slug):
    rng = random.Random(4915 + index)
    tones = [
        ("#c0baa0", "#4e878b", "#829777", "#667a62"),
        ("#a4a599", "#477e83", "#94998a", "#757b71"),
        ("#cec298", "#bba476", "#ada97e", "#8f9470"),
    ]
    ground, water, hill, ink = tones[index]
    image = Image.new("RGB", (W, H), ground)
    draw = ImageDraw.Draw(image)
    for line in range(-8, 64):
        y = line * 16
        points = [(x, y + 17 * math.sin(x / 106 + line * .09)
                   + 14 * math.sin(x / 175 - line * .21)) for x in range(-20, W + 21, 12)]
        draw.line(points, mix(hill, ground, .45), 1)
    if index == 0:
        shore = [(0, 465), (75, 441), (167, 482), (269, 486), (385, 428),
                 (515, 357), (643, 322), (765, 319), (908, 345), (1025, 286), (1200, 219)]
        draw.polygon(shore + [(W, H), (0, H)], fill=water)
        for offset, color in [(17, "#abc1aa"), (8, "#d2d1af"), (2, "#626f5a")]:
            draw.line([(x, y + offset) for x, y in shore], fill=color, width=3)
        for _ in range(1550):
            x, y = rng.randrange(W), rng.randrange(H)
            if image.getpixel((x, y)) == (78, 135, 139):
                draw.arc((x, y, x + rng.randint(6, 31), y + 4), 10, 175, "#78a2a1")
        for sx, sy in [(120, 85), (350, 155), (310, 355), (970, 130), (1060, 220)]:
            for _ in range(22):
                x, y = rng.gauss(sx, 27), rng.gauss(sy, 16)
                s = rng.uniform(6, 20)
                draw.ellipse((x - s, y - s, x + s, y + s * .65), fill=hill, outline=ink)
                draw.arc((x - s * .6, y - s * .45, x + s * .6, y + s * .6), 50, 150, ink)
    elif index == 1:
        for _ in range(115):
            x, y = rng.randrange(W), rng.randrange(H)
            s = rng.randrange(8, 44)
            draw.line([(x - s, y + s * .25), (x, y - s * .43), (x + s * .3, y - s * .1),
                       (x + s * .8, y - s * .2)], fill=ink, width=2)
        x, y = point(71, 52)
        for s, color in [(113, ink), (108, "#bfd0b6"), (100, water)]:
            draw.ellipse((x - s, y - s * .65, x + s, y + s * .65), fill=color)
    else:
        for x in range(30, 1060, 45):
            y = 48 + (x % 97)
            for j in range(6):
                draw.line((x + j * 4, y, x + j * 4 - 14, y + 38), fill="#9b986a", width=2)
        for y1, y2 in [(0, 286), (420, 750)]:
            draw.line((553, y1, 553, y2), fill=ink, width=27)
            for y in range(y1, y2, 14):
                draw.rectangle((542, y, 560, y + 10), fill="#d4c2a1", outline=ink)
    for _ in range(18000):
        x, y = rng.randrange(W), rng.randrange(H)
        r, g, b = image.getpixel((x, y))
        delta = rng.choice((-10, -6, 4, 8))
        draw.line((x, y, x + rng.choice((1, 2, 3)), y), fill=tuple(max(0, min(255, c + delta)) for c in (r, g, b)))
    zones = [point(x, y) for x, y in LAYOUTS[index]]
    for a, b in fields[index][2]:
        pair = [zones[a - 1], zones[b - 1]]
        draw.line(pair, fill="#655e4e", width=15)
        draw.line(pair, fill="#d3bc92", width=10)
        (x, y), (xx, yy) = pair
        steps = max(1, round(math.dist(*pair) / 15))
        for j in range(steps):
            draw.line([(x + (xx - x) * t, y + (yy - y) * t) for t in (j / steps, (j + .40) / steps)],
                      fill="#928567", width=2)
    for x, y in zones:
        draw.ellipse((x - 65, y - 48, x + 65, y + 48), fill="#d2c7a5", outline=ink, width=2)
        draw.ellipse((x - 60, y - 43, x + 60, y + 43), outline="#a09778", width=1)
    draw.rectangle((5, 5, W - 6, H - 6), outline="#5b7062", width=2)
    image.save(DEST / (slug + ".webp"), quality=83, method=6)


def main():
    portraits = DEST / "portraits"
    portraits.mkdir(exist_ok=True, parents=True)
    atlas = Image.open(OUT / "Карта мира.png").convert("RGB")
    atlas.crop((54, 184, 1956, 1225)).save(DEST / "atlas.webp", quality=88, method=6)
    for i in range(len(heroes)):
        school = i // 3
        color = pal[school]
        paper = mix(color, "#eee6ca", .76)
        portrait = Image.new("RGB", (240, 240), paper)
        d = ImageDraw.Draw(portrait)
        for r in (45, 74, 103, 109):
            d.ellipse((120-r, 126-r, 120+r, 126+r), outline=mix(color, paper, .58))
        fig = sprite("hero" + str(school), i, school)
        fig = fig.crop(fig.getchannel("A").getbbox())
        fig.thumbnail((48, 47), Image.Resampling.NEAREST)
        fig = fig.resize((fig.width * 4, fig.height * 4), Image.Resampling.NEAREST)
        portrait.paste(fig, ((240 - fig.width)//2, (240 - fig.height)//2), fig)
        portrait.save(portraits / f"H{i+1:02}.webp", lossless=True)
    for index, slug in enumerate(("bell", "dungeon", "siege")):
        field(index, slug)
    scenery = DEST / "terrain"
    scenery.mkdir(exist_ok=True)
    for name in ("house", "forest", "cavern", "gate", "bombard", "catapult"):
        shutil.copyfile(OUT / "3D" / "местность" / (name + ".stl"), scenery / (name + ".stl"))


if __name__ == "__main__":
    main()
