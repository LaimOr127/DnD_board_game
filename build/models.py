from pathlib import Path
import numpy as np, manifold3d as md, trimesh, math, json
from PIL import Image,ImageDraw
from art import sprite,icon
from world import realms
from party import heroes,items
from foes import foes
from maps import OUT,font
M=md.Manifold;CS=md.CrossSection
DEST=OUT/'3D';DEST.mkdir(exist_ok=True)
def box(x,y,z,w,d,h):return M.cube([w,d,h]).translate([x,y,z])
def cyl(x,y,z,r,h,r2=None,n=24):return M.cylinder(h,r,r if r2 is None else r2,n).translate((x,y,z))
def profile(points,height):return CS([points],md.FillRule.EvenOdd).extrude(height)
def union(parts):return M.batch_boolean(parts,md.OpType.Add)
seen={}
def save(group,name,m):
    where=DEST/group;where.mkdir(exist_ok=True);q=m.to_mesh();obj=trimesh.Trimesh(np.array(q.vert_properties[:,:3]),np.array(q.tri_verts),process=False);assert m.status()==md.Error.NoError and m.volume()>.01 and len(m.decompose())==1,(name,m.status(),len(m.decompose()));(where/(name+'.stl')).write_bytes(obj.export(file_type='stl'));seen[group+'/'+name]=[round(float(x),1) for x in obj.extents]

def relief(mask,scale,height,z=0,offset=(0,0)):
    paths=[];h,w=mask.shape
    for y,row in enumerate(mask):
        ids=np.flatnonzero(np.diff(np.r_[False,row,False].astype(int))); yy=(h-y-1)*scale+offset[1];
        for l,r in zip(ids[::2],ids[1::2]):
            a=l*scale+offset[0];b=r*scale+offset[0];paths.append([(a,yy),(b,yy),(b,yy+scale),(a,yy+scale)])
    return CS(paths).offset(.035 if z<2 else .018,md.JoinType.Miter).extrude(height).translate((0,0,z)) if paths else M()

def idrel(code,scale,x,y,z):
    import PIL.ImageFont as pf
    f=pf.load_default(size=11);a=Image.new('1',(32,14));ImageDraw.Draw(a).text((1,-1),code,font=f,fill=1,stroke_width=0);a=a.crop(a.getbbox());return relief(np.asarray(a),scale,.48,z,(x,y))

def pawn(art,code,big=False):
    a=np.asarray(art);mask=a[:,:,3]>0;s=.46 if big else .38;w=68*s;h=58*s;ww=w*.5; yy=h*.78
    poly=[(2,0),(w-2,0),(w,2),(w,yy),(w*.79,h-1),(ww,h+1),(w*.21,h-1),(0,yy),(0,2)];plate=profile(poly,1.8);tab=box(ww-6,-3.5,0,12,4,1.8);lum=a[:,:,:3].astype(float).mean(axis=2);low=relief(mask,s,.66,1.74);high=relief(mask&(lum>110),s,.55,2.34)
    # Use the crest above the tab; trim the illustration where it meets a bevel.
    shell=profile(poly,3.2);rel=(low+high)^shell;plaque=box(ww-6,.3,1.7,12,3.8,.86);letters=idrel(code,.36,ww-5.0,.45,2.50);return union([plate,tab,rel,plaque,letters])

def token(kind,seed,name):
    a=np.asarray(icon(kind,seed));mask=a[:,:,3]>0;s=.46;w=48*s;bg=cyl(w/2,w/2,0,12,1.8,n=48);return union([bg,relief(mask,s,.65,1.75),relief(mask&(a[:,:,:3].astype(float).mean(axis=2)>125),s,.55,2.33)])

def house(x,y,k=1):
    w=9*k;dep=10*k;base=box(x,y,0,w,dep,6*k);pts=[(0,0),(w+2*k,0),((w+2*k)/2,5*k)];roof=profile(pts,dep+2*k).rotate((90,0,0)).translate((x-k,y+dep+k,5.8*k));return union([base,roof,box(x+w*.4,y-.3*k,0,2*k,.6*k,4*k),box(x+w*.75,y+dep*.64,5*k,1.7*k,2*k,4.5*k)])
