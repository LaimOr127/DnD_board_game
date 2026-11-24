import math, json, re, random, sys
from pathlib import Path
from PIL import Image,ImageDraw
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from world import realms,coords,edges,pal,acts,endings
from party import heroes,schools,items
from foes import foes,families
from extras import local,weather
from edicts import peoples
from appendix import perks,levels,landmarks,extra_rules
from art import sprite,icon,mix
from maps import OUT,ROOT,worldmap,fields
sys.path.append(str(ROOT/'site'))
from personal_quests import QUESTS
for nick,fn in [('S','arial'),('SB','arialbd'),('G','georgia'),('GB','georgiab')]:pdfmetrics.registerFont(TTFont(nick,'C:/Windows/Fonts/'+fn+'.ttf'))
PAPER='#fbf7e9';INK='#223a3a';MUTED='#4b605c';GOLD='#ab7943';LINE='#c6b894';MOBS,BOSSES=foes();cards={};measure=[]
def clr(c,s):c.setFillColor(HexColor(s))
def stroke(c,s):c.setStrokeColor(HexColor(s))
def rect(c,x,y,w,h,color):clr(c,color);c.rect(x,y,w,h,fill=1,stroke=0)
def txt(c,x,y,text,size=10,face='S',color=INK,al='left'):
    clr(c,color);c.setFont(face,size);getattr(c,{'left':'drawString','center':'drawCentredString','right':'drawRightString'}[al])(x,y,str(text))
def wrap(t,w,font,size):
    words=t.split();lines=[];line=''
    for word in words:
        new=(line+' '+word).strip()
        if line and pdfmetrics.stringWidth(new,font,size)>w:lines.append(line);line=word
        else:line=new
    if line:lines.append(line)
    assert all(pdfmetrics.stringWidth(l,font,size)<=w+.2 for l in lines),(t,w,size)
    return lines
def fitted(c,x,y,t,w,size,face='GB',color=INK):
    s=min(size,w/max(1,pdfmetrics.stringWidth(t,face,1)));txt(c,x,y,t,s,face,color);return s
