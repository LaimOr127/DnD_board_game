import sys,json,random,statistics,math,hashlib
from pathlib import Path
import numpy as np,trimesh,pymupdf,manifold3d
from PIL import Image,ImageDraw,ImageOps
from printkit import OUT,ROOT,cards,MOBS,BOSSES,heroes,items,schools,QUESTS
from world import realms,edges,acts,endings
from field_guide import GUIDES
from chronicle_cards import validate_chronicles
from foes import families
from roadside import MEETINGS
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
    die = trimesh.load_mesh(ROOT/'Кубики'/'Береговой d6 — 16 мм.stl')
    solid = manifold3d.Manifold(manifold3d.Mesh(die.vertices.astype('float32'), die.faces.astype('uint32')))
    assert die.is_volume and len(solid.decompose())==1 and np.allclose(die.extents,[16,16,16])
    assert np.linalg.norm(die.center_mass-[0,0,8]) < 0.01
    expected=[7,36,55,15,2,34,12,5,8];pdfs=sorted(OUT.glob('*.pdf'));assert len(pdfs)==9;pagecounts={};tmp=ROOT/'qa-temp';tmp.mkdir(exist_ok=True);allthumb=[]
    for ix,p in enumerate(pdfs):
        d=pymupdf.open(p);assert len(d)==expected[ix],(p,len(d));pagecounts[p.name]=len(d);alltext=''
        for pi,pg in enumerate(d):
            alltext+=pg.get_text();pix=pg.get_pixmap(matrix=pymupdf.Matrix(.33,.33),alpha=False);ar=np.frombuffer(pix.samples,'uint8').reshape(pix.height,pix.width,3);assert ar.std()>9,(p,pi);allthumb.append((p.stem[:2]+'.'+str(pi+1),Image.fromarray(ar)))
        if ix in [4,5,6,7]:
            pref=['H','M','B','I'][ix-4];assert all(k in alltext for k in cards if k[0]==pref),(p,'missing card')
        if ix == 3:
            travel_pages = ' '.join(d[i].get_text().casefold() for i in range(8,13))
            for region in realms:
                assert region[3].casefold() in travel_pages, region[3]
                assert all(hidden.casefold() not in travel_pages for hidden in (region[8],region[11])), region[0]
            for i, labels in [(13, ('Сохранение встречи', 'СОХРАНИЛ(А)', 'Зона', 'Действие', 'сигнал', 'ворот')),
                              (14, ('Журнал решений и обещаний', 'Герой / игрок', 'место', 'отклика'))]:
                sheet = d[i].get_text()
                assert '\x00' not in sheet and all(label in sheet for label in labels), (p, i+1)
        if ix in [0,1,2]:assert 'море' in alltext.casefold() and '□' not in alltext
        if ix == 1:
            from printkit import parse_book, RULE_BOOK
            from maps import fields
            chapters = [page for filename in RULE_BOOK for page in parse_book(filename)]
            assert '\x00' not in alltext
            assert [title for _,title,_ in d.get_toc()] == [title for title,_ in chapters]
            for pg,(title,blocks) in zip(d,chapters):
                text = ' '.join(pg.get_text().split())
                assert all(' '.join(body.split()) in text for _,body in blocks), title
                assert len(pg.get_images()) >= sum(kind.startswith('art-') for kind,_ in blocks), title
            assert "Слово своего героя" in d[18].get_text()
            assert "Как оставить стол до следующей встречи" in d[19].get_text()
            free_table = ' '.join(d[20].get_text().split())
            assert 'Свободный стол для другой игры' in free_table and 'Меню хода' in free_table
            for threshold in (8, 9):
                count = sum(a + b + 1 >= threshold for a in range(1, 7) for b in range(1, 7))
                assert f'{count} из 36' in free_table
            # The first shot and the practice fight must remain playable with the printed pieces.
            bridge = fields[0][2]
            assert (1,2) in bridge and (2,4) in bridge
            assert min(b if a==4 else a for a,b in bridge if 4 in (a,b))==2
            assert heroes[0][0]=='Сойка' and heroes[15][0]=='Гран' and int(heroes[15][2][0])==2
            assert 'дальность 0, база 2' in items[int(heroes[15][3])-1][3]
            first, practice = MOBS[:2]
            assert first['id']=='M001' and 'первую атаку по этой фигуре герои делают с преимуществом' in first['trait']
            assert (practice['id'],practice['hp'],practice['defense'],practice['t'])==('M002',3,8,1)
            assert practice['trait'].startswith('Боковой ход') and 5 < practice['defense'] <= 10
        if ix == 2:
            register = (ROOT/'design'/'campaign-register.md').read_text(encoding='utf8')
            assert set(QUESTS) == {f'H{i:02}' for i in range(1, 19)}
            for i, (hero_id, quest) in enumerate(sorted(QUESTS.items())):
                page = ' '.join(d[27+i].get_text().split()).casefold()
                assert set(quest.paths) == {'a', 'b'} and quest.realm != quest.reply_realm
                passages = [hero_id, heroes[i][0], quest.title, quest.offer, quest.meeting, quest.unfinished,
                            realms[quest.realm-1][0], realms[quest.reply_realm-1][0]]
                for branch in quest.paths.values():
                    passages.extend([branch.label, branch.scene, branch.reply, branch.epilogue])
                for passage in passages:
                    assert passage.casefold() in page and passage in register, (hero_id, passage)
            assert set(GUIDES) == set(range(1,11))
            heads, names = set(), set()
            for area, entry in GUIDES.items():
                row = realms[area-1]
                public_text = ' '.join(d[44+area].get_text().split())
                title = row[5][0].upper() + row[5][1:]
                assert title in public_text, area
                master_text = ' '.join(d[6+area].get_text().split())
                assert title in master_text and f'фиксированная T {levels[area-1]}' in master_text, area
                page = public_text.casefold()
                residents = entry['residents']
                heads.add(entry['head'].split(',')[0])
                assert len(residents) == 3 and all(set(p) == {'name','role','hook'} for p in residents)
                assert [p['name']+', '+p['role'] for p in residents[:2]] == [row[6], MEETINGS[area].npc]
                names.update(p['name'] for p in residents)
                fields = [row[0],row[2],row[3],row[5],*(v for k,v in entry.items() if k != 'residents')]
                fields.extend(value for person in residents for value in person.values())
                fields.extend(family[0] for family in families[3*area-3:3*area])
                assert all(v.casefold() in page for v in fields), area
                assert all(value.casefold() not in page for value in row[8:12]+row[14:15]), area
            assert len(heads)==10 and len(names)==30 and not heads & names
        d.close()
    guide = (OUT/'Начать здесь.txt').read_text(encoding='utf8')
    for label in ('01 Правила', '02 Кампания и атлас'):
        assert f"{label} — {pagecounts[label + '.pdf']} страниц" in guide
    for k in range(0,len(allthumb),40):
        sel=allthumb[k:k+40];sheet=Image.new('RGB',(1000,math.ceil(len(sel)/8)*163),'#c9c4b4');dr=ImageDraw.Draw(sheet)
        for j,(tag,im) in enumerate(sel):
            pic=ImageOps.contain(im,(118,143));x=(j%8)*125;y=(j//8)*163;sheet.paste(pic,(x,y));dr.text((x,y+143),tag,fill='black')
        sheet.save(tmp/f'all-{k}.jpg')
    simulations=[sim(n,t,n*971+t) for n in range(2,7) for t in [1,3,5]]
    res={'контент':{'герои':18,'обычные':300,'боссы':100,'вещи':40,'королевства':10,'народы':10,'полевые_листы':len(GUIDES),'старосты':len(heads),'жители_на_полевых_листах':len(names),'регионы_связны':True,'финалы':8,'местные_контракты':30,'главы':5,'общие_поручения_Неры':2,'личные_поручения':len(QUESTS),'личные_решения':sum(len(q.paths) for q in QUESTS.values())},'проверка':{'файлы_STL':len(geom),'отдельный_кубик_d6_STL':1,'открытые_рёбра_или_плохой_обход':len(faults),'карточки_PNG':len(images),'страницы_PDF':pagecounts,'все_страницы_отрисованы':True},'модель':'Условный неподвижный босс; все бьют штатным оружием по сильной характеристике, фокус врага по раненому. Без рун, лечения, брони, критической искры, особенностей, сигналов, движения и переговоров. Проверяет только базовую арифметику боя. Это не плейтест.','моделирование':simulations}
    res['проверка']['карточки_с_историей'] = validate_chronicles()
    (OUT/'Проверка.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(res,ensure_ascii=False,indent=1))
if __name__=='__main__':main()
