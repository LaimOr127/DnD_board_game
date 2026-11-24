"""Sectional 404 × 340 mm shell: panels, matching hole patterns and hinge parts."""

from PIL import Image, ImageDraw
import numpy as np

from maps import font
from models import box, cyl, profile, relief, union


W, D, FLOOR, BELT = 404, 340, 5, 114
HALF_X, HALF_Y = W/2, D/2
SIDE = HALF_Y-4
BODY_HEIGHT = FLOOR+3*BELT
WALL = 4
HINGES = (59,143,261,345)
LATCHES = (77,W-77)
HINGE_LENGTH = 47
M4 = 2.18
SEAM_OFFSETS = (-25,-12,12,25)
MAP_SPLIT = (48,202)
TITLE_POSITIONS = ((56,147),(208,147))


def holes(points, start=-1, height=11, radius=M4):
    return union([cyl(u,v,start,radius,height,n=24) for u,v in points])


def hole_y(x, z, start, length, radius=M4):
    return cyl(0,0,0,radius,length,n=24).rotate((90,0,0)).translate((x,start+length,z))


def hole_x(y, z, start, length, radius=M4):
    return cyl(0,0,0,radius,length,n=24).rotate((0,90,0)).translate((start,y,z))


def lip_mount(position, along_x, outside_low):
    # Recess the screw head in the lip on the tray side.
    radii = (M4,4.26) if outside_low else (4.26,M4)
    rotation = (0,90,0) if along_x else (-90,0,0)
    return cyl(0,0,0,radii[0],2.45,radii[1],n=24).rotate(rotation).translate(position)


def floor_wall_points(length):
    return (45,length-45)


def flat_deck_holes():
    return [(HALF_X+d,y) for y in (80,260) for d in SEAM_OFFSETS] + [
        (x,HALF_Y+d) for x in (101,303) for d in SEAM_OFFSETS]


def lid_holes():
    return flat_deck_holes() + [(x,11.2) for a in HINGES for x in (a-15.5,a+15.5)] + [
        (x,D-15) for a in LATCHES for x in (a-8,a+8)] + [
        (origin+u,y) for origin in MAP_SPLIT for u in (15,139) for y in (55,285)] + [
        (47,92),(357,248)] + title_holes()


def title_holes():
    return [(x+u,y+23) for x,y in TITLE_POSITIONS for u in (10,130)]


def deck_quarter(column,row,lid=False):
    x0,y0 = column*HALF_X,row*HALF_Y
    plate = box(x0,y0,0,HALF_X,HALF_Y,FLOOR)
    if lid:
        points = lid_holes()
    else:
        points = flat_deck_holes()+[(x,y) for x in (23,W-23) for y in (23,D-23)]
        outer_y = 4 if row==0 else D-6.8
        outer_x = 4 if column==0 else W-6.8
        lip_x = box(x0,outer_y,4.7,HALF_X,2.8,14.5)
        lip_y = box(outer_x,y0,4.7,2.8,HALF_Y,14.5)
        # The short lips stay outside the clear rail envelope.
        cut = [hole_y(x0+u,FLOOR+8,outer_y-1,5) for u in floor_wall_points(HALF_X)]
        cut += [hole_x(4+row*SIDE+u,FLOOR+8,outer_x-1,5) for u in floor_wall_points(SIDE)]
        cut += [lip_mount((x0+u,outer_y+(.5 if row==0 else -.15),FLOOR+8),False,row==0)
                for u in floor_wall_points(HALF_X)]
        cut += [lip_mount((outer_x+(.5 if column==0 else -.15),4+row*SIDE+u,FLOOR+8),True,column==0)
                for u in floor_wall_points(SIDE)]
        plate = union([plate,lip_x,lip_y])-union(cut)
    local_points = [(x,y) for x,y in points if x0<x<x0+HALF_X and y0<y<y0+HALF_Y]
    plate -= holes(local_points)
    for u,v in local_points:
        # Keep the deck surfaces clear where the trays and the map rest.
        if not lid:
            plate -= cyl(u,v,2.75,M4,2.35,4.26,n=24)
        elif (u,v) in flat_deck_holes() or (u,v) in title_holes():
            plate -= cyl(u,v,-.05,4.26,2.35,M4,n=24)
    return plate.translate((-x0,-y0,0))


