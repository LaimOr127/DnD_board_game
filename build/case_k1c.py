"""Pack the case for the 418 miniature collection as ready-to-print 3MF plates."""

import csv
from dataclasses import dataclass

import trimesh

from case_shell import (BELT, BODY_HEIGHT, D, FLOOR, HALF_X, HALF_Y, W, bridge_center, bridge_deck, bridge_tall,
                        corner, deck_quarter, foot, hinge, hinge_check, latch, map_rail, map_turn, title, wall_panel)
from figure_plates import COLLECTION, batches, check_plate
from k1c_plates import OUTPUT, arrange, write_plate
from models import box, cyl, idrel, union


DESTINATION = OUTPUT/'Кейс'
TRAY_W, TRAY_D, TRAY_H, TRAY_FLOOR = 194,160,53,3
TRAY_EDGE, DIVIDER = 2.0,1.3
FIGURE_X, FIGURE_Y = 5,4
TRAY_LOCATIONS = ('сзади слева','сзади справа','спереди слева','спереди справа')
CARD_MAX = (93,73,47)
MARKERS = ('ОЗ','Искры и щиты','Припасы','Жетоны и d6')


@dataclass(frozen=True)
class Plate:
    code: str
    name: str
    repeat: int
    columns: int
    shapes: tuple


def figure_trays():
    catalog, _ = batches()
    mobs = [key for key in catalog if key[0]=='M']
    bosses = [key for key in catalog if key[0]=='B']
    trays = []
    for area in range(10):
        for half in (0,1):
            a = area*30+half*15
            b = area*10+half*5
            level = area//2+1
            location = TRAY_LOCATIONS[(area%2)*2+half]
            trays.append((f'{area+1:02}{chr(65+half)}',level,location,mobs[a:a+15]+bosses[b:b+5]))
    trays.append(('H',6,TRAY_LOCATIONS[0],[key for key in catalog if key[0]=='H']+['','']))
    return catalog, trays


def cells(nx,ny):
    w,d = TRAY_W/nx, TRAY_D/ny
    for row in range(ny):
        for col in range(nx):
            yield row,col,((col+.5)*w,(row+.5)*d),(
                w-(TRAY_EDGE if col==0 else DIVIDER/2)-(TRAY_EDGE if col==nx-1 else DIVIDER/2),
                d-(TRAY_EDGE if row==0 else DIVIDER/2)-(TRAY_EDGE if row==ny-1 else DIVIDER/2),
                TRAY_H-TRAY_FLOOR)


def tray_shell(width=TRAY_W,depth=TRAY_D,height=TRAY_H):
    return box(0,0,0,width,depth,height)-box(TRAY_EDGE,TRAY_EDGE,TRAY_FLOOR,width-2*TRAY_EDGE,depth-2*TRAY_EDGE,height)


def pull_slots():
    return union([box(10,y,34,4,4,13) for y in (-1,TRAY_D-3)])


def figurine_tray(codes):
    shell = tray_shell()
    all_parts = [shell]
    for col in range(1,FIGURE_X):
        x = col*TRAY_W/FIGURE_X-DIVIDER/2
        all_parts.append(box(x,1.9,TRAY_FLOOR-.2,DIVIDER,TRAY_D-3.8,TRAY_H-TRAY_FLOOR+.2))
    for row in range(1,FIGURE_Y):
        y = row*TRAY_D/FIGURE_Y-DIVIDER/2
        all_parts.append(box(1.9,y,TRAY_FLOOR-.2,TRAY_W-3.8,DIVIDER,TRAY_H-TRAY_FLOOR+.2))
    cuts = [pull_slots()]
    for (_,_,(x,y),_),code in zip(cells(FIGURE_X,FIGURE_Y),codes):
        if code:
            cuts.append(cyl(x,y,-.2,6.8,TRAY_FLOOR+.4,n=28))
            cuts.append(idrel(code,.48,x-6.5,y-16.4,TRAY_FLOOR-.34))
    return union(all_parts)-union(cuts)


