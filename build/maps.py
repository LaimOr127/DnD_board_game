from PIL import Image,ImageDraw,ImageFont,ImageFilter
from world import coords,realms,edges,sea,pal
from art import mix
from pathlib import Path
import random, math
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Море имён';OUT.mkdir(exist_ok=True)
def font(size,bold=False,serif=False):return ImageFont.truetype('C:/Windows/Fonts/'+(('georgiab' if bold else 'georgia') if serif else ('arialbd' if bold else 'arial'))+'.ttf',size)

def worldmap():
    rng=random.Random(728);w,h=2010,1350;im=Image.new('RGB',(w,h),'#f2e8ce');d=ImageDraw.Draw(im); d.rounded_rectangle((26,26,w-26,h-26),radius=5,outline='#6d7055',width=2)
    d.text((68,47),'АТЛАС  /  ЛИСТ 01',font=font(19,True),fill='#806e49');d.text((65,70),'Море имён',font=font(76,True,True),fill='#203d3b');d.text((w-69,89),'ДЕСЯТЬ КОРОН',font=font(28,True,True),fill='#254e4e',anchor='ra');d.text((w-69,132),'Общая карта странствий  •  порталы скрыты',font=font(22),fill='#516a65',anchor='ra')
    x0,y0,x1,y1=54,184,w-54,h-125;mw,mh=x1-x0,y1-y0; m=Image.new('RGB',(mw,mh),'#8cb6b2');md=ImageDraw.Draw(m);xy=lambda q:(int(q[0]/100*mw),int(q[1]/100*mh));
    mainland=[(9,-2),(29,-2),(35,4),(41,1),(48,3),(52,-4),(78,-3),(94,0),(100,7),(104,27),(100,54),(104,83),(95,86),(88,83),(84,94),(77,89),(71,99),(64,98),(61,84),(56,90),(48,87),(46,92),(39,83),(34,83),(33,73),(28,77),(23,73),(19,76),(18,68),(14,67),(13,56),(17,51),(15,45),(18,40),(12,36),(13,30),(8,25),(10,19),(5,12),(11,9)];island=[(7,82),(10,78),(18,79),(22,84),(21,89),(17,94),(12,92),(10,87),(6,88)]; lake=[(54,54),(59,51),(65,53),(69,49),(71,54),(67,60),(62,62),(60,68),(56,65),(56,61),(52,59)]
    def jagged(poly):
        pts=[]
        for (ax,ay),(bx,by) in zip(poly,poly[1:]+poly[:1]):
            n=max(1,int(math.hypot(bx-ax,by-ay)*1.6));
            for j in range(n):
                t=j/n;pts.append(xy((ax+(bx-ax)*t+rng.uniform(-.33,.33),ay+(by-ay)*t+rng.uniform(-.38,.38))))
        return pts
    mask=Image.new('L',(mw,mh));sd=ImageDraw.Draw(mask);polys=[jagged(mainland),jagged(island)];lk=jagged(lake)
    for pl in polys:sd.polygon(pl,fill=255)
    sd.polygon(lk,fill=0)
    for n in range(1000):
        x,y=rng.randrange(mw),rng.randrange(mh);md.arc((x-12,y-3,x+12,y+3),5,163,'#76a5a4',1)
    for pl in polys+[lk]:
        for off,color in [(15,'#a3c5be'),(8,'#c7d5ba')]:md.line(pl+pl[:1],fill=color,width=off*2)
    for pl in polys:md.polygon(pl,fill='#dfd8af',outline='#60776a',width=3)
    md.polygon(lk,fill='#7faaa6',outline='#577b75',width=3)
    for n in range(13500):
        x,y=rng.randrange(mw),rng.randrange(mh)
        if mask.getpixel((x,y)):md.line((x,y,x+rng.choice([1,2,4]),y),fill=rng.choice(['#d5d0a9','#d5cca2','#eae1bb']),width=1)
    def hill(x,y,size):
        a=size;l=int(a*.85);md.polygon([(x-l,y),(x,y-int(a*1.3)),(x+l,y)],fill='#b0b497',outline='#657969',width=2);md.polygon([(x,y-int(a*1.3)),(x+l,y),(x+2,y-4),(x-1,y-a//2)],fill='#7c9180');md.polygon([(x,y-int(a*1.3)),(x-int(a*.42),y-int(a*.66)),(x-1,y-int(a*.76)),(x+int(a*.25),y-int(a*.55))],fill='#f5e9c9')
    def tree(x,y,s):
        md.line((x,y-s//2,x,y+3),fill='#526e58',width=2);md.polygon([(x-s//2,y-2),(x-s//4,y-s//2),(x-s//3,y-s//2),(x,y-s),(x+s//2,y-2)],fill=rng.choice(['#789376','#90a383','#657f68']),outline='#5d7862')
    for cx,cy,rx,ry,num,tp in [(30,17,17,11,72,'m'),(53,12,10,8,34,'m'),(79,14,17,14,80,'m'),(44,42,14,14,360,'t'),(25,55,7,9,100,'t'),(70,27,7,9,32,'m'),(68,74,10,10,100,'t'),(83,55,9,11,33,'m')]:
        loc=sorted([(rng.gauss(cx,rx/2.4),rng.gauss(cy,ry/2.4)) for k in range(num)],key=lambda q:q[1]);
        for q in loc:
            x,y=xy(q)
            if 35<x<mw-35 and 35<y<mh-30 and mask.getpixel((x,y)):(hill if tp=='m' else tree)(x,y,rng.randint(14,31) if tp=='m' else rng.randint(10,22))
    for cx,cy in [(26,65),(45,75),(49,70),(75,46)]:
        for k in range(15):
            x,y=xy((cx+rng.uniform(-5,5),cy+rng.uniform(-5,5)));md.line([(x-10,y+5),(x+9,y-5)],'#b5a26c',2)
    for points in [[(31,22),(32,36),(29,43),(32,48),(26,54),(25,62),(20,67),(14,67)],[(74,19),(71,31),(66,38),(67,45),(63,54)],[(57,65),(56,71),(60,78),(60,87)]]:md.line([xy(q) for q in points],fill='#7faaa2',width=5)
    def road(a,b,water):
        x,y=xy(coords[a-1]);xx,yy=xy(coords[b-1]);dx,dy=xx-x,yy-y;n=max(1,int(math.hypot(dx,dy)/14));
        for j in range(n):
            t=j/n;u=(j+.55)/n;md.line((x+dx*t,y+dy*t,x+dx*u,y+dy*u),fill='#295865' if water else '#805f3c',width=3)
    for a,b in edges:road(a,b,(a,b) in sea)
    for i,(cx,cy) in enumerate(coords):
        x,y=xy((cx,cy));vx,vy=x+65,y-13
        for xx,yy in [(vx,vy),(vx+12,vy+4)]:md.rectangle((xx-6,yy-5,xx+6,yy+5),fill='#e5c690',outline='#5c503c');md.polygon([(xx-8,yy-5),(xx,yy-12),(xx+8,yy-5)],fill='#a56c49')
        md.ellipse((x-19,y-19,x+19,y+19),fill='#203e40',outline='#f4db9c',width=3);md.text((x,y),f'{i+1:02}',font=font(16,True),fill='#fff3ce',anchor='mm');title=realms[i][0];ww=md.textlength(title,font=font(23,True,True))/2+11;md.rounded_rectangle((x-ww,y+21,x+ww,y+52),radius=5,fill='#f5e9c9',outline='#aa9c77');md.text((x,y+35),title,font=font(23,True,True),anchor='mm',fill='#283f3b')
    for q,name in [((7,61),'МОРЕ'),((7,65),'ЧЕРНИЛ'),((84,73),'Соляные'),((84,76),'пустоши')]:md.text(xy(q),name,font=font(17,False,True),fill='#41686b',anchor='mm')
    x,y=xy((91,43));md.polygon([(x,y-34),(x+8,y),(x,y+24),(x-8,y)],fill='#f6e8bf',outline='#395759',width=2);md.polygon([(x,y-34),(x,y),(x-8,y)],fill='#395759');md.text((x,y-46),'С',font=font(16,True),anchor='mm',fill='#395759');im.paste(m,(x0,y0));d.rectangle((x0,y0,x1,y1),outline='#566e61',width=3)
    d.text((69,h-85),'●  область и столица      ⌂  деревня      – –  дорога      · ·  морской переход',font=font(24),fill='#355553');d.text((w-67,h-83),'Путь между двумя номерами = один день',font=font(22,False,True),fill='#625c44',anchor='ra');im.save(OUT/'Карта мира.png',dpi=(200,200));return im

fields=[('Колокол у брода',['Площадь','Мостки','Звонница','Отмель','Амбар','Лодка'],[(1,2),(2,3),(2,4),(1,5),(5,3),(4,6),(6,3)]),('Подземелье',['Вход','Развилка','Архив','Обвал','Цистерна','Затвор'],[(1,2),(2,3),(2,4),(3,5),(4,5),(5,6)]),('Застава',['Двор','Ворота','Бомбарда','Катапульта','Дорога','Склон'],[(1,2),(1,3),(1,4),(2,3),(2,4),(2,5),(2,6),(5,6)])]
