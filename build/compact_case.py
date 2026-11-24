"""One-piece tubs and lids for the travel edition of the K1C case."""

import csv
from math import cos, pi, sin

import numpy as np
from PIL import Image, ImageDraw

from art import sprite
from case_k1c import printable_mesh
from figure_plates import COLLECTION, batches, check_plate
from k1c_plates import BOSSES as BOSS_MODELS, OUTPUT, POSED, arrange, geometry, pieces, write_plate
from maps import font
from models import box, cyl, idrel, profile, relief, union
from printkit import cards


DEST = OUTPUT / 'Кейс дорожный'
W, D, BODY, TOP, DECK = 164, 197, 111, 124, 3.2
SEAM, WALL, FLOOR = 5.0, 3.2, 4
AY, AZ = -5.75, 112
END_STARTS = (60, 95)
TRAY_W, TRAY_D, TRAY_H = 153.2, 187.6, 52.8
HEROES = [f'H{i:02}' for i in range(1,19)]
BOSSES = [f'B{i:03}' for i in range(1,101,10)]
CROWDS = (('S','knight','караул'), ('Z','wolf','звери'),
          ('L','bat','крылатые'), ('C','spider','ползучие'))
CARD_LANES = (
    (('H', 'H',1,18,15), ('I','I',1,40,27), ('B1','B',1,50,31),
     ('M1','M',1,60,37), ('M2','M',61,120,37)),
    (('B2','B',51,100,33), ('M3','M',121,165,29), ('M4','M',166,210,29),
     ('M5','M',211,255,29), ('M6','M',256,300,29)),
)


def along_x(points, x, length):
    return profile(points,length).rotate((90,0,90)).translate((x,0,0))


def bore(x,y,z,length,r=2.24,up=1):
    # The roof meets at 45° in the print orientation.
    a = [(y+r*cos(i*pi/180),z+up*r*sin(i*pi/180)) for i in range(135,406,15)]
    return along_x([*a,(y,z+up*r*2**.5)],x,length)


def knuckles(moving):
    web = ([(-3.5,3.6),(5.3,10.7),(13,10.7),(13,8.4),(7,8.4),(5.7,.9),(1.9,-1.6)]
           if moving else [(-3.7,-3.6),(5.9,-13.2),(8,-13.2),(8,-1.2),(5.8,-1.2),(3,2.9),(-2.6,3.7)])
    sections = [(73.8,20.4)] if moving else [(x,13) for x in END_STARTS]
    parts = []
    for x,length in sections:
        barrel = cyl(0,0,0,5.15,length,n=40).rotate((0,90,0)).translate((x,AY,AZ))
        bridge = along_x([(AY+y,AZ+z) for y,z in web],x,length)
        parts.append((barrel+bridge)-bore(x-.2,AY,AZ,length+.4,up=-1 if moving else 1))
    return union(parts)


def raised_label(value, width, height, z, x, y, size=105):
    face = font(size,True,True)
    l,t,r,b = face.getbbox(value)
    mask = Image.new('1',(r-l+4,b-t+4))
    ImageDraw.Draw(mask).text((2-l,2-t),value,fill=1,font=face)
    scale = min(width/mask.width,height/mask.height)
    return relief(np.asarray(mask),scale,.72,z,(x-scale*mask.width/2,y-scale*mask.height/2))


def lid(right):
    rim = [box(0,0,BODY+.6,W,4,TOP-BODY-.6),box(0,D-4,BODY+.6,W,4,TOP-BODY-.6),
           box(W-WALL if right else 0,3.8,BODY+.6,WALL,D-7.6,TOP-BODY-.6)]
    shell = union([box(0,0,TOP-DECK,W,D,DECK),*rim,knuckles(True)])
    for y in (3.6,D-3.6):
        x = 0 if right else W-8
        shell += box(x,y-3.6,BODY+.6,8,7.2,TOP-BODY-.6)
        shell -= bore(x-.1,y,117,8.2,up=-1)
    # Two slots accept one flat elastic band on each lid half.
    shell -= union([box(W/2-9,y-1.4,TOP-DECK-.15,18,2.8,DECK+.25)
                    for y in (7,D-7)])
    # When viewed from the closure side, large X is on the reader's left.
    word = 'МОРЕ' if right else 'ИМЁН'
    engraving = raised_label(word,135,32,TOP-.70,W/2,105).rotate((0,0,180)).translate((W,210,0))
    return shell-engraving


