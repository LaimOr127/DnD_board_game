"""A printable trial of a larger piece of terrain: Nera's cottage in Three Willows."""

from math import atan, degrees, hypot
from random import Random

from PIL import Image, ImageDraw
import trimesh

from k1c_plates import arrange, write_plate
from maps import OUT, font
from models import CS, M, box, cyl, md, profile, union


WIDTH, DEPTH, EAVES = 58, 44, 29
PEGS = ((5, 1.35), (53, 42.65))


def stone(x, z, width, height, depth):
    edge = .46
    cross = CS.square((width-2*edge,height-2*edge)).translate((edge,edge)).offset(edge,md.JoinType.Round)
    return cross.extrude(depth).rotate((90,0,0)).translate((x,.45,z))


def beam(a,b,width):
    dx,dz = b[0]-a[0],b[1]-a[1]
    scale = width/(2*hypot(dx,dz))
    ox,oz = -dz*scale,dx*scale
    points = [(a[0]+ox,a[1]+oz),(b[0]+ox,b[1]+oz),(b[0]-ox,b[1]-oz),(a[0]-ox,a[1]-oz)]
    return profile(points,1.65).rotate((90,0,0)).translate((0,.32,0))


def facade(length, openings, seed):
    rng = Random(seed)
    parts = [box(0,0,1.65,length,2.7,EAVES-1.65)]
    for row in range(4):
        x = .28 if row%2 else .72
        while x+2 < length:
            w = min(rng.uniform(4.2,7.0),length-x-.25)
            parts.append(stone(x,2.55+row*2.63+rng.uniform(-.19,.19),w,2.42,rng.uniform(.85,1.59)))
            x += w+rng.uniform(.28,.62)
    for z in (13.7,18.2,22.65,27.1):
        parts.append(box(0,-.59,z,length,.79,1.03))
    parts.extend([beam((1.38,11.6),(1.38,28.55),2.69),beam((length-1.38,11.6),(length-1.38,28.55),2.69),
                  beam((1.6,12.2),(length-1.6,12.2),2.05),beam((1.6,27.63),(length-1.6,27.63),2.15),
                  beam((2,13),(15,26.5),1.9),beam((length-2,13),(length-15,26.5),1.9)])
    holes = []
    for centre, width, bottom, shoulder in openings:
        radius = width/2
        # A pointed lintel prints with a shorter bridge than a rectangular opening.
        outline=[(centre-radius,bottom),(centre+radius,bottom),(centre+radius,shoulder),
                 (centre,shoulder+radius),(centre-radius,shoulder)]
        frame=[(centre-radius-.82,bottom),(centre+radius+.82,bottom),(centre+radius+.82,shoulder+.34),
               (centre,shoulder+radius+1.12),(centre-radius-.82,shoulder+.34)]
        parts.append(profile(frame,2.2).rotate((90,0,0)).translate((0,.55,0)))
        holes.append(profile(outline,8).rotate((90,0,0)).translate((0,4.4,0)))
    return union(parts)-union(holes)


def cottage():
    floor = box(-2.2,-2.2,0,WIDTH+4.4,DEPTH+4.4,2.4)
    boards = [box(2.4,3+j*3.81,2.28,WIDTH-4.8,3.55,.74) for j in range(10)]
    front = facade(WIDTH,[(11,7,15,19.5),(28.7,11.2,2.4,14.25),(46,7.2,14.7,18.3)],41)
    back = facade(WIDTH,[(20,8,14.65,19),(38,7,15.3,19.9)],42).rotate((0,0,180)).translate((WIDTH,DEPTH,0))
    east = facade(DEPTH,[(24,8.4,14.85,19.3)],43).rotate((0,0,90)).translate((WIDTH,0,0))
    west = facade(DEPTH,[(14,6.8,15.25,20)],44).rotate((0,0,270)).translate((0,DEPTH,0))
    bench = union([box(5.4,36,2.6,18,4.3,5.2),box(4.9,35.4,7.1,19.5,5.3,1.55),
                   box(6.75,36.4,8.35,3.2,3.4,.9),box(9.7,37.1,8.35,3.1,2.45,.7)])
    pins = [cyl(x,y,EAVES-.48,.96,2.42,.85,n=24) for x,y in PEGS]
    return union([floor,*boards,front,back,east,west,bench,*pins])


