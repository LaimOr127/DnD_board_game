import math,json
import numpy as np
import trimesh
from models import M,box,cyl,union,save,seen,DEST,idrel
from brom_sample import sculpt as brom
from party import heroes
from foes import foes
from hero_figures import figure_body, sweep
from foe_figures import BOSS_BADGES, FAMILY_BADGES, VARIANT_BADGES, ornament

def blob(x,y,z,rx,ry,rz,facets=24):return M.sphere(1,facets).scale((rx,ry,rz)).translate((x,y,z))
def stick(a,b,r1,r2=None,faces=16):
    v=np.subtract(b,a);length=np.linalg.norm(v);pitch=math.degrees(math.acos(v[2]/length));yaw=math.degrees(math.atan2(v[1],v[0]));return M.cylinder(length,r1,r1 if r2 is None else r2,faces).rotate((0,pitch,0)).rotate((0,0,yaw)).translate(a)
def spike(a,b,r):return sweep([a,b],[r,min(.62,r)])

def connected_body(model, code):
    shells = [shell for shell in model.decompose() if shell.volume() > 0.0001]
    if len(shells) != 1:
        raise ValueError(f'{code}: disconnected solids {[(round(s.volume(),3), s.bounding_box()) for s in shells]}')
    # Internal closed voids can be left where decorative relief meets the body.
    return shells[0]