def tower(x,y,r,h,spire=False):
    parts=[cyl(x,y,0,r,h,n=12),cyl(x,y,h-1,r+1,1.4,n=12)];
    if spire:parts.append(cyl(x,y,h,r+1,6,0,n=12))
    else:
        for j in range(6):
            t=math.pi*j/3;parts.append(box(x+(r-.7)*math.cos(t)-.8,y+(r-.7)*math.sin(t)-.8,h,1.8,1.8,1.9))
    return union(parts)
def castle(i):
    rr=12+i%3;parts=[cyl(0,0,0,rr+4,1.5,n=12),box(-9,-6,1,18,12,5),tower(0,2,3.4,11+i%4,i%2==0)];
    for j,(x,y) in enumerate([(-9,-6),(9,-6),(9,6),(-9,6)]):parts.append(tower(x,y,2.7,6+((i+j)%3),bool((i>>j)&1)))
    parts.append(box(-3,-8,1,6,4,6));return union(parts)-box(-1.5,-9,1.5,3,4,3.4)
def terrain():
    trees=[cyl(0,0,0,12,1.3,n=18)]
    for x,y,h in [(-4,0,14),(3.5,3,18),(3,-4,11)]:
        trees +=[cyl(x,y,1,1.2,h*.7),cyl(x,y,3,4,h*.6,.3,n=8),cyl(x,y,h*.4,3,h*.6,0,n=8)]
    rocks=[cyl(0,0,0,14,1.5,n=13),cyl(-4,0,1,9,17,0,n=5),cyl(5,1,1,8,12,0,n=6),cyl(3,-5,1,6,8,0,n=5)]
    arch=(box(-9,-2,0,18,4,15)-box(-5,-3,0,10,6,10))-cyl(0,0,0,4.9,6,n=32).rotate((90,0,0)).translate((0,3,9));arch=union([arch,cyl(0,0,0,10,1.6,n=24),box(-2,-2.5,12,4,5,4)])
    cave=(cyl(0,0,0,13,12,6,n=9)-box(-4,-14,0,8,13,6))+cyl(0,0,0,13,1,n=12)
    lake=cyl(0,0,0,13,1.4,n=20).scale((1,.72,1));lake=lake+(cyl(0,0,1.35,12,1,n=20)-cyl(0,0,1,10.8,3,n=20)).scale((1,.72,1))
    field=box(0,0,0,22,17,1.5)
    for i in range(6):field+=box(2+i*3,1,1.4,1.25,15,1)
    sea_=box(0,0,0,22,16,1.2)
    for i in range(3):sea_+=profile([(1,2+i*4),(8,3+i*4),(14,2+i*4),(21,3+i*4),(21,4+i*4),(14,3+i*4),(8,4+i*4),(1,3+i*4)],1.6)
    return dict(forest=union(trees),mountain=union(rocks),portal=arch,cavern=cave,lake=lake,field=field,sea=sea_,house=house(0,0),village=union([cyl(0,0,0,16,1.6),house(-11,-5,.8),house(1,-2),house(-4,6,.6)]),city=union([cyl(0,0,0,18,1.5),house(-10,-7),house(2.4,-10.4,.78),tower(2,5,5,14,True),tower(-8.4,6.7,3,8)]))

def siege():
    base=box(-11,-7,0,22,14,1.8);wheels=[]
    for x in [-6,6]:
        for y in [-4,6]:wheels.append(cyl(0,0,0,3,2,n=12).rotate((90,0,0)).translate((x,y,3.3)))
    carriage=box(-8,-3,1.6,16,6,4);b=cyl(0,0,0,2.8,14,3.5,n=12).rotate((0,77,0)).translate((-6,0,5.2));end=cyl(0,0,0,1.25,.7,n=10).rotate((0,77,0)).translate((7.3,0,8.25));bomb=union([base,carriage,b]+wheels)-end
    frame=profile([(0,0),(10,0),(5,8)],2).rotate((90,0,0));beam=box(-7,-1.4,0,15,2.8,2.6).rotate((0,-28,0)).translate((0,0,7));basket=cyl(5.6,0,10.4,3,2,3.8,n=10);cat=union([base,carriage,frame.translate((-5,3.0,2)),frame.translate((-5,-1,2)),beam,basket]+wheels);return bomb,cat

