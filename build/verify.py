import sys,json,random,statistics,math,hashlib
from pathlib import Path
import numpy as np,trimesh,pymupdf
from PIL import Image,ImageDraw,ImageOps
from printkit import OUT,ROOT,cards,MOBS,BOSSES,heroes,items,schools
from world import realms,edges,acts,endings
from edicts import edicts
from extras import local
from appendix import levels

def sim(n,t,seed):
    rng=random.Random(seed);wins=[];down=[];rounds=[]
    for run in range(500):
        hp=[8+2*(t-1)]*n;bhp=(5+2*t+max(0,t-2))*n;drops=0;lastround=0
        for rd in range(1,41):
            lastround=rd
            for i in range(n):
                if hp[i]<=0:continue
                roll=rng.randint(1,6)+rng.randint(1,6)
                if roll!=2 and (roll==12 or roll+2+t-1>=7+t):bhp-=2+t-1
                if bhp<=0:break
            if bhp<=0:break
            already=set()
            for _ in range(n//2 if rd==1 else (n+1)//2):
                targets=[i for i in range(n) if hp[i]>0 and i not in already]
                if not targets:break
                target=min(targets,key=lambda i:(hp[i],i));already.add(target);roll=rng.randint(1,6)+rng.randint(1,6)
                if roll!=2 and (roll==12 or roll+t+1>=9):
                    hp[target]-=3+(t-1)//2+int(t>=4)
                    if hp[target]<=0:drops+=1
            if max(hp)<=0:break
        wins.append(bhp<=0);rounds.append(lastround);down.append(drops>0)
    return dict(герои=n,ступень=t,партий=500,победы_проц=round(100*statistics.mean(wins),1),хотя_бы_одно_падение_проц=round(100*statistics.mean(down),1),медиана_раундов=statistics.median(rounds))

def main():
    assert len(cards)==458 and len(heroes)==18 and len(items)==40 and len(MOBS)==300 and len(BOSSES)==100
    assert len(set(z['name'] for z in MOBS+BOSSES))==400 and len({(z['ability'],z['trait']) for z in MOBS})==300 and len({z['decree'] for z in BOSSES})==100
    assert all(len(v)==15 for v in realms) and all(len(v)==7 for v in local) and len(realms)==10 and len(endings)==8
    assert all(sorted(h[2])==['0','1','2'] for h in heroes); assert all(int(h[2][({'Мощь':0,'Ловкость':1,'Воля':2}[items[int(h[3])-1][3].split(',')[0]])])==2 for h in heroes)
    avail={1}
    for _ in range(10):avail|={b for a,b in edges if a in avail}|{a for a,b in edges if b in avail}
    assert len(avail)==10
    for a in range(10):
        for tier in range(1,6):assert len([b for b in BOSSES if b['area']==a and b['t']==tier])==2 and len([b for b in MOBS if b['area']==a and b['t']==tier])==6
    spatial={p.stem for p in (OUT/'3D').rglob('*.stl')};images={p.stem for p in (OUT/'Карточки PNG').rglob('*.png')};assert set(cards)==images and set(cards)<=spatial
    faults=[];geom=list((OUT/'3D').rglob('*.stl'));assert len(geom)==928;assert all((OUT/'3D'/group/(key+'.stl')).exists() for key in cards if key[0] in 'HMB' for group in [{'H':'объёмные герои','M':'объёмные существа','B':'объёмные боссы'}[key[0]]])
    for p in geom:
        mesh=trimesh.load_mesh(p)
        if not (mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0 and np.isfinite(mesh.vertices).all()):faults.append(p.parent.name+'/'+p.name)
    if faults:raise AssertionError(('STL',len(faults),faults))
    expected=[7,14,27,8,2,34,12,5,8];pdfs=sorted(OUT.glob('*.pdf'));assert len(pdfs)==9;pagecounts={};tmp=ROOT/'qa-temp';tmp.mkdir(exist_ok=True);allthumb=[]
    for ix,p in enumerate(pdfs):
        d=pymupdf.open(p);assert len(d)==expected[ix],(p,len(d));pagecounts[p.name]=len(d);alltext=''
        for pi,pg in enumerate(d):
            alltext+=pg.get_text();pix=pg.get_pixmap(matrix=pymupdf.Matrix(.33,.33),alpha=False);ar=np.frombuffer(pix.samples,'uint8').reshape(pix.height,pix.width,3);assert ar.std()>9,(p,pi);allthumb.append((p.stem[:2]+'.'+str(pi+1),Image.fromarray(ar)))
        if ix in [4,5,6,7]:
            pref=['H','M','B','I'][ix-4];assert all(k in alltext for k in cards if k[0]==pref),(p,'missing card')
        if ix in [0,1,2]:assert 'МОРЕ' in alltext and '□' not in alltext
        d.close()
    for k in range(0,len(allthumb),40):
        sel=allthumb[k:k+40];sheet=Image.new('RGB',(1000,math.ceil(len(sel)/8)*163),'#c9c4b4');dr=ImageDraw.Draw(sheet)
        for j,(tag,im) in enumerate(sel):
            pic=ImageOps.contain(im,(118,143));x=(j%8)*125;y=(j//8)*163;sheet.paste(pic,(x,y));dr.text((x,y+143),tag,fill='black')
        sheet.save(tmp/f'all-{k}.jpg')
    simulations=[sim(n,t,n*971+t) for n in range(2,7) for t in [1,3,5]]
    res={'контент':{'герои':18,'обычные':300,'боссы':100,'вещи':40,'королевства':10,'народы':10,'регионы_связны':True,'финалы':8,'местные_контракты':30,'главы':5},'проверка':{'файлы_STL':len(geom),'открытые_рёбра_или_плохой_обход':len(faults),'карточки_PNG':len(images),'страницы_PDF':pagecounts,'все_страницы_отрисованы':True},'модель':'Условный неподвижный босс; все бьют штатным оружием по сильной характеристике, фокус врага по раненому. Без рун, лечения, брони, критической искры, особенностей, сигналов, движения и переговоров. Проверяет только базовую арифметику боя. Это не плейтест.','моделирование':simulations};(OUT/'Проверка.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(res,ensure_ascii=False,indent=1))
if __name__=='__main__':main()
