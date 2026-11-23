import math,json
import numpy as np
from models import M,box,cyl,union,save,seen,DEST,profile,idrel
from party import heroes
from foes import foes

def blob(x,y,z,rx,ry,rz,facets=12):return M.sphere(1,facets).scale((rx,ry,rz)).translate((x,y,z))
def stick(a,b,r1,r2=None,faces=9):
    v=np.subtract(b,a);length=np.linalg.norm(v);pitch=math.degrees(math.acos(v[2]/length));yaw=math.degrees(math.atan2(v[1],v[0]));return M.cylinder(length,r1,r1 if r2 is None else r2,faces).rotate((0,pitch,0)).rotate((0,0,yaw)).translate(a)
def spike(a,b,r):return stick(a,b,r,.23,6)
def crown(x,y,z,rr):
    parts=[cyl(x,y,z,rr,1.5,n=10)]
    for i in range(5):
        th=i*2*math.pi/5;px=x+(rr-.65)*math.cos(th);py=y+(rr-.65)*math.sin(th);parts.append(spike((px,py,z+1),(px+.2*math.cos(th),py+.2*math.sin(th),z+3.2),.85))
    return parts

def mini(kind,seed,area,big,hero=False,code=None):
    parts=[cyl(0,0,0,10.8,1.3,11,n=28),cyl(0,0,1.2,11,.9,10.3,n=28)];v=seed%10;hats={'crone':2,'mariner':3,'judge':4,'priest':4,'queen':2,'scribe':4,'ghost':6,'titan':9,'kiln':9,'tower':9,'foxsage':0,'ghoul':6,'knight':7,'skeleton':8,'golem':9};role=int(kind[-1]) if hero else hats.get(kind)
    if role is not None:
        solid=role in [1,3,5,7,9];sx=5.1 if solid else 3.9;ht=19.8 if role==1 else 22.0;start=ht-8.6
        for s in (-1,1):
            parts+=[blob(s*2.25,-.75,2.8,2.05,3,1.5),stick((s*2.25,0,2.7),(s*1.9,0,start-2),1.7,1.9)]
        parts +=[blob(0,.25,start,sx,3,5),cyl(0,0,start-3.3,sx*.91,1.1,n=10).scale((1,.76,1)),blob(0,-.12,ht-1.3,3.7,3.2,4),blob(0,-2.25,ht-1.7,2.15,1.6,1.8)]
        for s in (-1,1):
            parts +=[blob(s*1.33,-2.72,ht-.7,.78,.68,.68),stick((s*(sx-.8),.25,start+2),(s*(sx+1.3),-.7,start-.1),1.65),stick((s*(sx+1.3),-.7,start-.1),(s*(sx+1.5),-2.4,start-.9),1.3)]
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
            parts +=[blob(0,.05,ht+1.1,4,3.4,2.4),blob(-ax,-2.5,start-.7,2.9,1.1,4.5,12),stick((ax,-2.4,start-2.3),(ax+.7,-2.4,ht+2),.95,.3),box(ax-1.8,-3.05,start,4,1.2,1)]
        elif role==5:
            parts +=[blob(0,-2.5,ht-2.7,3,2,1.8),stick((ax,-2.35,start-3),(ax,-2.35,ht-2),1),blob(ax+1.1,-2.3,ht-1.2,2.5,1.15,2.5)]
            for s in (-1,1):parts.append(spike((s*1.7,-3.45,ht-3),(s*2.1,-3.95,ht-.4),.95))
        elif role in (6,8):
            parts +=[blob(0,-.3,ht+.2,3.75,3.05,2.8),stick((ax,-2.3,start-.9),(ax+1.5,-3.1,start+.5),1.1,.45)]
            for j in range(3):parts.append(blob(0,-2.27,start+1.7-j*1.35,3-j*.25,1.1,.55))
        else:parts +=[box(-3.3,-2.85,ht-3.5,6.6,5.7,6),blob(-ax,-2.3,start-1,2.2,2.2,2.5),blob(ax,-2.3,start-1,2.2,2.2,2.5)]
        if hero and seed%3==1:parts.append(blob(-sx-.2,-2.3,start+1.35,1.8,1.4,1.4))
        if hero and seed%3==2:parts.extend([stick((-ax,-2.4,start-2),(-ax,-2.4,ht+1.3),.65),box(-ax-.2,-2.75,ht-1.1,3,.8,2.4)])
        head=(0,0,ht+1.5);anchor=(.7,.5,start+3.1)
    elif kind in ('wolf','cat','boar','stag'):
        for sx in (-1,1):
            for sy in (-1,1):parts.append(stick((sx*3,sy*4.1,1.9),(sx*2.5,sy*3.1,8.1),1.18,1.6))
        parts.extend([blob(0,0,8.3,4.2,6.2,3.45),blob(0,-4.15,10.6,3.1,3.2,3.7),blob(0,-6.4,12.7,3.2,3.2,2.95),blob(0,-8.1,12.0,2.1,2.2,1.45),stick((0,4.3,8.8),(.7,7,10.3),1.5,1.1),stick((.7,7,10.3),(1.2,9.2,10.8 if kind=='cat' else 12),1.1,.55)])
        for s in (-1,1):
            parts.append(spike((s*1.9,-5.8,14.4),(s*2.7,-5.2,17.1),1.05));parts.append(blob(s*2.1,-8.05,13,.73,.7,.7));
            if kind=='stag':parts.extend([stick((s*1.4,-5.4,14.5),(s*3.7,-5.25,18.1),.85),stick((s*3.7,-5.25,18.1),(s*4.4,-4.5,20),.8,.3),spike((s*3.2,-5.3,17.4),(s*5.5,-5.7,18.2),.68)])
            if kind=='boar':parts.append(spike((s*1.4,-8.55,11.7),(s*2.5,-9.1,13.6),.75))
        head=(0,-6.25,14.6);anchor=(0,0,10.8)
    elif kind in ('crab','spider','beetle','centipede','mantis'):
        parts+=[blob(0,0,6.1,4.7,5.4,3.2),blob(0,-4.15,6.15,3.0,2.7,2.4)]
        for s in (-1,1):
            for i in range(4 if kind in ('spider','centipede') else 3):
                y=(i-1.4)*2.1;a=(s*3,y,6);b=(s*(6.2+.25*i),y+.3,5);end=(s*(7.5+.1*i),y-1.1,1.9);parts.extend([stick(a,b,.9),stick(b,end,.9,.65)])
            if kind in ('crab','mantis'):parts.extend([stick((s*3,-3.25,6.1),(s*5.8,-6.4,8.1),1.2),blob(s*5.8,-6.45,8.7,1.9,2.4,1.7),spike((s*5.2,-7.3,9.3),(s*4.8,-9,10.4),.75)])
        if kind=='beetle':parts.append(spike((0,-4.7,7.7),(0,-7.5,11),1.1))
        if kind=='centipede':parts.extend([blob(0,4+i*1.55,5.55-i*.55,2.4-i*.35,2.4-i*.35,1.6) for i in range(3)])
        head=(0,-4.2,7.65);anchor=(0,0,8.65)
    elif kind in ('moth','ray','bird','bat','fish'):
        parts.extend([stick((0,.7,1.9),(0,0,7.5),2.1,1.6),blob(0,0,10.1,2.9,4,3.6),blob(0,-2.6,12.2,2.1,2.25,2.15)])
        for s in (-1,1):
            parts.extend([stick((s*1.65,0,10.5),(s*4.5,.25,11.8),1.85),blob(s*5.6,.55,12.45,4.5,2.2,1.65).rotate((0,0,0)),spike((s*7,.4,12.65),(s*10.1,1.9,15.3 if kind in ('moth','bat') else 13.25),1.45)])
            if kind=='moth':parts.append(stick((s*.65,-3,13.3),(s*2.1,-3.9,16.3),.55,.35))
        parts.append(spike((0,2.6,10),(0,6.8,9.4),1.65));
        if kind=='bird':parts.append(spike((0,-4.1,12.35),(0,-6.7,12.1),1.1))
        if kind=='fish':parts.append(spike((0,.7,12.3),(0,2,16),1.3))
        head=(0,-2.4,13.6);anchor=(0,.5,12.6)
    elif kind=='serpent':
        pts=[(0,5.5,2.9),(-4.3,4.6,4),(-5,1.2,4.4),(-2.5,-1.6,5.1),(1,-1.4,6.5),(3.25,0,9.5),(2.7,.2,12.2),(.7,-1.8,14.6)];
        for i,(a,b) in enumerate(zip(pts,pts[1:])):parts.extend([stick(a,b,2.1 if i else 1.7,2.1),blob(*b,2.1,2.1,2.1)])
        parts.extend([blob(.4,-2.9,14.7,2.7,3.2,1.9),blob(.4,-4.8,14.3,2.1,2,1.1)]);head=(.4,-2.9,15.7);anchor=(2.7,.2,12.7)
    elif kind=='tree':
        parts.extend([cyl(0,0,1.7,3.9,12,2.3,n=7),blob(0,-.25,13,2.85,2.65,3.4)])
        for s in (-1,1):
            parts.extend([stick((s*.8,0,8),(s*4.1,-.1,10),1.55),stick((s*4.1,-.1,10),(s*5.9,0,14.2),1.1,.6),blob(s*5.6,.3,14.7,2.8,2.3,2.4),stick((s*.65,0,12),(s*2.5,1,17.6),1.2,.65),blob(s*2.5,1,17.8,2.8,2.25,2.2)])
        head=(0,0,14.4);anchor=(0,-.15,14)
    else:raise ValueError(kind)
    if not hero:
        for i in range(v%3+1):
            ax,ay,az=anchor;dx=(i-(v%3)/2)*.89;parts.append(spike((ax+dx,ay,az-.65),(ax+dx*1.25,ay+.4,az+1.6+(v//3)*.52),.83))
        # Relief pips on the rear of the base identify rank by touch.
        for k in range(seed%5+1):parts.append(cyl(k*1.55-3.1,8.25,1.75,.57,.75,n=8))
    if big:
        x,y,z=head;parts+=crown(x,y,z-1.0,2.65);parts.append(cyl(0,0,0,11.7,.7,11.2,n=28))
    if code:parts.append(idrel(code,.30,-3.7,-8.6,2.03))
    model=union(parts)
    if big:model=model.scale([1.28]*3)
    return model

def main():
    mobs,boss=foes()
    for i in range(len(heroes)):save('объёмные герои',f'H{i+1:02}',mini('hero'+str(i//3),i,i//3,False,True,f'H{i+1:02}'))
    for isboss,ls in [(False,mobs),(True,boss)]:
        for z in ls:save('объёмные боссы' if isboss else 'объёмные существа',z['id'],mini(z['body'],z['seed'],z['area'],isboss,code=z['id']))
    meta=DEST/'размеры-мм.json';base=json.loads(meta.read_text(encoding='utf8'));base.update(seen);meta.write_text(json.dumps(base,ensure_ascii=False,indent=1),encoding='utf8');print('Объёмных фигур:',len(seen))
if __name__=='__main__':main()