def board():
    a=box(0,0,0,150,105,2.6);a+=box(1,1,2.5,148,2,2);a+=box(1,2,2.5,2,98,2);a+=box(147,2,2.5,2,98,2)
    for x,y,w,dep in [(5,5,93,67),(99,6,45,31),(99,39,45,31)]:
        frame=box(x,y,2.5,w,dep,2.2)-box(x+1.5,y+1.5,2,w-3,dep-3,4)-box(x+w/2-7,y-1,2,14,4,4);a+=frame
    for y in [80,83.6,94,97.6]:a+=box(6,y,2.5,138,2,6)
    b=box(0,0,0,150,105,2.6)
    for y in [11,39,67]:
        for yy in [y,y+3.8]:b+=box(5,yy,2.5,140,2,7)
    for x in [8,32,56,80,104,128]:b+=cyl(x,92,2.5,6,1.2,n=16)
    return a,b

def main():
    mobs,bosses=foes()
    for i,h in enumerate(heroes):k=f'H{i+1:02}';save('герои',k,pawn(sprite('hero'+str(i//3),i,i//3),k))
    for big,ls in [(False,mobs),(True,bosses)]:
        for rec in ls:save('боссы' if big else 'существа',rec['id'],pawn(sprite(rec['body'],rec['seed'],rec['area'],big),rec['id'],big))
    for i,it in enumerate(items):save('снаряжение',f'I{i+1:02}',token(it[4],i,it[0]))
    for i,realm in enumerate(realms):save('местность',f'K{i+1:02}',castle(i))
    for i in range(10):
        tile=cyl(0,0,0,16,1.3,n=6+i%5);parts=[tile,house(-9,-5,.75+i%3*.1),house(1,-3,.68+(i//3)*.08)]
        if i%3==0:parts.append(tower(0,7,2.8,7+i/3,True))
        elif i%3==1:parts.append(house(-2,5,.52))
        else:parts.append(cyl(1,8,.8,3.3,6+i/3,0,n=7))
        save('местность',f'V{i+1:02}',union(parts))
    for i in range(5):
        floor=box(0,0,0,38,38,2);floor+=box(0,0,1.8,13,2,5+i);floor+=box(24,0,1.8,14,2,5+i);floor+=box(0,0,1.8,2,12,5+i);floor+=box(0,24,1.8,2,14,5+i)
        for j in range(i+1):floor+=box(25+j*2,24,1.9,2.1,10,.7+j*.65)
        save('местность',f'depth-{i+1}',floor)
    save('местность','gate',union([box(-12,-3,0,24,6,1.2),tower(-9,0,3.1,10),tower(9,0,3.1,10),box(-8,-2.2,6.8,16,4.4,3)]))
    save('местность','wall',union([box(0,0,0,29,7,1.3),box(0,2,1,29,3,7)]+[box(3*j,2,7.8,1.7,3,2) for j in range(10)]))
    store=box(0,0,0,72,96,34)-box(2.2,2.2,2,67.6,91.6,34);lid=box(0,0,0,77.2,101.2,6)-box(2,2,1.8,73.2,97.2,6);save('планшет','card-box',store);save('планшет','card-lid',lid)
    for name,model in terrain().items():save('местность',name,model)
    for name,model in zip(['bombard','catapult'],siege()):save('местность',name,model)
    a,b=board();save('планшет','A-hero',a);save('планшет','B-loadout',b)
    stand=cyl(0,0,0,9.5,4,n=32)-box(-6.35,-1.15,.45,12.7,2.3,4);save('планшет','base-slot',stand);save('планшет','fit-test',box(0,0,0,12,8,1.8))
    for name,kind,seed in [('health-1','heart',0),('spark','spark',2),('supply','knot',4),('ward','rune',2),('danger','eye',1)]:save('жетоны',name,token(kind,seed,name))
    for name,mark in [('health-5',5),('max-health',0)]:
        disk=token('heart',0,name)
        if mark:
            for j in range(5):disk+=cyl(7+j*2,11,1.7,.7,1.9,n=10)
        else:disk=disk-cyl(11,11,-1,2.2,7,n=20)
        save('жетоны',name,disk)
    (DEST/'размеры-мм.json').write_text(json.dumps(seen,ensure_ascii=False,indent=1),encoding='utf8');print('STL:',len(seen),flush=True)
if __name__=='__main__':main()
