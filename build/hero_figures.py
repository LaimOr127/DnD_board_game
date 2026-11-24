"""Poses and equipment keyed to the eighteen hero cards, in millimetres."""

from math import acos, atan2, cos, degrees, pi, sin

from models import M, cyl, union


def oval(point, radii):
    return M.sphere(1, 28).scale(radii).translate(point)


def limb(a, b, start, end):
    x, y, z = (q - p for p, q in zip(a, b))
    length = (x*x + y*y + z*z)**.5
    return (M.cylinder(length, start, end, 16).rotate((0, degrees(acos(z/length)), 0))
            .rotate((0, 0, degrees(atan2(y, x)))).translate(a))


def sweep(points, radii):
    parts = [oval(p, (r, r, r)) for p, r in zip(points, radii)]
    parts += [limb(a, b, r, s) for a, b, r, s in zip(points, points[1:], radii, radii[1:])]
    return union(parts)


def loop(x, y, z, rx, rz, thickness=.78):
    points = [(x+rx*cos(i*pi/8), y, z+rz*sin(i*pi/8)) for i in range(17)]
    return sweep(points, [thickness]*17)


# Stance, centre shift, head, arm positions and showpiece for each card.
POSES = (
    (26, 3.5, -1.1, 'braid', (-6.5,-3,20), (6,-4,18), 'bow'),       # Сойка
    (29, 3.3,  .8, 'elf', (-5,-4,17), (6,-1,20), 'branch'),          # Лиор
    (24, 3.4, -1.6, 'hood', (-6,-2.5,16), (5.5,-4,17), 'low_bow'),  # Ильва
    (22, 4.4, -.3, 'beard', (-5.7,-4,15), (7,-1,16), 'prop'),        # Бром
    (23, 4.2,  .7, 'bun', (-6,-2.5,15), (6.5,-1,22), 'hammer'),      # Тора
    (22, 4,   1.3, 'helm', (-5.6,-3,15), (6,-4,17), 'crossbow'),     # Келл
    (27, 3.7, -.6, 'hood', (-5.8,-3,20), (6,-3,18), 'knot'),          # Мара
    (25, 3.5,  .5, 'bun', (-5.2,-3,15), (5.8,-4,20), 'bottles'),      # Яса
    (27, 3.6,  .1, 'hood', (-5.4,-2,14), (5.5,-3.5,21), 'candle'),    # Веста
    (27, 4.3, -.7, 'helm', (-6,-4.8,17), (7,-1,18), 'shield'),        # Ивар
    (27, 3.5, 1.1, 'braid', (-5.7,-.5,17), (7,-4,19), 'rapier'),      # Рена
    (29, 4,   -.4, 'beard', (-6,-1,18), (6.4,-1,18), 'banner'),       # Оллен
    (28, 3.5, -.2, 'elf', (-5.7,-3.3,18), (6,-1,20), 'salt'),        # Ней
    (26, 3.5,  .5, 'hood', (-6,-3.6,16), (5.8,-4,21), 'mirror'),      # Тея
    (29, 3.8,  .5, 'beard', (-5.7,-3,18), (6.3,-1,21), 'clock'),     # Эсс
    (28, 4.9, -1.2, 'tusk', (-6.8,-3,17), (7.6,-1,23), 'pick'),     # Гран
    (28, 4.6,  .8, 'braid', (-6.7,-3.6,17), (6,-4,19), 'horn'),      # Урса
    (27, 4.5, 1.3, 'tusk', (-6.8,-4,16), (6.6,-1,18), 'rope'),       # Рох
)