def grip_divider(x,y,d):
    wall = box(x,y,3.8,1.4,d,77)
    return wall-box(x-.2,y+d/2-20,47,1.8,40,35)


def card_slots():
    parts = [box(WALL-.15,D/2-.8,3.8,W-WALL-SEAM+.3,1.6,74)]
    for lane, (start,d) in zip(CARD_LANES, [(WALL-.15,D/2-.8-WALL+.3),
                                           (D/2+.65,D/2-WALL-.65+.15)]):
        x = WALL
        for i,(label,_,_,_,length) in enumerate(lane):
            parts.append(idrel(label,.75,x+4,start+4,3.93))
            x += length
            if i < len(lane)-1:
                parts.append(grip_divider(x,start,d))
                x += 1.4
        assert x <= W-SEAM
    for x,w in ((WALL-.15,3),(W-SEAM-2.85,3)):
        # Continuous ledges with a 45° ramp hold the removable token tray above the sleeves.
        section = [(x,82),(x+w,85),(x+w,86.5),(x,86.5)] if x < W/2 else [
            (x+w,82),(x,85),(x,86.5),(x+w,86.5)]
        parts.append(profile(section,D-2*WALL+.3).rotate((90,0,0)).translate((0,D-WALL+.15,0)))
    return union(parts)


def tub(right):
    a,b = (SEAM,WALL) if right else (WALL,SEAM)
    shell = box(0,0,0,W,D,BODY)-box(a,WALL,FLOOR,W-a-b,D-2*WALL,BODY)
    shell += knuckles(False)
    for y in (14,D-14):
        for z in (18,95):
            x = 0 if right else W-SEAM
            shell -= bore(x-.15,y,z,SEAM+.3)
            if right:
                shell -= box(1.65,y-3.65,z-3.65,3.55,7.3,7.3)
            else:
                recess = cyl(0,0,0,4.4,2.35,2.2,n=32).rotate((0,90,0))
                shell -= recess.translate((W-SEAM-.05,y,z))
    return shell if right else shell+card_slots()


def tray_shell(height):
    return box(0,0,0,TRAY_W,TRAY_D,height)-box(1.7,1.7,2.8,TRAY_W-3.4,TRAY_D-3.4,height)


def figure_tray(bosses):
    picked = BOSSES if bosses else HEROES
    cols, rows = 4,5
    w,d = TRAY_W/cols,TRAY_D/rows
    last_row = 3 if bosses else rows
    model = tray_shell(TRAY_H)
    ribs = [box(x*w-.65,1.55,2.6,1.3,(3*d-1.3 if bosses and x!=2 else TRAY_D-3.1),TRAY_H-2.6)
            for x in range(1,cols)]
    ribs += [box(1.55,y*d-.65,2.6,TRAY_W-3.1,1.3,TRAY_H-2.6) for y in range(1,last_row+int(bosses))]
    if bosses:
        ribs.append(box(1.55,4*d-.65,2.6,TRAY_W-3.1,1.3,TRAY_H-2.6))
    model = union([model,*ribs])
    for i,key in enumerate(picked):
        row,col = divmod(i,cols)
        x,y = (col+.5)*w,(row+.5)*d
        model -= cyl(x,y,-.1,7,3,n=30)+idrel(key,.55,x-6.7,y-15.7,2.44)
    for x in (TRAY_W*.29,TRAY_W*.71):
        for y in (-.1,TRAY_D-2):
            model -= box(x-7,y,TRAY_H-8,14,2.2,8.1)
    return model