def wall_panel(side, top='plain'):
    length = SIDE if side else HALF_X
    edge = 8 if side else 12
    rail = 3 if side else 5
    points = [(u,v) for u in (edge,length-edge) for v in (27,87)]
    points += [(length/2,v) for v in (9,21,BELT-21,BELT-9)]
    points += [(u,8) for u in floor_wall_points(length)]
    if top == 'hinges':
        points += [(u,BELT-17.5) for c in HINGES[:2] for u in (c-15.5,c+15.5)]
    if top == 'latch':
        points += [(u,BELT-12) for u in (77,HALF_X-77)]
    panel = union([box(0,0,0,length,BELT,WALL),
                   *[box(u-3,0,WALL-.18,6,BELT,rail+.18) for u in (28,length-28)]])
    if top == 'latch':
        for u in (77,HALF_X-77):
            panel += box(u-5.3,BELT-17.3,3.85,10.6,10.6,4.35)
            panel -= box(u-3.7,BELT-15.7,4.45,7.4,7.4,4.05)
    panel -= holes(points)
    for u,v in points:
        if top != 'latch' or v!=BELT-12:
            panel -= cyl(u,v,1.72,M4,2.4,4.26,n=24)
    return panel


def corner():
    part = union([box(-3.6,-3.6,0,31.2,3.65,BELT),box(-3.6,-.04,0,3.65,27.65,BELT)])
    bores = [hole_y(12,v,-4,5) for v in (27,87)] + [hole_x(12,v,-4,5) for v in (27,87)]
    return part-union(bores)


def bridge_center():
    shell = box(-22,0,0,44,80,3.8)
    cuts = []
    for u in (-12,8):
        for v in (10,70):
            cuts += [box(u,v-M4,-1,4,M4*2,7),cyl(u,v,-1,M4,7,n=24),cyl(u+4,v,-1,M4,7,n=24)]
    return shell-union(cuts)


def bridge_tall():
    return box(-11,-30,0,22,60,3.8)-holes([(0,v) for v in (-21,-9,9,21)])


def bridge_deck():
    return box(-31,-11,0,62,22,4)-holes([(u,0) for u in SEAM_OFFSETS])


def foot():
    base = box(-14,-14,0,28,28,10)
    bore = holes([(0,0)],height=16)
    pocket = cyl(0,0,-.1,5.8,7.1,n=24)
    return base-bore-pocket


def hinge(moving):
    """Model in print orientation: pin bore is vertical, mount axes are transverse."""
    r = 5.55
    if moving:
        mount = box(5,3.95,0,3.6,21,HINGE_LENGTH)
        parts = [cyl(0,0,14.3,r,18.4,n=36), mount,
                 profile([(3.25,1),(6.4,2.7),(8.05,5.2),(5.35,7.05),(3.15,4.2)],18.4).translate((0,0,14.3))]
        mounts = [hole_x(19.2,v,4.6,5) for v in (8,39)]
    else:
        mount = box(-25,4.25,0,20.8,3.75,HINGE_LENGTH)
        parts = [mount]
        web = [(-12.6,4.28),(-4.08,1.65),(-2.85,2.8),(-4.32,6.25),(-10.2,5.7)]
        for start in (0,33.7):
            parts += [cyl(0,0,start,r,13.3,n=36),profile(web,13.3).translate((0,0,start))]
        mounts = [hole_y(-17.5,v,3.9,5.5) for v in (8,39)]
    return union(parts)-cyl(0,0,-.3,2.24,HINGE_LENGTH+.6,n=34)-union(mounts)


def latch():
    vertical = box(-13,-3.6,-19,26,3.6,27)
    top = box(-13,-3.6,5,26,28,3.4)
    return (vertical+top)-hole_y(0,-12,-4,5)-holes([(-8,15),(8,15)],start=4,height=6)


def map_rail():
    cross = [(0,0),(10,0),(10,2.8),(7,2.8),(7,8),(21,8),(21,10.6),(0,10.6)]
    rail = profile(cross,154).rotate((90,0,90))
    return rail-holes([(15,5),(139,5)],height=15)


def map_turn():
    finger = box(-5,-7,0,33,14,3.2)
    return finger-holes([(0,0)])


def title(word):
    shape = profile([(0,5),(7,0),(133,0),(140,5),(140,41),(133,46),(7,46),(0,41)],2.8)
    face = font(105,True,True)
    x0,y0,x1,y1 = face.getbbox(word)
    bitmap = Image.new('1',(x1-x0+4,y1-y0+4))
    ImageDraw.Draw(bitmap).text((2-x0,2-y0),word,font=face,fill=1)
    scale = min(111/bitmap.width,33/bitmap.height)
    letters = relief(np.asarray(bitmap),scale,.83,2.72,((140-scale*bitmap.width)/2,(46-scale*bitmap.height)/2))
    return (shape+letters)-holes([(10,23),(130,23)])


def hinge_check():
    fixed, moving = hinge(False), hinge(True)
    deck = box(0,8,0,5,D,HINGE_LENGTH)
    body = box(-BELT,8,0,BELT,D,HINGE_LENGTH)
    for angle in range(0,106,5):
        overlap = ((fixed+body) ^ (moving+deck).rotate((0,0,-angle))).volume()
        if overlap > .05:
            raise ValueError(f'Hinge parts interfere at {angle} degrees: {overlap:.2f} mm³')