def organizer(labels,markers=False):
    tray = tray_shell()-pull_slots()
    ribs = [box(1.9,TRAY_D/2-.65,TRAY_FLOOR-.15,TRAY_W-3.8,1.3,TRAY_H-TRAY_FLOOR+.15)]
    if markers:
        ribs.extend(box(col*TRAY_W/4-.65,1.9,TRAY_FLOOR-.15,1.3,TRAY_D/2-1.8,TRAY_H-TRAY_FLOOR+.15) for col in (1,2,3))
        ribs.append(box(TRAY_W/2-.65,TRAY_D/2-.1,TRAY_FLOOR-.15,1.3,TRAY_D/2-1.8,TRAY_H-TRAY_FLOOR+.15))
    else:
        ribs.append(box(TRAY_W/2-.65,1.9,TRAY_FLOOR-.15,1.3,TRAY_D-3.8,TRAY_H-TRAY_FLOOR+.15))
    pocket_cells = list(cells(2,2))
    if markers:
        pocket_cells = pocket_cells[2:]
    cuts = []
    for (_,_,(x,y),_),label in zip(pocket_cells,labels):
        cuts.append(cyl(x,y,-.2,9.5,TRAY_FLOOR+.4,n=32))
        cuts.append(idrel(label,.65,x-8,y-32.5,TRAY_FLOOR-.34))
    if markers:
        for i,label in enumerate(('HP','SP','RP','D6')):
            cuts.append(idrel(label,.65,(i+.5)*TRAY_W/4-5.5,8,TRAY_FLOOR-.34))
    return union([tray,*ribs])-union(cuts)


def organizer_cover():
    deck = box(0,0,0,TRAY_W,TRAY_D,3.1)
    pins = [cyl(x,y,2.94,1.3,1.7,1.14,n=24) for x in (4.5,TRAY_W-4.5) for y in (4.5,TRAY_D-4.5)]
    return union([deck,*pins])


def probe_card():
    # Corner gauge for the maximum 93 × 73 mm sleeve envelope.
    base = box(0,0,0,98,22,2.8)
    return union([base,box(0,0,2.65,2.5,22,8),box(95.5,0,2.65,2.5,22,8),box(0,0,2.65,98,2.5,8)])


def pusher():
    return cyl(0,0,0,9,5,n=32)+cyl(0,0,4.8,4.3,39,3.8,n=28)


def plates(trays):
    card1 = ('H','I','B1','B2')
    card2 = ('M1','M2','M3','M4')
    card3 = ('M5','M6')
    result = [Plate('00-fit','Проба петли и ширины протектора',1,2,(hinge(False),hinge(True),probe_card())),
              *[Plate(f'{10+row*2+col:02}-base','Дно, четверть '+str(row*2+col+1),1,1,(deck_quarter(col,row),))
                for row in (0,1) for col in (0,1)],
              *[Plate(f'{14+row*2+col:02}-lid','Крышка, четверть '+str(row*2+col+1),1,1,(deck_quarter(col,row,lid=True),))
                for row in (0,1) for col in (0,1)],
              Plate('20-panel-x-x08','Длинная стенка, нижние два пояса',8,1,(wall_panel(False),)),
              Plate('21-panel-y-x12','Боковая стенка, все пояса',12,1,(wall_panel(True),)),
              Plate('22-panel-front-x02','Длинная стенка под винты закрывания',2,1,(wall_panel(False,'latch'),)),
              Plate('23-panel-rear-x02','Длинная стенка под петли',2,1,(wall_panel(False,'hinges'),)),
              Plate('30-corners-x03','Уголки корпуса',3,4,(corner(),)*4),
              Plate('31-center-bridges-x03','Накладки на стык половин стенки',3,2,(bridge_center(),)*4),
              Plate('32-belt-bridges-x04','Накладки между поясами',4,4,(bridge_tall(),)*4),
              Plate('33-deck-bridges-x02','Накладки на стыки дна и крышки',2,2,(bridge_deck(),)*4),
              Plate('34-feet-pusher','Четыре ножки и выталкиватель',1,3,(*(foot().rotate((180,0,0)),)*4,pusher())),
              Plate('35-hinges-x02','Две петли, четыре половины',2,4,(hinge(False),hinge(True))*2),
              Plate('36-locks-map-turns','Скобы крышки и поворотные упоры карты',1,4,
                    (latch().rotate((180,0,0)),latch().rotate((180,0,0)),map_turn(),map_turn())),
              Plate('37-map-rails-x02','Секции направляющих для карты',2,1,(map_rail(),)*2),
              Plate('38-title','Рельефное название крышки',1,1,(title('МОРЕ'),title('ИМЁН'))),
              Plate('39-insert-cover-x04','Крышка внутреннего лотка',4,1,(organizer_cover(),)),
              Plate('40-heroes','Лоток 18 героев и 2 запасные ячейки',1,1,(figurine_tray(trays[-1][3]),)),
              Plate('41-cards-c1','Колоды H, I, B1 и B2',1,1,(organizer(card1),)),
              Plate('42-cards-c2','Колоды M1–M4',1,1,(organizer(card2),)),
              Plate('43-cards-c3-markers','Колоды M5, M6 и четыре отсека жетонов',1,1,(organizer(card3,markers=True),))]
    result += [Plate(f'{50+i:02}-tray-{tag}',f'Лоток {tag} · ярус {level}, {spot}',1,1,(figurine_tray(codes),))
               for i,(tag,level,spot,codes) in enumerate(trays[:-1])]
    return result