def token_tray():
    height = 22
    return union([tray_shell(height),box(TRAY_W/2-.7,1.55,2.6,1.4,TRAY_D-3.1,height-2.6),
                  box(1.55,TRAY_D/2-.7,2.6,TRAY_W-3.1,1.4,height-2.6),
                  box(TRAY_W/2-8,TRAY_D/2-7,height-2,16,14,5.7)])


def marker(code, creature=None):
    if creature:
        base = cyl(0,0,0,12.25,2.4,11.7,n=48)
        image = sprite(creature,0).getchannel('A')
        image = image.crop(image.getbbox())
        scale = min(7.5/image.width,6.2/image.height)
        figures = [relief(np.asarray(image)>40,scale,.73,2.34,(x-3.5,y))
                   for x,y in [(-4,-2.9),(3.5,-2.7),(0,3.5)]]
    else:
        base = profile([(-11,-9),(-7,-12),(7,-12),(11,-9),(11,8),(8,11),(-8,11),(-11,8)],2.4)
        crown = profile([(-6,-1),(-7,4),(-3,2),(0,6),(3,2),(7,4),(6,-1)],.85)
        figures = [crown.translate((0,0,2.3))]
    return union([base,*figures,idrel(code,.72,-4.6,-9.6,2.32)])


def sample():
    bottom = (box(57,0,97,54,8,BODY-97)+knuckles(False)).translate((-57,0,-97))
    top = (box(57,0,TOP-DECK,54,14,DECK)+knuckles(True)).translate((-57,0,0))
    width = box(0,0,0,98,16,2.8)+union([box(x,0,2.7,2.5,16,7) for x in (0,95.5)])
    seams = [tub(right)^box(0 if right else W-SEAM,5,8,SEAM,18,20) for right in (False,True)]
    return bottom, top.rotate((180,0,0)), width, *seams


def verify():
    a, b = tub(False), tub(True).translate((W,0,0))
    right_trays = box(W+6.2,4.2,FLOOR,TRAY_W,TRAY_D,2*TRAY_H)
    left_tray = token_tray().translate((4.1,4.2,86.5))
    closed = lid(False)+lid(True).translate((W,0,0))
    folded_map = box(27,7.5,TOP-DECK-6,274,182,6)
    assert ((a+b) ^ (right_trays+left_tray)).volume() < .05
    assert (closed ^ (right_trays+left_tray+folded_map)).volume() < .05
    # Guard volumes include both tubs and the moving lid with its paper pocket.
    for angle in range(0,111,5):
        moved = (closed+folded_map).translate((0,-AY,-AZ)).rotate((angle,0,0)).translate((0,AY,AZ))
        assert ((a+b)^moved).volume() < .05, angle
    assert len(set(HEROES+BOSSES))==28
    with (COLLECTION/'Указатель.csv').open(encoding='utf-8-sig',newline='') as file:
        dims = {r['Код']:tuple(float(r[k]) for k in ('Ширина, мм','Глубина, мм','Высота с базой, мм'))
                for r in csv.DictReader(file,delimiter=';')}
    figures = tuple(min(x) for x in zip(*(tuple(
        free-size for free,size in zip((TRAY_W/4-2.35,TRAY_D/5-2.35,TRAY_H-2.8),dims[key]))
        for key in HEROES+BOSSES)))
    assert min(figures) >= 2, figures
    ids = {f'{prefix}{i:0{3 if prefix in "BM" else 2}}' for lane in CARD_LANES
           for _,prefix,start,end,_ in lane for i in range(start,end+1)}
    assert ids == set(cards) and len(ids) == 458
    assert (D-2*WALL-1.6)/2 >= 93 and all(
        length-2 >= (end-start+1)*.55 for lane in CARD_LANES for _,_,start,end,length in lane)
    row_depth = (D-2*WALL-1.6)/2
    for j,lane in enumerate(CARD_LANES):
        x = WALL
        y = WALL + j*(row_depth+1.6) + (row_depth-93)/2
        for slot,_,_,_,length in lane:
            stack = box(x+1,y,FLOOR+.5,length-2,93,73)
            assert ((a+left_tray)^stack).volume() < .05, slot
            x += length+1.4