def equipment(gear, left, right):
    x, y, z = right
    a, b, c = left
    if gear in ('bow', 'low_bow'):
        # Set the arc across the front so it reads from a player's seat.
        low = (x-4.6,y,z-5.0) if gear == 'bow' else (x-6.9,y-.7,z-2.7)
        high = (x-4.6,y,z+8) if gear == 'bow' else (x+4.3,y-.7,z+1.5)
        arc = sweep([low,(x-.3,y,z-3.6),right,(x+.6,y,z+3.8),high],[.75,.93,1.06,.90,.73])
        return arc + limb(low,high,.57,.57)
    if gear in ('branch', 'prop', 'banner', 'salt', 'clock', 'rope'):
        top = 35 if gear == 'banner' else 31 if gear == 'clock' else z+5
        staff = sweep([(x-1,y+.5,1.9),right,(x+.35,y,top)], [1.12,1.04,.88])
        if gear == 'branch':
            return staff + sweep([(x,y,z+3),(x-2.2,y,z+5),(x-3.2,y,z+7)],[1.1,.94,.64]) + oval((x+1,y,z+4.6),(1.4,1.4,1.4))
        if gear == 'prop':
            return staff + sweep([(x-2.5,y,z+4),(x,y,z+2.5),(x+2.5,y,z+4)],[.9,1.32,.9])
        if gear == 'banner':
            folds = [oval((x-1.4-j*1.55,y+.32*sin(j),top-3-j*.54),(1.48,.89,3.25-j*.20)) for j in range(5)]
            return union([staff, *folds])
        if gear == 'salt':
            return staff + oval((x+.32,y,top),(2.3,1.85,2.05)) + oval((a,b,c+1.3),(1.55,1.36,1.56))
        if gear == 'clock':
            return staff + oval((x+.35,y,top),(2.85,.85,2.85)) + loop(x+.35,y-.55,top,2.32,2.32,.61)
        return staff + loop(a-1,b,c-1,2.85,3.55,.93)
    if gear in ('hammer', 'pick'):
        head = (x-.7,y,z+4.1)
        handle = sweep([(x+.75,y,z-3.4),right,head],[.91,.96,1.1])
        end = sweep([(x-3.25,y,head[2]-.2),head,(x+3.4,y,head[2]-(1.8 if gear=='pick' else 0))],
                    [1.5,1.72,.72] if gear == 'pick' else [1.53,1.5,1.53])
        return handle + end
    if gear == 'crossbow':
        return sweep([(x+.15,y+2,z),right,(x,y-3.5,z+.55)],[1.45,.94,.74]) + sweep([(x-2.6,y-2,z),(x,y-3,z+.35),(x+2.6,y-2,z)],[.68,.9,.68])
    if gear == 'knot':
        return loop(a-.5,b,c+1,3,2.05,.87) + loop(a+.5,b,c+.7,1.7,2.9,.78) + sweep([right,(x+.85,y,z+2.7),(x+.2,y,z+5)],[1.02,.93,.76])
    if gear in ('bottles', 'candle'):
        tip = oval((x,y,z+3.55),(.86,.86,1.37))
        if gear == 'candle':
            branch = sweep([right,(x+1.4,y,z+1.7),(x+2.7,y,z+2)],[1.05,.88,.73])
            return oval((x,y,z+1.4),(1.26,1.2,2.33)) + tip + branch + oval((x+2.7,y,z+2.95),(.85,.86,1.69))
        return oval((x,y,z+1.3),(1.99,1.73,2.05)) + tip + oval((a,b,c-1.5),(1.86,1.65,2.32))
    if gear == 'shield':
        return oval((a+.45,b-.9,c),(4.45,1.16,5.5)) + oval((a+.45,b-1.85,c),(1.68,1.11,1.73)) + sweep([right,(x+.5,y,z+4),(x+.85,y,z+7.5)],[1.02,1.33,.74])
    if gear == 'rapier':
        return sweep([right,(x+2,y-1,z+2.8),(x+4.9,y-1.6,z+7.8)],[1.1,.84,.62]) + loop(x+.39,y,z+.42,1.54,1.37,.57)
    if gear == 'mirror':
        return oval((x,y,z+2.7),(3.18,.98,3.95)) + loop(x,y-.63,z+2.65,2.76,3.45,.59)
    if gear == 'horn':
        return sweep([left,(a+.2,b-.1,c+2.1),(a-2.2,b-.6,c+3.0),(a-5,b-.8,c+3.6)],[1.02,1.16,1.52,2.04]) + oval((x,y,z+1.3),(1.43,1.08,1.66))
    raise ValueError(gear)


