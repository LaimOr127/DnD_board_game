"""Extract the canonical WebPs from local, row-major two-row illustration sheets.

Usage: python build/card_plates.py qa-temp/ink-sheet-sources.json
The JSON maps a zero-based sheet key (for example H0 or M29) to a local PNG.
To apply a two-figure replacement sheet last, use its keyed pair of card IDs,
for example M166+M205 in left-to-right order.
Individual images keep the original paint and resolution. The figure bounding
boxes set the margins, so a long spear or a wide skirt still fits on the card.
"""
import argparse
import json
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from PIL import Image, ImageFilter


ASSETS = Path(__file__).resolve().parents[1] / "site/static/assets"
LIMITS = {"H": 3, "I": 4, "B": 10, "M": 30}


def gutter(ink, center, radius):
    """Trace the lightest continuous gutter between two illustrated silhouettes."""
    left = max(0, round(center - radius))
    right = min(ink.shape[1], round(center + radius) + 1)
    strip = ink[:, left:right]
    # Work at half size. Widen the ink slightly to keep its pale outer edges.
    cost = Image.fromarray(strip).resize(
        (max(2, strip.shape[1] // 2), max(2, strip.shape[0] // 2)), Image.Resampling.BOX)
    cost = np.asarray(cost.filter(ImageFilter.MaxFilter(3))).astype(np.float32)
    height, width = cost.shape
    offset = np.abs(np.arange(width) - (center-left)*width/(right-left))
    cost = np.maximum(cost - 7, 0) + offset * .035
    previous = cost[0].copy()
    directions = np.zeros((height, width), dtype=np.int8)
    columns = np.arange(width)
    for y in range(1, height):
        padded = np.pad(previous, 1, constant_values=np.inf)
        choices = np.stack((padded[:-2] + .8, previous, padded[2:] + .8))
        best = np.argmin(choices, axis=0)
        directions[y] = best - 1
        previous = cost[y] + choices[best, columns]
    path = np.empty(height, dtype=np.int32)
    x = int(np.argmin(previous))
    for y in reversed(range(height)):
        path[y] = x
        x += int(directions[y, x])
    ys = (np.arange(height) + .5) * strip.shape[0] / height - .5
    xs = (path + .5) * strip.shape[1] / width + left
    return np.rint(np.interp(np.arange(strip.shape[0]), ys, xs)).astype(np.int32)


def save_cell(rgb, ink, owner, background, output, square):
    yy, xx = np.where(owner & (ink > 32))
    if len(xx) < 200:
        raise ValueError(f"Нет рисунка для {output.stem}")
    pad = max(9, round(max(np.ptp(xx), np.ptp(yy)) * .032))
    x0, x1 = int(xx.min()), int(xx.max()+1)
    y0, y1 = int(yy.min()), int(yy.max()+1)
    width, height = x1-x0+2*pad, y1-y0+2*pad
    if square:
        width = height = max(width, height)
    area = Image.new("RGB", (width, height), background)
    left = x0-(width-(x1-x0))//2
    top = y0-(height-(y1-y0))//2
    box = (max(0,left), max(0,top), min(rgb.width,left+width), min(rgb.height,top+height))
    a,b,c,d = box
    mask = Image.fromarray(owner[b:d,a:c])
    area.paste(rgb.crop(box), (a-left,b-top), mask)
    # The companion and the print builder may read a card while it is rebuilt.
    with NamedTemporaryFile(dir=output.parent, suffix=".tmp", delete=False) as temp:
        temp_path = Path(temp.name)
    try:
        area.save(temp_path, format="WEBP", quality=95, method=5)
        temp_path.replace(output)
    finally:
        temp_path.unlink(missing_ok=True)


def ruled_interiors(gray, count):
    """Mob sheets have thin, straight printed rules; omit their antialiased edges."""
    length = gray.shape[1]
    cuts = []
    contrast = np.minimum(np.roll(gray,-6,axis=1),np.roll(gray,6,axis=1)) - gray
    for i in range(count+1):
        middle = min(length-1,round(length*i/count))
        start, end = max(0,middle-12), min(length,middle+13)
        # A printed rule persists across both rows even where the drawing touches it.
        score = np.quantile(contrast[:,start:end], .26, axis=0)
        cuts.append(start + int(np.argmax(score)) if score.max() > 5 else middle)
    return [(a+4,b-3) for a,b in zip(cuts,cuts[1:])]


def extract(key, source):
    pair = re.fullmatch(r"(M\d{3})\+(M\d{3})",key)
    if pair:
        if pair[1] == pair[2] or not all(1 <= int(k[1:]) <= 300 for k in pair.groups()):
            raise ValueError(f"Некорректная пара {key!r}")
        family, batch = "M", None
    else:
        match = re.fullmatch(r"([HIBM])(0|[1-9][0-9]?)", key)
        if not match or int(match[2]) >= LIMITS[match[1]]:
            raise ValueError(f"Неизвестный лист {key!r}")
        family, batch = match[1], int(match[2])
    cols = 3 if family == "H" else 5
    folder = ASSETS / ("portraits" if family == "H" else "cards")
    folder.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        if image.format != "PNG":
            raise ValueError(f"Ожидался исходный PNG для {key}")
        rgb = image.convert("RGB")
    pixels = np.asarray(rgb)
    edge = np.concatenate([pixels[0],pixels[-1],pixels[:,0],pixels[:,-1]])
    paper = np.median(edge, axis=0).astype(np.int16)
    if family == "M" and not pair:
        # The ruled outer frame is gray. Sample the actual ivory paper inside it.
        samples = pixels[::5,::5].reshape(-1,3)
        light = samples.mean(axis=1)
        paper = np.median(samples[light >= np.percentile(light,75)],axis=0).astype(np.int16)
    ink = np.abs(pixels.astype(np.int16)-paper).max(axis=2).astype(np.uint8)
    background = tuple(map(int,paper))
    height, width = ink.shape
    if pair:
        cut = gutter(ink,width/2,width*.14)
        left = np.arange(width)[None,:] < cut[:,None]
        for card_id, owner in zip(pair.groups(),(left,~left)):
            save_cell(rgb,ink,owner,background,folder/(card_id+".webp"),False)
        return
    if family == "M":
        gray = np.asarray(rgb.convert("L"),dtype=np.int16)
        rows, columns = ruled_interiors(gray.T, 2), ruled_interiors(gray, cols)
        for row, (top, bottom) in enumerate(rows):
            for col, (left, right) in enumerate(columns):
                box = (left,top,right,bottom)
                cell = ink[top:bottom,left:right]
                num = batch*10 + row*cols+col+1
                save_cell(rgb.crop(box),cell,np.ones_like(cell,dtype=bool),
                          background,folder/f"M{num:03}.webp",False)
        return
    xx, yy = np.arange(width)[None,:], np.arange(height)[:,None]
    middle = gutter(ink.T,height/2,height*.105)
    for row in range(2):
        row_mask = (yy < middle[None,:]) if row == 0 else (yy >= middle[None,:])
        top = 0 if row == 0 else int(middle.min())
        bottom = int(middle.max())+1 if row == 0 else height
        local_ink = np.where(row_mask[top:bottom], ink[top:bottom], 0)
        bounds = [np.zeros(bottom-top, dtype=int)]
        for col in range(1,cols):
            bounds.append(gutter(local_ink, width*col/cols, width/cols*.27))
        bounds.append(np.full(bottom-top,width))
        for col in range(cols):
            owner = np.zeros_like(ink, dtype=bool)
            owner[top:bottom] = row_mask[top:bottom] & (xx >= bounds[col][:,None]) & (xx < bounds[col+1][:,None])
            num = 2*cols*batch+row*cols+col+1
            key_id = f"{family}{num:0{2 if family in 'HI' else 3}}"
            save_cell(rgb,ink,owner,background,folder/(key_id+".webp"),family=="H")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("keys", nargs="*", help="Process only these sheet keys")
    args = parser.parse_args()
    sources = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    for key in args.keys or sources:
        source = Path(sources[key])
        extract(key, source if source.is_absolute() else args.manifest.parent/source)
        print(key, flush=True)