def write_index():
    catalog,_ = batches()
    with (DEST/'Фигурки и карты.csv').open('w',encoding='utf-8-sig',newline='') as file:
        index = csv.writer(file,delimiter=';')
        index.writerow(['Лоток','Код','Название','Ряд от петель','Ячейка в ряду'])
        for name, keys in [('Герои',HEROES),('Боссы',BOSSES)]:
            for i,key in enumerate(keys):
                row,col = divmod(i,4)
                index.writerow([name,key,catalog[key][1],row+1,col+1])
        index.writerow([])
        index.writerow(['Ряд карт','Отсек','От карты','До карты','Длина стопки, мм'])
        for i,lane in enumerate(CARD_LANES,1):
            for slot,prefix,start,end,length in lane:
                n = 3 if prefix in 'BM' else 2
                index.writerow([i,slot,f'{prefix}{start:0{n}}',f'{prefix}{end:0{n}}',length-2])


def main():
    DEST.mkdir(exist_ok=True)
    verify()
    index = []
    tokens = [marker(f'{code}{i}',creature) for code,creature,_ in CROWDS for i in range(1,4)]
    plates = [('00-fit','Петля, проба соединения М4 и калибр карты', 2, sample()),
              ('01-cards','Половина корпуса с вертикальными отсеками для карт',1,(tub(False),)),
              ('02-figures','Половина корпуса для двух лотков с фигурками',1,(tub(True),)),
              ('03-lid-imen','Половина крышки «ИМЁН»',1,(lid(False).rotate((180,0,0)),)),
              ('04-lid-more','Половина крышки «МОРЕ»',1,(lid(True).rotate((180,0,0)),)),
              ('05-hero-tray','Лоток 18 героев',1,(figure_tray(False),)),
              ('06-boss-tray','Лоток десяти боссов и фишек толпы',1,(figure_tray(True),)),
              ('07-token-tray','Четыре отсека под жетоны и кости',1,(token_tray(),)),
              ('08-crowds','12 жетонов толпы и два жетона боссов',5,(*tokens,marker('B1'),marker('B2')))]
    for name,caption,columns,shapes in plates:
        keys = [('compact',f'{name}-{i+1}',1) for i in range(len(shapes))]
        meshes = {key:printable_mesh(shape,key[1]) for key,shape in zip(keys,shapes)}
        placements = arrange(keys,meshes,columns,gap=7,margin=6)
        dest = DEST/(name+'.3mf')
        write_plate(dest,meshes,placements)
        check_plate(dest,[key[1] for key in keys],meshes,placements)
        size = max(max(m.extents[:2]) for m in meshes.values())
        index.append([dest.name,caption,len(keys),f'{size:.2f}'])
        print(dest.name, len(keys), flush=True)
    for name,caption,group,codes in [('09-heroes','18 объёмных героев',POSED,HEROES),
                                     ('10-bosses','10 объёмных боссов',BOSS_MODELS,BOSSES)]:
        keys = pieces(group,codes)
        meshes = geometry(keys)
        placements = arrange(keys,meshes,5,gap=10)
        dest = DEST/(name+'.3mf')
        write_plate(dest,meshes,placements)
        check_plate(dest,codes,meshes,placements)
        size = max(max(m.extents[:2]) for m in meshes.values())
        index.append([dest.name,caption,len(keys),f'{size:.2f}'])
        print(dest.name,len(keys),flush=True)
    with (DEST/'Ведомость печати.csv').open('w',encoding='utf-8-sig',newline='') as file:
        schedule = csv.writer(file,delimiter=';')
        schedule.writerow(['Файл','Что печатается','Деталей','Наибольшая сторона на столе, мм'])
        schedule.writerows(index)
    write_index()


if __name__ == '__main__':
    main()