def img(c,im,x,y,w,h):c.drawImage(ImageReader(im),x,y,w,h,mask='auto')
def art_for(key):
    v=int(key[1:])-1
    if key[0]=='H':return sprite('hero'+str(v//3),v,v//3)
    if key[0]=='I':return icon(items[v][4],v)
    z=(MOBS if key[0]=='M' else BOSSES)[v];return sprite(z['body'],z['seed'],z['area'],key[0]=='B')

def deckdata():
    for i,h in enumerate(heroes):
        k=f'H{i+1:02}';sch=schools[i//3];cards[k]=(h[0],sch+'  /  '+h[1],i//3,'М '+h[2][0]+'    Л '+h[2][1]+'    В '+h[2][2]+'     ЗАЩ 9   ОЗ 8',[('ПРИЁМ  /  1 ИСКРА',h[4]),('ТАЛАНТ  /  УР. 2 ИЛИ 6',h[5]),('СВЯЗКА И ЦЕНА',h[7])],f'Старт: I{int(h[3]):02} + I19  •  3 искры')
    for b in MOBS+BOSSES:
        k=b['id'];big=k[0]=='B';hp=str(b['hp'])+('×N' if big else '');stats=f'ОЗ {hp}    ЗАЩ {b["defense"]}   АТК +{b["t"]+int(big)}   УР {b["dmg"]}   ДАЛЬ {b["reach"]}'
        sections=([('ЗАКОН АРЕНЫ',b['decree']),('ПЕРЕЛОМ  /  ½ ОЗ',b['ability']),('СИГНАЛ',b['omen']+' '+b['signal']+' '+b['counter']),('ПОРАЖЕНИЕ',b['loss'])] if big else [('ИНСТИНКТ',b['ability']),('ОСОБЕННОСТЬ',b['trait']),('ПОРАЖЕНИЕ',b['loss'])]);cards[k]=(b['name'],('Босс' if big else 'Существо')+'  /  ступень '+str(b['t']),b['area'],stats,sections,f'{b["area"]+1:02}  •  '+realms[b['area']][0]);
    for i,it in enumerate(items):cards[f'I{i+1:02}']=(it[0],it[1]+'  /  каталог',i%10,f'ЦЕНА {it[2]} СЕРЕБРА',[('ПРИМЕНЕНИЕ',it[3]),('ЯЧЕЙКА',('Флакон на поясе. После применения сбросьте.' if it[1]=='Зелье' else 'Наденьте в слот «'+it[1].lower()+'».'))],('Реликвия области '+f'{i-29:02}' if i>=30 else 'Снаряжение отряда'))
deckdata()

def card(c,key,x,y):
    name,kind,area,stats,blocks,foot=cards[key];w=63*mm;h=88*mm;cp=pal[area];c.saveState();c.translate(x,y);rect(c,0,0,w,h,'#f8f2df');stroke(c,'#53655a');c.setLineWidth(.5);c.rect(.8,.8,w-1.6,h-1.6);rect(c,1,h-17,w-2,16,INK);txt(c,7,h-11,key,8.4,'SB','#ffe2a2');txt(c,w-7,h-11,kind,7,'SB','#f1e8cd','right');fitted(c,7,h-34,name,w-14,14.3)
    top=h-38;ah=46 if key[0]=='B' else 58;rect(c,5,top-ah,w-10,ah,mix(cp,'#eaead2',.70));rng=random.Random(key);stroke(c,mix(cp,'#e1e2c8',.45));c.setLineWidth(.45)
    for step in range(3):
        line=c.beginPath();line.moveTo(5,top-ah+7+step*4)
        for xx in range(5,174,7):line.lineTo(xx,top-ah+5+step*4+rng.random()*9)
        c.drawPath(line)
    for ind in range(3):c.circle(w/2,top-ah*.52,15+ind*5,stroke=1)
    spriteim=art_for(key)
    factor=4;big=spriteim.resize((spriteim.width*factor,spriteim.height*factor),Image.Resampling.NEAREST);sw=ah*spriteim.width/spriteim.height;img(c,big,(w-sw)/2,top-ah,sw,ah)
    for side in (12,w-14):txt(c,side,top-ah/2-1,'✦' if False else '•',8,'SB',cp)
    ypos=top-ah-13;rect(c,5,ypos-2,w-10,14,INK);txt(c,w/2,ypos+2,stats,7.35,'SB','#f4e8ca','center');start=ypos-12;bottom=16;avail=start-bottom
    def layout(size):return [(label,wrap(body,w-16,'S',size)) for label,body in blocks]
    for z in range(85,56,-1):
        size=z/10;data=layout(size);needed=sum(size+3+len(lines)*(size+1.45) for label,lines in data)
        if needed<=avail:break
    assert needed<=avail,(key,needed,avail);measure.append((key,size));yy=start
    for label,lines in data:
        txt(c,8,yy,label,6.1,'SB',mix(cp,INK,.35));yy-=size+1
        for l in lines:txt(c,8,yy,l,size,'S');yy-=size+1.45
        yy-=2
    assert yy+10>=bottom-3,(key,yy)
    stroke(c,LINE);c.line(7,14,w-7,14);txt(c,8,5.5,foot,6.45,'SB',MUTED);c.restoreState()

def sheet(c,keys,label):
    w,h=A4;cw,ch=63*mm,88*mm;sx=(w-3*cw)/2;sy=(h-3*ch)/2
    for j,key in enumerate(keys):card(c,key,sx+(j%3)*cw,sy+(2-j//3)*ch)
    stroke(c,'#656859');c.setLineWidth(.35)
    for i in range(4):
        x=sx+i*cw;y=sy+i*ch;c.line(x,sy-6,x,sy-1);c.line(x,sy+3*ch+1,x,sy+3*ch+6);c.line(sx-6,y,sx-1,y);c.line(sx+3*cw+1,y,sx+3*cw+6,y)
    txt(c,sx,15,'МОРЕ ИМЁН   /   '+label,7,'SB',MUTED);txt(c,w-sx,15,'63 × 88 мм   •   A4   •   печать 100%',7,'S',MUTED,'right');c.showPage()
def decks():
    for fn,prefix in [('04 Герои','H'),('05 Существа','M'),('06 Боссы','B'),('07 Вещи','I')]:
        c=Canvas(str(OUT/(fn+'.pdf')),pagesize=A4);c.setTitle(fn+' · Море имён');keys=[k for k in cards if k.startswith(prefix)]
        for i in range(0,len(keys),9):sheet(c,keys[i:i+9],keys[i]+' — '+keys[min(i+8,len(keys)-1)])
        c.save()

def parse_book(filename='rules.md'):
    pages=[]
    for line in (ROOT/'design'/filename).read_text(encoding='utf8').splitlines():
        if line.startswith('# '):pages.append([line[2:],[]]);continue
        if line:pages[-1][1].append(('h' if line.startswith('## ') else 'p',line.removeprefix('## ')))
    return pages

def bookpage(c,title,blocks,num,series,over='',art=None):
    c.setPageSize(A4);w,h=A4;rect(c,0,0,w,h,PAPER);rect(c,0,h-8,w,8,INK);txt(c,43,h-42,'М О Р Е   И М Ё Н     /     '+series.upper(),8,'SB',MUTED);txt(c,w-43,h-42,f'{num:02}',12,'GB',GOLD,'right');stroke(c,LINE);c.line(43,h-53,w-43,h-53);fitted(c,42,h-97,title,w-84,28,'GB');top=h-128
    if over:txt(c,43,top+5,over,9,'SB',GOLD);top-=17
    for p in range(125,84,-1):
        size=p/10;lay=[];total=0
        for typ,body in blocks:
            if not body:continue
            ll=wrap(body,w-90,'SB' if typ=='h' else 'G',size+1 if typ=='h' else size);step=(size+4) if typ=='h' else (size*1.45);before=7 if typ=='h' else 0;after=4 if typ=='h' else 8;total+=before+len(ll)*step+after;lay.append((typ,ll,step,before,after))
        if total<=top-48:break
    assert total<=top-48,(title,total,top); yy=top
    for typ,ll,step,before,after in lay:
        yy-=before
        for l in ll:txt(c,44,yy,l,size+1 if typ=='h' else size,'SB' if typ=='h' else 'G',mix(GOLD,INK,.37) if typ=='h' else INK);yy-=step
        yy-=after
    if art and yy>139:
        aa=art.resize((art.width*4,art.height*4),Image.Resampling.NEAREST);ww=min(100,(yy-47)*aa.width/aa.height);img(c,aa,(w-ww)/2,50,ww,ww*aa.height/aa.width)
    stroke(c,LINE);c.line(43,34,w-43,34);txt(c,43,20,'ДЕСЯТЬ КОРОН   /   ИГРОВОЕ ИЗДАНИЕ   •   16+',6.8,'SB',MUTED);txt(c,w-42,20,'Море имён     /     '+str(num),8,'G',MUTED,'right');bid=str(num);c.bookmarkPage(bid);c.addOutlineEntry(title,bid);c.showPage()

def rules():
    c=Canvas(str(OUT/'01 Правила.pdf'),pagesize=A4);c.setTitle('Море имён · Правила');
    for i,(title,blocks) in enumerate(parse_book()):bookpage(c,title,blocks,i+1,'Правила стола',art=icon(['bell','rune','sword','heart','coin','helm','portal','eye','lantern','horn','crown','book'][i],i))
    for j,(title,blocks) in enumerate(extra_rules):bookpage(c,title,blocks,13+j,'Справочник')
    for j,(title,blocks) in enumerate(parse_book('promises.md')):
        section = 'Игровой стол' if title in ('Как оставить стол до следующей встречи','Свободный стол для другой игры') else 'Книга обещаний'
        bookpage(c,title,blocks,13+len(extra_rules)+j,section)
    c.save()
def campaign():
    pages=[]
    def page(title,blocks,over='',art=None):pages.append((title,blocks,over,art))
    page('Хартия последнего берега',[('p','Кампания для 2–6 героев. Ведущему можно читать всё; кооперативному столу — сначала пролог и только открытые записи. Пять глав составляют основную историю, каждый регион можно исследовать отдельно.'),('h','Три времени моря'),('p','87 лет назад море ворвалось в долину. Десять корон подняли Затвор и отдали ему имена умерших — память стала платой за сушу. 19 лет назад последние списки закончились. Казначеи начали подмешивать имена живых. Девять дней назад колокол у Трёх Ив позвонил сам: механизм получил одинаковое имя дважды и стал проверять весь реестр.'),('h','Три стороны, у каждой есть резон'),('p','Эйра, королева Вельна, хочет удержать берега до эвакуации; знает, что чиновники вписывают живых. Братство Пустых Ложек хочет обнародовать список, но в нём есть имена детей. Соляная Лига умеет связать новые острова арками и рассчитывает владеть переправами. Ни одна сторона не считает себя служанкой моря.'),('h','Что знают герои'),('p','Каждый способен помнить одну вымаранную вещь. До старта назовите её соседу справа. В финале сосед решает, как память о ней изменит выбранное послесловие. Сюжетные следы всегда доступны; кости определяют цену, темп и друзей.'),('h','Навигация'),('p','Главы: 2–6. Финалы: 7. Атлас и 30 местных дел: 8–17. Закрытый ключ порталов: 18. Дорожные встречи: 19. Личные истории героев: 20–25. Народы и обычаи: 26–27. Поручения H01–H18: 28–45, по порядку номеров. Отдельно: правила, тактические поля, колоды M/B/H/I и лист первого вечера.')],art=icon('portal'))
    for i,a in enumerate(acts):page(a[0],[('h','Прочитать вслух'),('p',a[1]),('h','Раскладка'),('p',a[2]),('h','Выбор'),('p',a[3]),('h','Что меняется'),('p',a[4]),('h','Последняя строка'),('p',a[5])],f'ОСНОВНАЯ ИСТОРИЯ  /  ГЛАВА {i+1} ИЗ 5',art=art_for(['M001','H04','H16','I11','B009'][i]))
    eb=[]
    for name,cond,end in endings:eb.extend([('h',name+'  /  '+cond),('p',end)])
    eb.append(('p','Послесловие: при трёх и более шрамах назовите потерянную деревню. При непогашенном долге армия требует ваш знак. При раскрытом заговоре бывший противник станет первым летописцем. Сочетайте подходящие последствия.'));page('Восемь судеб побережья',eb)
    for i,(rr,ex) in enumerate(zip(realms,local)):
        n,folk,cap,vill,biome,roy,npc,want,entr,rel,pact,port,quest,choice,gain=rr; aa,bb,cc,dd,ee,ff,levels=ex; page(n,[('h','Двор и деревня'),('p',f'{roy.capitalize()} принимает в столице {cap}; деревня — {vill}. Здесь живут {folk}. {npc.capitalize()} {want}. Один и тот же народ может жить по обе стороны границы; происхождение не задаёт характер героя.'),('h','01  /  '+quest),('p',choice+' '+gain+' За основное местное дело +1 слава здесь; первое выполнение даёт опыт по общим правилам.'),('h','02  /  '+aa),('p',bb+' Награда: '+cc),('h','03  /  '+dd),('p',ee+' Награда: '+ff),('h','Вход: '+entr),('p','Этажи I → V: '+levels+'. На каждом примените соответствующую опасность глубины с листа тактики. В архиве хранится '+rel+'. На V вместо боя допустима сделка: '+pact+'. Получите награду за достижение, даже если договорились.'),('h','Местные колоды и выходы'),('p',f'Особая вылазка «{landmarks[i]}»: фиксированная T {levels[i]}; её обычная встреча даёт 1 осколок дополнительно за первую победу. Общая колода: M{i*30+1:03}–M{(i+1)*30:03}; B{i*10+1:03}–B{(i+1)*10:03}. Дороги: '+', '.join(f'{(b if a==i+1 else a):02}' for a,b in edges if i+1 in (a,b))+'. Реликвия: '+items[30+i][0]+f' (I{31+i:02}).')],f'ОБЛАСТЬ {i+1:02}   /   '+biome.upper(),art=art_for(f'B{i*10+1:03}'))
    keys=[]
    for i,rr in enumerate(realms):keys +=[('h',f'{i+1:02}   /   '+rr[0]),('p',rr[11])]
    keys += [('p','Открывайте запись только после первого следа. Указан бросок открытия; при неудаче всё равно можно найти арку за день и припас. Не показывайте эту страницу на общей карте.')];page('Под сургучом: ключ переправ',keys)
    ws=[('p','Вместо обычного путевого NPC можно кинуть d6 и разыграть одну из сцен. Выбор всегда доброволен; выданную разовую награду отметьте. Если исход не описан, применяется цена импровизации из правил.')];
    for i,(t,a,b) in enumerate(weather):ws.extend([('h',f'{i+1}   /   '+t),('p',a+' '+b)])
    page('Люди у дороги',ws)
    for sc in range(6):
        hs=[]
        for i in range(sc*3,sc*3+3):
            h=heroes[i];hs += [('h',f'H{i+1:02}  /  '+h[0]+', '+h[1].lower()),('p',h[6]+' '+h[7]),('p','Личный приём (1 действие, 1 искра): '+h[4]+' Талант: '+h[5])]
        hs.extend([('h','Школьный навык вне боя'),('p',perks[sc])])
        hs.append(('p','Это три самостоятельных стартовых героя школы, а не последовательные повышения уровня. Выбирайте свободно; все начинают с одинакового запаса сердец и искр. Любого можно переименовать. Народ — история, школа — правила.'))
        page(schools[sc]+': три пути',hs,art=art_for(f'H{sc*3+1:02}'))
    for group in range(2):
        bio=[('p','Ведьма, воин и маг могут происходить из любого народа. Эльф, дварф и орк — названия трёх традиционных школ: их ученика тоже может усыновить иной народ. Биография даёт связи, не прибавку к характеристикам.')]
        for folk,custom,question in peoples[group*5:group*5+5]:bio += [('h',folk),('p',custom+' '+question)]
        page('Народы и обычаи · '+str(group+1),bio)
    for hero_id, quest in sorted(QUESTS.items()):
        hero_name = heroes[int(hero_id[1:]) - 1][0]
        home, reply = realms[quest.realm - 1][0], realms[quest.reply_realm - 1][0]
        blocks = [('h','Обещание'), ('p',quest.offer),
                  ('h','Встреча · ' + home), ('p',quest.meeting)]
        for path in quest.paths.values():
            blocks.extend([('h',path.label), ('p',path.scene),
                           ('p','Ответ · ' + path.reply), ('p','Последний звон · ' + path.epilogue)])
        blocks.extend([('h','Если герой оставил выбор открытым'), ('p',quest.unfinished)])
        page(quest.title, blocks, f'{hero_id}  /  {hero_name.upper()}     •     МЕСТО ОТВЕТА  /  {reply.upper()}')
    c=Canvas(str(OUT/'02 Кампания и атлас.pdf'),pagesize=A4);c.setTitle('Море имён · Книга берегов');
    for i,(t,b,over,art) in enumerate(pages):bookpage(c,t,b,i+1,'Книга берегов',over,art)
    c.save()