def printable_mesh(shape,name):
    if len(shape.decompose()) != 1:
        raise ValueError(f'{name} is not a single print solid')
    raw = shape.to_mesh()
    model = trimesh.Trimesh(raw.vert_properties[:,:3],raw.tri_verts)
    if not model.is_volume or len(model.split(only_watertight=False))!=1:
        raise ValueError(f'{name} is not a closed volume in the 3MF mesh')
    model.apply_translation(-model.bounds[0])
    return model


def write_index(catalog,trays):
    with (COLLECTION/'Указатель.csv').open(encoding='utf-8-sig',newline='') as index:
        sizes = {r['Код']:tuple(float(r[k]) for k in ('Ширина, мм','Глубина, мм','Высота с базой, мм'))
                 for r in csv.DictReader(index,delimiter=';') if r['Файл 3MF']!='00-sample.3mf'}
    encountered = set()
    smallest = float('inf')
    with (DESTINATION/'Ячейки фигурок.csv').open('w',encoding='utf-8-sig',newline='') as inventory:
        out = csv.writer(inventory,delimiter=';')
        out.writerow(['Код','Имя','Ярус от дна','Положение','Лоток','Ряд от петель','Ячейка слева',
                      'Зазор по ширине, мм','Зазор по глубине, мм','Зазор сверху, мм'])
        for tag,level,spot,codes in trays:
            for (row,col,_,space),code in zip(cells(FIGURE_X,FIGURE_Y),codes):
                if not code:
                    continue
                free = tuple(a-b for a,b in zip(space,sizes[code]))
                if min(free)<.80 or code in encountered:
                    raise ValueError((tag,code,space,sizes[code],free))
                smallest = min(smallest,*free)
                encountered.add(code)
                out.writerow([code,catalog[code][1],level,spot,tag,row+1,col+1,*(f'{v:.2f}' for v in free)])
    assert encountered==set(catalog)==set(sizes) and len(encountered)==418
    assert all(min(a-b for a,b in zip(space,CARD_MAX))>1 for _,_,_,space in cells(2,2))
    # Both modules of every layer slip between continuous ribs with 2 mm play.
    assert W-14-2*TRAY_W==2 and D-18-2*TRAY_D==2
    assert BODY_HEIGHT-10.6-(FLOOR+6*TRAY_H+3.1) > 10
    assert 268 < 308 and 180 < 226 # folded map, retained by the adjustable bands
    print(f'{len(encountered)} figure cells; narrowest total clearance {smallest:.2f} mm',flush=True)


def main():
    DESTINATION.mkdir(exist_ok=True)
    hinge_check()
    catalog, trays = figure_trays()
    write_index(catalog,trays)
    specifications = plates(trays)
    with (DESTINATION/'Ведомость печати.csv').open('w',encoding='utf-8-sig',newline='') as file:
        writer=csv.writer(file,delimiter=';')
        writer.writerow(['Пластина','Детали','Сколько раз печатать','Деталей за раз','Наибольший размер детали на столе, мм',
                         'Объём сплошной геометрии одной пластины, см³'])
        for spec in specifications:
            keys = []
            models = {}
            known = {}
            for shape in spec.shapes:
                identity = id(shape)
                if identity not in known:
                    key = ('case',f'{spec.code}-{len(known)+1}',1)
                    known[identity] = key
                    models[key] = printable_mesh(shape,key[1])
                keys.append(known[identity])
            found=arrange(keys,models,spec.columns,gap=7,margin=8)
            target=DESTINATION/(spec.code+'.3mf')
            candidate=target.with_suffix('.tmp')
            write_plate(candidate,models,found)
            check_plate(candidate,[key[1] for key in keys],models,found)
            candidate.replace(target)
            size = max(max(models[k].extents[:2]) for k in keys)
            amount = sum(models[k].volume for k in keys)/1000
            writer.writerow([target.name,spec.name,spec.repeat,len(keys),f'{size:.2f}',f'{amount:.2f}'])
            print(target.name,len(keys),spec.repeat,flush=True)
    print('plates',len(specifications),'print runs',sum(p.repeat for p in specifications),
          'copies',sum(len(p.shapes)*p.repeat for p in specifications),flush=True)


if __name__ == '__main__':
    main()