def mini(kind, area, big, code):
    number = int(code[1:])-1
    v = number % 10
    base_radius = 11.7 if big else 11
    parts=[cyl(0,0,0,base_radius-.4,.58,base_radius,n=48),cyl(0,0,.51,base_radius,1.1,n=48),
           cyl(0,0,1.54,base_radius,.62,10.3,n=48)]
    hats={'crone':2,'mariner':3,'judge':4,'priest':4,'queen':2,'scribe':4,'ghost':6,'titan':9,'kiln':9,'tower':9,'foxsage':0,'ghoul':6,'knight':7,'skeleton':8,'golem':9}
    role = hats.get(kind)
    if role is not None:
        solid=role in [1,3,5,7,9];sx=5.1 if solid else 3.9;ht=19.8 if role==1 else 22.0;start=ht-8.6
        for s in (-1,1):
            parts+=[blob(s*2.25,-.75,2.8,2.05,3,1.5),stick((s*2.25,0,2.7),(s*1.9,0,start-2),1.7,1.9)]
        parts +=[blob(0,.25,start,sx,3,5),cyl(0,0,start-3.3,sx*.91,1.1,n=10).scale((1,.76,1)),blob(0,-.12,ht-1.3,3.7,3.2,4),blob(0,-2.25,ht-1.7,2.15,1.6,1.8)]
        for s in (-1,1):
            parts +=[blob(s*1.33,-2.72,ht-.7,.78,.68,.68),stick((s*(sx-.8),.25,start+2),(s*(sx+1.3),-.7,start-.1),1.65),stick((s*(sx+1.3),-.7,start-.1),(s*(sx+1.5),-2.4,start-.9),1.3)]
            parts += [blob(s*(sx-.53),-.34,start+1.75,1.76,1.95,1.3),
                      blob(s*(sx+1.31),-1.96,start-.69,1.38,1.32,.72),
                      blob(s*1.41,-2.7,ht-2.66,1.13,.96,1.04)]
        parts.append(blob(.08,-3.16,ht-1.24,.86,.82,1.06))
        for layer in range(3):
            parts.append(sweep([(-sx*.62,-2.15,start+1.2-layer*1.2),(0,-2.83,start+.6-layer*1.2),
                                (sx*.63,-2.18,start+1.2-layer*1.2)],[.51,.62,.51]))
        ax=sx+1.6
        if role in [0,2,4,6]:parts +=[cyl(0,1.45,4,4.6,start-1,2.25,n=9).scale((1,.74,1))]
        if role==0:
            for s in (-1,1):parts.append(spike((s*2.9,-.3,ht),(s*5.2,.15,ht+1.7),1.05))
            parts +=[blob(0,.3,ht+1.3,3.6,3,1.8),stick((ax,-2.35,start-1),(ax+1,-2.2,start+3),.82),stick((ax+1,-2.2,start+3),(ax-1,-2,start+6),.82),stick((ax,-2.35,start-1),(ax+1,-2.3,start-3),.82),stick((ax+1,-2.3,start-3),(ax-1,-2.2,start-6),.82),stick((ax-1,-2.2,start-6),(ax-1,-2,start+6),.48)]
        elif role==1:
            parts+=[blob(0,-2.6,ht-4,2.9,1.8,3.2),blob(0,.1,ht+1.15,4.1,3.35,2.3),stick((ax,-2.4,start-3),(ax+.7,-2.5,start+4.8),.85),box(ax-1.3,-4.3,start+3.8,5,3.7,3)]
        elif role in (2,4):
            parts +=[cyl(0,0,ht+.6,4.5,.9,n=12),cyl(.1,.2,ht+1.3,3.0,4.6,.3,n=8),stick((ax,-2.3,2),(ax,-2.3,ht-.1),.9),blob(ax,-2.3,ht+1,1.7,1.55,2)]
            if role==4:parts.append(box(-sx-2,-3.65,start-1.9,3,2,4.1))
        elif role in (3,7):
            parts.append(blob(0,.05,ht+1.1,4,3.4,2.4))
            if code == 'B001':
                bell = cyl(-ax,-2.46,start-3.6,2.78,4.0,1.16,n=32)
                parts.extend([bell,cyl(-ax,-2.46,start-3.75,3.01,.82,2.65,n=32),
                              sweep([(-ax,-2.46,start+.2),(-ax,-2.38,start+1.14)],[1.04,.81])])
            elif code == 'B003':
                parts.extend([sweep([(ax-1,-2.39,2.03),(ax,-2.38,start-1),(ax+1.44,-1.84,27.8)],[.98,1.05,.83]),
                              blob(ax+1.59,-1.78,27.83,2.42,1.09,3.46)])
            else:
                parts +=[blob(-ax,-2.5,start-.7,2.9,1.1,4.5,12),stick((ax,-2.4,start-2.3),(ax+.7,-2.4,ht+2),.95,.3),box(ax-1.8,-3.05,start,4,1.2,1)]
        elif role==5:
            parts +=[blob(0,-2.5,ht-2.7,3,2,1.8),stick((ax,-2.35,start-3),(ax,-2.35,ht-2),1),blob(ax+1.1,-2.3,ht-1.2,2.5,1.15,2.5)]
            for s in (-1,1):parts.append(spike((s*1.7,-3.45,ht-3),(s*2.1,-3.95,ht-.4),.95))
        elif role in (6,8):
            parts +=[blob(0,-.3,ht+.2,3.75,3.05,2.8),stick((ax,-2.3,start-.9),(ax+1.5,-3.1,start+.5),1.1,.45)]
            for j in range(3):parts.append(blob(0,-2.27,start+1.7-j*1.35,3-j*.25,1.1,.55))
        else:parts +=[blob(0,-.26,ht-1,3.75,3.29,3.6),blob(-ax,-2.3,start-1,2.2,2.2,2.5),blob(ax,-2.3,start-1,2.2,2.2,2.5)]
        head=(0,0,ht+1.5);anchor=(.7,.5,start+3.1)
    elif kind in ('wolf','cat','boar','stag'):
        for sx in (-1,1):
            for sy in (-1,1):
                stride = (.22+v*.15)*(1 if sx == sy else -1)
                paw = (sx*(3.05+v*.04),sy*4.1+stride,2.56)
                joint = (sx*2.9,sy*3.8+.74+stride*.36,5.38)
                parts += [blob(*paw,1.27,1.60,1.12),sweep([paw,joint,(sx*2.41,sy*3.11,8.2)],[.95,1.21,1.64])]
        parts.extend([blob(0,0,8.3,4.2,6.2,3.45),blob(0,-4.15,10.6,3.1,3.2,3.7),blob(0,-6.4,12.7,3.2,3.2,2.95),blob(0,-8.1,12.0,2.1,2.2,1.45),stick((0,4.3,8.8),(.7,7,10.3),1.5,1.1),stick((.7,7,10.3),(1.2,9.2,10.8 if kind=='cat' else 12),1.1,.55)])
        for s in (-1,1):
            parts.append(spike((s*1.9,-5.8,14.4),(s*2.7,-5.2,17.1),1.05));parts.append(blob(s*2.1,-8.05,13,.73,.7,.7));
            parts.append(blob(s*2.05,-7.86,11.87,1.51,1.54,1.36))
            for tuft in range(3):
                parts.append(sweep([(s*(2.36+.08*tuft),-4.9+.86*tuft,11.25-.3*tuft),
                                    (s*(3.1+.1*tuft),-4.03+.82*tuft,10.55-.53*tuft)],[.85,.59]))
            if kind=='stag':parts.extend([stick((s*1.4,-5.4,14.5),(s*3.7,-5.25,18.1),.85),stick((s*3.7,-5.25,18.1),(s*4.4,-4.5,20),.8,.3),spike((s*3.2,-5.3,17.4),(s*5.5,-5.7,18.2),.68)])
            if kind=='boar':parts.append(sweep([(s*2.3,-5.9,13.4),(s*3.7,-6.1,14.8),(s*3.8,-6.5,16.7)],[1.24,.97,.63]))
        if kind=='boar':parts.append(blob(0,-1.6,10.3,4.65,4.4,4.5))
        if kind=='wolf' and not big and number//10 == 21:
            parts.append(sweep([(0,4.3,8.8),(.65,6.5,9.6),(1.8,9.3,11.9),(2.6,10.2,14.1)],[1.52,1.86,1.57,.91]))
        head=(0,-6.25,14.25);anchor=(0,0,10.4)
    elif kind in ('crab','spider','beetle','centipede','mantis'):
        parts+=[blob(0,0,6.1,4.7,5.4,3.2),blob(0,-4.15,6.15,3.0,2.7,2.4)]
        for i in range(3):
            parts.append(blob(0,-.7+i*1.54,7.33,4.1-i*.35,1.37,1.42))
        for s in (-1,1):
            for i in range(4 if kind in ('spider','centipede') else 3):
                y=(i-1.4)*2.1;a=(s*3,y,6);b=(s*(6.2+.25*i),y+.3,5);end=(s*(7.5+.1*i),y-1.1,1.9);parts.extend([stick(a,b,.9),stick(b,end,.9,.65)])
            if kind in ('crab','mantis'):parts.extend([stick((s*3,-3.25,6.1),(s*5.8,-6.4,8.1),1.2),blob(s*5.8,-6.45,8.7,1.9,2.4,1.7),spike((s*5.2,-7.3,9.3),(s*4.8,-9,10.4),.75)])
            parts.append(blob(s*1.35,-5.49,7.64,.82,.81,.79))
        if kind=='beetle':parts.append(spike((0,-4.7,7.7),(0,-7.5,11),1.1))
        if kind=='centipede':parts.extend([blob(0,4+i*1.55,5.55-i*.55,2.4-i*.35,2.4-i*.35,1.6) for i in range(3)])
        head=(0,-4.2,7.65);anchor=(0,0,8.65)
    elif kind in ('moth','ray','bird','bat','fish'):
        parts.extend([stick((0,.7,1.9),(0,0,7.5),2.1,1.6),blob(0,0,10.1,2.9,4,3.6),blob(0,-2.6,12.2,2.1,2.25,2.15)])
        for s in (-1,1):
            parts.extend([stick((s*1.65,0,10.5),(s*4.5,.25,11.8),1.85),blob(s*5.6,.55,12.45,4.5,2.2,1.65).rotate((0,0,0)),spike((s*7,.4,12.65),(s*10.1,1.9,15.3 if kind in ('moth','bat') else 13.25),1.45)])
            if kind=='moth':parts.append(stick((s*.65,-3,13.3),(s*2.1,-3.9,16.3),.55,.35))
            for j in range(3):
                parts.append(sweep([(s*(3.1+j*.96),.55,12.6),(s*(4.3+j*1.03),1.68,12.32),
                                    (s*(4.6+j*1.07),2.08,11.78)], [.53,.51,.49]))
        parts.append(spike((0,2.6,10),(0,6.8,9.4),1.65));
        if kind=='bird':parts.append(spike((0,-4.1,12.35),(0,-6.7,12.1),1.1))
        if kind=='fish':parts.append(spike((0,.7,12.3),(0,2,16),1.3))
        head=(0,-2.4,13.6);anchor=(0,.5,12.6)
    elif kind=='serpent':
        pts=[(0,5.5,2.9),(-4.3,4.6,4),(-5,1.2,4.4),(-2.5,-1.6,5.1),(1,-1.4,6.5),(3.25,0,9.5),(2.7,.2,12.2),(.7,-1.8,14.6)];
        for i,(a,b) in enumerate(zip(pts,pts[1:])):parts.extend([stick(a,b,2.1 if i else 1.7,2.1),blob(*b,2.1,2.1,2.1)])
        parts.extend([blob(.4,-2.9,14.7,2.7,3.2,1.9),blob(.4,-4.8,14.3,2.1,2,1.1)]);head=(.4,-2.9,15.7);anchor=(2.7,.2,12.7)
        for p in pts[3:]:
            parts.append(blob(p[0],p[1]+.85,p[2]+.92,1.43,1.35,.97))
    elif kind=='tree':
        parts.extend([cyl(0,0,1.7,3.9,12,2.3,n=7),blob(0,-.25,13,2.85,2.65,3.4)])
        for s in (-1,1):
            parts.extend([stick((s*.8,0,8),(s*4.1,-.1,10),1.55),stick((s*4.1,-.1,10),(s*5.9,0,14.2),1.1,.6),blob(s*5.6,.3,14.7,2.8,2.3,2.4),stick((s*.65,0,12),(s*2.5,1,17.6),1.2,.65),blob(s*2.5,1,17.8,2.8,2.25,2.2)])
            parts.append(sweep([(s*2.1,-2.16,3.5),(s*2.27,-2.56,7.9),(s*1.65,-2.18,11.55)],[.83,.75,.61]))
        head=(0,0,14.4);anchor=(0,-.15,14)
    else:raise ValueError(kind)
    if big:
        shape = BOSS_BADGES[area].split()[v]
        x,y,z = head
        parts.append(ornament(shape,(x,y,z-.9),1.30))
        ax,ay,az = anchor
        parts.append(ornament(('ridge','fan','split','hood','crest')[area % 5], (ax,ay+.35,az-1.25),.95+v*.035))
    else:
        ax,ay,az = anchor
        parts.append(ornament(FAMILY_BADGES[number//10], (ax,ay,az-1.5),.91))
        x,y,z = head
        parts.append(ornament(VARIANT_BADGES[v], (x,y,z-1.05),.64+v*.045))
    model = union(parts)
    # Bend the pose above the base so adjacent variants stay readable in one colour.
    top = model.bounding_box()[5]
    lean = [-1.5,2.9,-3.1,-.65,1.55,-2.2,3.2,-2.85,1.9,.7][v] + (area-4.5)*.15
    spread = [1, .97, 1.18, 1.05, 1.29, .93, .91, 1.13, 1.19, 1.07][v]
    rise = [1, .94, .88, 1.13, .83, 1.05, 1.05, .98, 1.12, 1.19][v]
    def pose(point):
        x,y,z = point
        t = max(0,z-2.16)/(top-2.16)
        return (x*(1+(spread-1)*t)+lean*t, y*(1+(1-spread)*.48*t)+(v%3-1)*1.23*t,
                z+(rise-1)*(top-2.16)*t)
    model = connected_body(model.warp(pose) + idrel(code,.30,-3.7,-8.6,2.03),code)
    height = model.bounding_box()[5]
    if big:
        return model.scale((1.32, 1.32, min(1.43, 49 / height)))
    return model.scale((1.12, 1.12, max(1.16, 16 / height)))


def save_figure(group, key, model):
    _, _, bottom, _, _, top = model.bounding_box()
    if abs(bottom) > 1e-5 or top > 50:
        raise ValueError(f'{key}: expected a seated base and height at most 50 mm, got {bottom:g}–{top:g}')
    save(group, key, model)
    path = DEST/group/(key+'.stl')
    mesh = trimesh.load_mesh(path)
    if mesh.is_volume:
        return
    # STL stores float32. Tangent surfaces can collapse to zero-volume sheets on export.
    components = sorted(mesh.split(only_watertight=False),key=lambda shell: shell.area,reverse=True)
    if not (components and components[0].is_volume and all(abs(shell.volume) < 1e-6 and shell.area < .1
                                                           for shell in components[1:])):
        raise ValueError(f'{key}: invalid geometry after STL round trip')
    path.write_bytes(components[0].export(file_type='stl'))


def main():
    mobs,boss=foes()
    for i in range(len(heroes)):
        key = f'H{i+1:02}'
        shape = brom() if key == 'H04' else connected_body(figure_body(i) + idrel(key,.32,-3.70,-8.6,2.085),key).scale((1.18,)*3)
        save_figure('объёмные герои',key,shape)
    for isboss,ls in [(False,mobs),(True,boss)]:
        for z in ls:save_figure('объёмные боссы' if isboss else 'объёмные существа',z['id'],mini(z['body'],z['area'],isboss,z['id']))
    meta=DEST/'размеры-мм.json';base=json.loads(meta.read_text(encoding='utf8'));base.update(seen);meta.write_text(json.dumps(base,ensure_ascii=False,indent=1),encoding='utf8');print('Объёмных фигур:',len(seen))
if __name__=='__main__':main()