def figure_body(index):
    height, width, shift, hair, left, right, gear = POSES[index]
    shoulder = min(height-6.5, 21.0)
    hip = shoulder-6
    head = (shift, -.55, height-2.9)
    parts = [oval((shift,.35,hip+.8),(width*.82,2.85,3.6)),
             oval((shift,.18,shoulder-1.6),(width,3.15,4.33)),
             oval((shift,.1,shoulder+2.1),(1.72,1.74,2.7)),
             oval(head,(3.18,2.67,3.43)), oval((shift,-2.97,height-3.35),(1.02,.86,1.17))]
    for side, hand in zip((-1, 1), (left, right)):
        x = side * (3.15 if index in (3,4,5,15,16,17) else 2.6)
        y = side * (1.9 if index % 3 != 1 else -1.47)
        knee = (x+shift*.37,y*.63,hip*.54)
        parts += [oval((x,y-.7,2.85),(1.78,2.45,1.75)),
                  sweep([(x,y,3.05),knee,(shift+x*.77,.35,hip)],[1.47,1.52,1.94]),
                  sweep([(shift+side*(width-.51),.09,shoulder),
                         (hand[0]*.83,hand[1]*.47,(shoulder+hand[2])/2-2.13),hand], [1.69,1.33,1.15]),
                  oval(hand,(1.29,1.42,1.44)),
                  oval((shift+side*1.33,-2.74,height-2.17),(.85,.66,.55))]
        eye = (shift+side*1.15,-2.86,height-1.9)
        parts += [sweep([(eye[0]-side*.48,eye[1],eye[2]),eye,
                         (eye[0]+side*.76,eye[1]+.18,eye[2]+.08)],[.42,.49,.38]),
                  oval((shift+side*1.85,-2.13,height-3.83),(1.16,.97,1.43)),
                  oval((hand[0]*.95,hand[1]*.84,hand[2]+.23),(1.47,1.31,.68))]
        for band in (0,1):
            parts.append(oval((x*.98,y-.4,3.47+band*.8),(1.7,1.82,.57)))
    if index in (6,7,8,12,13,14):
        hem = [3.0,5.1,3.3,4.3,3.1,4.7][(6,7,8,12,13,14).index(index)]
        # Layer a flared robe around the feet with three raised folds.
        skirt = cyl(0,0,hem,4.25,hip-hem+.72,2.95,32).scale((1,.77,1)).translate((shift*.52,.45,0))
        parts.append(skirt)
        for offset in (-1, 0, 1):
            parts.append(sweep([(shift*.52+offset*2.33,-1.81,hem+1.1),
                                (shift*.67+offset*1.98,-2.25,hip*.77),
                                (shift+offset*1.41,-2.04,hip+.4)], [.66,.83,.68]))
    elif index in (1,2,11):
        parts.extend(oval((shift+x,1.4,hip-1.3),(1.9,2.8,6.35+x*.21)) for x in (-2.3,0,2.3))
    if index in (4,9,10,15,16,17):
        armoured_side = -1 if index in (9,15,17) else 1
        parts.append(oval((shift+armoured_side*(width-.28),.18,shoulder+.26),(2.24,2.67,1.52)))
        for row in range(3):
            z = shoulder-.74-row*1.55
            for side in (-1,1):
                parts.append(sweep([(shift,-2.97,z-.52),(shift+side*width*.61,-2.59,z),
                                    (shift+side*width*.83,-1.75,z+.58)],[.62,.76,.52]))
                parts.append(oval((shift+side*width*.45,-3.08,z-.35),(.51,.47,.54)))
    else:
        drape = -1 if index in (1,5,7,11,13) else 1
        parts.append(sweep([(shift+drape*width*.63,-1.55,shoulder+.18),(shift+drape*.7,-3.17,shoulder-2.45),
                            (shift-drape*width*.54,-2.57,hip+1.49)],[.75,.81,.61]))
        parts.append(oval((shift-drape*width*.73,-1.94,hip+.57),(1.22,1.08,1.58)))
    if index == 0:
        quiver = [(shift+1.8,2.05,hip+1),(shift+2.5,2.74,shoulder+2.6),(shift+3.9,2.22,shoulder+5.1)]
        parts.append(sweep(quiver,[1.03,1.58,.92]))
    elif index == 5:
        parts.append(oval((shift,-2.6,height-.7),(1.46,1.37,1.41)))
    elif index == 11:
        parts.append(oval((shift,-2.48,shoulder-1.0),(2.81,.95,2.39)))
    if hair in ('braid', 'bun', 'beard', 'elf', 'tusk'):
        parts.append(oval((shift,.13,height-1.27),(3.27,2.75,1.96)))
    if hair == 'hood':
        peak = 2.7 if index in (2,8) else 4.8 if index == 6 else 1.6
        parts += [oval((shift,1.08,height-1.58),(3.65,2.58,3.55)),
                  sweep([(shift,.65,height-1.0),(shift-.36,1.18,height+1.2),(shift-1.08,1.6,height+peak)], [2.02,1.47,.70])]
    elif hair == 'helm':
        parts += [oval((shift,.02,height-1),(3.67,3.34,1.98)), oval((shift,-2.41,height-1.28),(3.24,1.36,.95))]
    elif hair == 'beard':
        parts += [oval((shift+x,-2.14,height-5),(1.36,1.62,2.45-abs(x)*.23)) for x in (-1.35,0,1.35)]
    elif hair == 'braid':
        parts += [sweep([(shift+2.33,.2,height-2),(shift+3.21,1.0,height-4.8),(shift+3,1.74,height-7.8)], [1.2,1.16,.81])]
    elif hair == 'bun':
        parts.append(oval((shift,1.8,height+.1),(1.95,1.68,1.83)))
    if hair in ('elf', 'tusk') or index == 0:
        for side in (-1, 1):
            if hair == 'tusk':
                parts.append(sweep([(shift+side*1.77,-2.59,height-4.95),(shift+side*2.23,-2.9,height-3.4)], [.85,.52]))
            else:
                parts.append(sweep([(shift+side*2.37,-.54,height-3.3),(shift+side*4.47,-.32,height-1.9)], [1.02,.46]))
    parts += [oval((shift,-2.71,hip+1.96),(width*.56,.84,1.18)), equipment(gear,left,right)]
    base = cyl(0,0,0,10.45,.55,11,64) + cyl(0,0,.5,11,1.14,n=64) + cyl(0,0,1.58,11,.59,10.35,64)
    ground = oval((-6.55+.27*(index%4),3.45,2.01),(2.16,1.53,.74))
    return union([base,ground,*parts])