def roof():
    overhang = 2.4
    # Cross-section in Y/Z, extruded along X. The bottom bearing lip stays plane.
    pitch = 19/(DEPTH/2+overhang)
    whole = profile([(-overhang,0),(DEPTH+overhang,0),(DEPTH+overhang,2),
                     (DEPTH/2,21),(-overhang,2)],WIDTH+2*overhang)
    top = whole.rotate((90,0,90)).translate((-overhang,0,0))
    shingles = []
    rng = Random(82)
    slant = degrees(atan(pitch))
    for side in (-1,1):
        for row in range(5):
            y = -1.95+row*4.59
            z = 2+(y+overhang)*pitch
            x = -2.12
            while x+2 < WIDTH+2.3:
                width = min(rng.uniform(4.25,6.25), WIDTH+2.22-x)
                tile = box(0,0,0,width,5.15,rng.uniform(.76,1.12))
                # Turning around Z reverses the direction up the rear slope.
                tile = tile.rotate((slant,0,0))
                if side == -1:
                    tile = tile.translate((x,y,z-.35))
                else:
                    tile = tile.rotate((0,0,180)).translate((x+width,DEPTH-y,z-.35))
                shingles.append(tile)
                x += width + .34
    ridge = [M.sphere(1,18).scale((3.0,1.2,1.03)).translate((x,DEPTH/2,20.62))
             for x in range(0,WIDTH+1,5)]
    chim_x, chim_y = 16, 30
    chimney = union([box(chim_x,chim_y,11.7,6.55,5.6,12.9),box(chim_x-.52,chim_y-.54,23.1,7.59,6.78,1.72),
                     *[stone(chim_x+.31,16.9+z,5.91,1.45,1.31).translate((0,chim_y+.21,0)) for z in (0,2.1,4.2)]])
    sockets = [cyl(x,y,-.45,1.43,3.07,n=24) for x,y in PEGS]
    return union([top,chimney,*shingles,*ridge])-union(sockets)


def mesh(model):
    if len(model.decompose()) != 1 or model.status() != md.Error.NoError:
        raise ValueError('Printable part must be a single solid')
    raw = model.to_mesh()
    return trimesh.Trimesh(raw.vert_properties[:,:3],raw.tri_verts)


def main():
    from workshop import render_mesh

    body, cap = cottage(), roof()
    if (body ^ cap.translate((0,0,EAVES))).volume() > .1:
        raise ValueError('The assembled roof intersects the cottage')
    destination = OUT / 'Пластины K1C'
    directory = destination / 'Мастерская Неры'
    directory.mkdir(exist_ok=True)
    meshes = {}
    for name, solid in [('Nera-cottage',body),('Nera-roof',cap)]:
        part = mesh(solid)
        if not part.is_volume:
            raise ValueError(f'{name} is not a valid solid')
        (directory / f'{name}.stl').write_bytes(part.export(file_type='stl'))
        part.apply_translation(-part.bounds[0])
        meshes['scenery',name,1] = part
        print(name, part.extents.round(2).tolist())
    write_plate(destination/'10-nera-cottage.3mf',meshes,arrange(list(meshes),meshes,2))
    open_house = mesh(body)
    assembled = trimesh.util.concatenate((open_house,mesh(cap.translate((0,0,EAVES)))))
    sheet = Image.new('RGB',(1200,585),'#eee8d8')
    draw = ImageDraw.Draw(sheet)
    draw.text((34,27),'Мастерская Неры · Три Ивы',font=font(39,True,True),fill='#223c39')
    for i,(label,model) in enumerate([('Дом в сборе',assembled),('Дом со снятой крышей',open_house)]):
        sheet.paste(render_mesh(model,(592,447),'#ad7954'),(600*i+4,75))
        draw.text((600*i+300,543),label,font=font(24,True),fill='#223c39',anchor='ma')
    sheet.save(directory/'Мастерская Неры.png')


if __name__ == '__main__':
    main()
