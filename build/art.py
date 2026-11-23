from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageColor
import random, math, colorsys
from world import pal
INK='#192c31'; LIGHT='#fff0c6'; GOLD='#edb560'; STEEL='#a1cfce'
def mix(a,b,t):
    aa=ImageColor.getrgb(a);bb=ImageColor.getrgb(b);return '#%02x%02x%02x'%tuple(round(x+(y-x)*t) for x,y in zip(aa,bb))

def sprite(kind,seed=0,area=0,boss=False):
    im=Image.new('RGBA',(68,58));d=ImageDraw.Draw(im);p=d.polygon; e=d.ellipse; r=d.rectangle
    def line(pts,c,w=2):d.line(pts,fill=c,width=w)
    base=pal[area%10]; main=mix(base,('#d4ab65','#9bd6bc','#d2866b','#bda7d7','#96bada')[seed%5],.42); dark=mix(main,INK,.62); hi=mix(main,LIGHT,.58); skin=['#d89d75','#ab7356','#e4b48e','#bd8065'][seed%4]; edge='#3d3930';cloth=main
    def shape(points,c=main):p(points,c);line(list(points)+[points[0]],dark,1)
    def leg(x,y,dx=1):shape([(x,y),(x+5,y),(x+dx+4,48),(x+dx+7,50),(x+dx,50)],dark)
    def eye(x,y):r((x,y,x+3,y+2),INK);r((x+2,y,x+3,y+1),'#ffcf6b')
    original=kind
    outfits={'crone':2,'mariner':3,'judge':4,'priest':4,'queen':2,'scribe':4,'ghost':6,'titan':9,'kiln':9,'tower':9,'foxsage':0}
    extra=kind in outfits
    if extra:kind='hero'+str(outfits[kind]) if outfits[kind]<6 else ['ghoul','knight','skeleton','golem'][outfits[kind]-6]
    if kind.startswith('hero') or kind in ['ghoul','knight','skeleton','golem']:
        role=int(kind[-1]) if kind.startswith('hero') else {'ghoul':6,'knight':7,'skeleton':8,'golem':9}[kind];v=seed%3; bulky=role in (1,3,5,7,9);left=19 if bulky else 23
        if role in (5,6):skin='#84ad85' if role==5 else '#a8b3a1'
        if role==8:skin='#e4d2a4'
        if role==9:skin=hi
        leg(26,38,-2);leg(36,38,2);shape([(left+3,25),(38,21),(47,29),(50,46),(38,43),(22,45),(17,48)],dark);shape([(left,26),(29,23),(39,23),(48,29),(43,34),(40,42),(26,41),(23,33),(left-4,35)],cloth)
        shape([(27,25),(33,24),(37,28),(35,37),(28,36)],hi);r((25,37,41,39),edge);r((32,37,35,39),GOLD);shape([(25,13),(31,9),(40,12),(42,18),(38,25),(34,28),(28,24)],skin);eye(36,17);line([(37,23),(40,21)],edge,1)
        if role==0:
            shape([(26,20),(16,14),(28,16)],skin);shape([(24,18),(24,12),(32,7),(41,11),(44,15),(34,13)],dark);line([(44,10),(51,13),(56,21),(57,32),(51,40)],GOLD,2);line([(44,10),(51,40)],LIGHT,1);line([(32,33),(49,25)],skin,3)
        elif role==1:
            shape([(24,20),(31,23),(40,21),(40,28),(35,36),(29,31)],'#935b3e');line([(30,25),(33,31)],GOLD,2);shape([(22,17),(23,11),(29,8),(37,9),(43,14),(43,17)],hi);line([(46,37),(52,17)],edge,3);shape([(45,13),(56,12),(59,17),(48,20)],STEEL)
        elif role==2:
            shape([(17,16),(27,10),(33,2),(34,7),(40,13),(48,18),(38,17),(28,16)],dark);line([(26,13),(37,13)],GOLD,2);line([(47,40),(51,11)],edge,2);e((47,7,55,15),hi);r((49,9,51,11),LIGHT);line([(27,21),(24,31)],dark,3)
        elif role in (3,7):
            shape([(24,17),(24,11),(31,7),(39,9),(43,14),(41,20),(39,16),(31,16)],STEEL);line([(31,9),(34,5),(42,5)],cloth,3);shape([(14,27),(24,24),(30,27),(28,37),(21,43),(15,36)],hi);line([(21,28),(21,38)],GOLD,2);shape([(44,31),(54,12),(57,9),(56,18),(47,34)],STEEL);line([(43,28),(50,33)],GOLD,2)
        elif role==4:
            shape([(23,18),(25,11),(31,6),(39,8),(43,14),(39,13),(32,11),(26,20)],dark);shape([(27,25),(31,24),(35,29),(41,24),(43,28),(36,37)],GOLD);line([(46,44),(50,15)],edge,3);shape([(46,13),(50,5),(56,11),(52,17)],hi);r((50,9,52,11),LIGHT)
        elif role==5:
            shape([(23,17),(18,13),(26,14)],skin);shape([(37,24),(40,19),(40,25)],LIGHT);line([(28,11),(30,7),(37,8)],dark,4);shape([(18,27),(24,23),(28,29),(24,33),(17,32)],hi);line([(46,39),(54,15)],edge,3);shape([(49,13),(51,8),(61,12),(58,20),(53,21)],STEEL)
        elif role in (6,8):
            e((24,8,42,21),skin);r((27,15,30,18),INK);r((35,14,39,17),INK);line([(29,23),(37,22)],edge);line([(42,27),(49,32),(55,24)],skin,3)
            for i in range(3):line([(27,29+i*3),(37,30+i*3)],skin,1)
        else:
            shape([(22,9),(38,7),(45,15),(41,23),(24,23)],hi);line([(27,16),(32,16)],INK);line([(36,15),(41,15)],GOLD);e((12,24,26,38),main);e((41,25,55,41),main)
        if v==1:shape([(19,26),(24,24),(36,36),(34,39)],GOLD);line([(28,13),(31,13)],LIGHT,1)
        if v==2:shape([(21,25),(27,26),(27,36),(19,35)],hi);r((21,27,23,29),GOLD);line([(29,11),(34,9)],LIGHT,1)
    elif kind in ('wolf','stag','boar','cat'):
        for x,y,dx in [(20,35,-4),(28,34,3),(39,34,-1),(45,33,5)]:leg(x,y,dx)
        shape([(17,34),(7,30),(4,22),(12,26),(22,27)],dark);shape([(15,30),(24,24),(36,23),(43,19),(49,22),(51,34),(40,39),(25,38),(16,36)]);shape([(36,24),(41,14),(46,9),(47,17),(54,14),(54,22),(62,25),(59,30),(50,29),(44,35)],main);shape([(22,27),(33,24),(41,23),(35,28),(27,30)],hi);eye(52,21);line([(52,28),(59,27)],INK,1)
        if kind=='stag':
            for dx in [-7,0]:line([(47+dx,18),(45+dx,11),(41+dx,5),(42+dx,2)],GOLD,2);line([(44+dx,10),(48+dx,5)],GOLD,2)
        if kind=='boar':shape([(53,28),(58,24),(61,20),(60,27),(55,31)],LIGHT);line([(26,24),(30,18),(33,23),(37,17),(41,22)],dark,3)
        if kind=='cat':line([(13,30),(6,24),(6,17),(10,15)],main,3);line([(28,28),(31,33)],dark,2);line([(34,26),(37,30)],dark,2)
    elif kind in ('bird','bat','moth','ray'):
        if kind=='bird':
            shape([(34,31),(22,27),(8,13),(9,22),(5,20),(9,30),(17,37),(30,39)],dark);shape([(34,32),(43,15),(57,5),(54,16),(61,12),(58,21),(50,30),(39,37)]);shape([(23,37),(33,27),(41,26),(46,20),(52,22),(51,28),(42,33),(34,40),(16,45)],hi);shape([(50,24),(59,25),(51,28)],GOLD);eye(47,23);line([(35,39),(32,45),(37,44)],GOLD,2)
        else:
            for side in (-1,1):
                mirror=lambda a:[(34+side*x,y) for x,y in a];shape(mirror([(0,31),(8,20),(24,8),(29,10),(25,22),(28,27),(19,28),(17,36),(9,33),(5,44),(0,37)]));shape(mirror([(5,29),(14,21),(23,15),(15,29),(10,31)]),hi);line(mirror([(3,32),(14,25),(23,15)]),dark,1)
            e((29,23,39,40),dark);shape([(29,25),(27,15),(33,21),(38,16),(38,26)],dark);eye(34,24)
            if kind=='ray':line([(34,33),(40,44),(49,49),(56,48)],main,2)
            if kind=='moth':e((13,20,20,26),GOLD);e((48,20,55,26),GOLD);line([(32,24),(27,17),(25,16)],LIGHT,1)
    elif kind in ('crab','spider','beetle','centipede','mantis'):
        for side in (-1,1):
            for j in range(3 if kind!='spider' else 4):
                x=34+side*(10+j);line([(x,29+j*2),(x+side*(10+j),26+j*4),(x+side*(16+j),35+j*4)],dark,3);line([(x+side*(10+j),27+j*4),(x+side*(12+j),29+j*4)],hi,1)
        e((19,20,49,41),dark);e((21,18,47,36),main);shape([(24,25),(30,19),(40,20),(42,23),(31,24),(27,28)],hi);eye(29,31);eye(38,31)
        if kind in ('crab','mantis'):
            for side in (-1,1):
                x=34+side*22;line([(34+side*13,29),(x,23),(x+side*3,16)],main,4);shape([(x-5,19),(x-6,9),(x-1,13),(x+4,7),(x+5,15),(x+2,21)],hi)
        if kind=='beetle':line([(34,20),(34,35)],dark,2);shape([(33,22),(29,14),(31,8),(33,16),(37,12),(36,20)],GOLD)
        if kind=='centipede':
            for j in range(4):e((11+j*7,18+j*3,23+j*7,29+j*3),hi if j%2 else main)
    elif kind=='fish':
        shape([(6,17),(19,23),(29,14),(43,14),(55,22),(60,30),(51,36),(36,40),(23,38),(17,32),(5,39),(10,28)],main);shape([(24,21),(31,9),(38,6),(38,16)],dark);shape([(33,31),(42,29),(34,42),(29,41)],hi);eye(48,23);line([(43,19),(40,26),(42,31)],dark,2);line([(50,31),(58,30)],LIGHT,2)
    elif kind=='serpent':
        pts=[(7,40),(17,33),(29,37),(40,36),(46,31),(43,23),(34,20),(33,15),(40,11),(51,15)];line(pts,dark,9);line([(x,y-2) for x,y in pts],main,6);shape([(43,9),(53,9),(60,15),(58,19),(47,18),(41,14)],hi);eye(53,12);line([(59,17),(64,18)],'#bd6657',1)
    elif kind=='tree':
        leg(25,35,-6);leg(35,34,5);shape([(22,43),(26,22),(19,12),(27,17),(29,5),(34,15),(44,8),(40,23),(43,42),(35,40),(30,35)],main);line([(26,28),(17,25),(12,16),(10,20)],dark,4);line([(39,29),(50,22),(53,13)],main,4);eye(28,24);eye(35,23);line([(27,31),(37,30)],dark);e((18,7,28,15),hi);e((38,6,48,13),hi)
    else:raise ValueError(kind)
    if extra:
        if original in ('priest','judge','scribe'):shape([(23,28),(30,25),(41,27),(44,46),(35,43),(22,47)],main);line([(31,27),(33,42)],GOLD,2);shape([(12,27),(22,29),(29,26),(29,37),(23,40),(13,37)],hi)
        if original=='queen':shape([(17,29),(26,24),(34,28),(42,25),(50,47),(38,44),(31,48),(17,46)],main);line([(25,29),(32,37),(39,29)],GOLD,2)
        if original=='mariner':shape([(16,15),(26,11),(31,5),(38,11),(49,16),(30,15)],dark);line([(19,15),(44,14)],GOLD,2);line([(45,43),(50,22)],STEEL,3)
        if original in ('tower','kiln'):shape([(18,12),(18,5),(22,5),(22,10),(29,10),(29,4),(33,4),(33,10),(39,10),(39,5),(44,5),(44,17)],hi);r((26,27,38,37),dark);line([(28,32),(31,29),(34,33),(37,29)],GOLD,2)
        if original=='ghost':shape([(21,27),(29,26),(39,28),(47,49),(39,44),(34,50),(28,45),(20,50)],hi)
    if kind.startswith('hero') and not extra:
        v=seed%3;role=int(kind[-1]);
        if v==1:
            if role in (0,2,4):shape([(12,28),(22,30),(26,27),(26,36),(20,39),(12,35)],hi);line([(19,31),(19,36)],dark,1)
            else:shape([(12,31),(18,26),(24,31),(23,39),(17,43),(12,38)],GOLD);line([(17,30),(18,39)],dark,2)
        if v==2:
            if role in (0,3,5):line([(12,47),(16,6)],edge,2);shape([(16,6),(26,9),(24,15),(14,13)],hi)
            else:line([(15,26),(18,20),(21,26)],GOLD,2);r((12,26,22,35),dark);r((15,27,20,32),GOLD)
    if not kind.startswith('hero') or extra or boss:
        mode=seed%10; px=25+(seed%4)*3
        if not boss:
            if mode==1:shape([(16,30),(9,18),(15,20),(10,12),(20,17),(25,28)],hi)
            if mode==2:shape([(30,27),(37,22),(43,24),(40,32),(34,36),(30,34)],GOLD);line([(34,29),(39,26)],dark,2)
            if mode==3:line([(22,29),(20,18),(14,10),(14,5)],dark,3);line([(20,18),(24,10)],hi,2)
            if mode==4:shape([(23,28),(15,13),(21,15),(25,8),(30,23)],main);line([(23,25),(23,14)],LIGHT,1)
            if mode==5:line([(23,29),(18,23),(17,16),(12,14)],hi,3);line([(17,17),(22,12)],GOLD,2)
            if mode==6:shape([(22,27),(22,13),(27,17),(30,8),(32,24)],STEEL)
            if mode==7:shape([(21,26),(17,19),(19,13),(26,11),(31,18),(30,26)],main);eye(23,17)
            if mode==8:shape([(21,21),(31,18),(43,23),(40,28),(34,25),(28,31),(23,27)],GOLD)
            if mode==9:line([(19,31),(10,27),(8,16),(13,12)],hi,3);shape([(10,16),(10,8),(14,12),(17,8),(15,17)],GOLD)
        if mode in (1,5,8):shape([(px,24),(px-4,17),(px+2,19),(px+3,13),(px+6,22)],GOLD)
        if mode in (0,3,6):line([(25,27),(30,31),(35,27),(39,30)],hi,2)
        if mode in (2,4,7,9):
            for j in range(2+mode%3):r((24+j*3,26+(j%2)*2,25+j*3,27+(j%2)*2),GOLD)
        if boss:
            shape([(21,14),(18,3),(25,8),(30,1),(34,8),(42,3),(39,14)],GOLD);line([(22,12),(38,12)],LIGHT,2);r((29,9,31,11),'#bb4a40');
            for side in (-1,1):line([(34+side*12,27),(34+side*16,30),(34+side*19,27)],GOLD,2)
    mask=im.getchannel('A');out=Image.new('RGBA',im.size,INK);out.putalpha(mask.filter(ImageFilter.MaxFilter(3)));out.alpha_composite(im);return out

def icon(kind,seed=0):
    im=Image.new('RGBA',(48,48));d=ImageDraw.Draw(im);p=d.polygon;r=d.rectangle;e=d.ellipse; c=['#d08e53','#649a91','#839eb6','#a681ba','#bb7055'][seed%5];h=mix(c,LIGHT,.6);s=mix(c,INK,.52)
    def line(points,color,width=2):d.line(points,fill=color,width=width)
    if kind=='heart':
        p([(3,13),(8,7),(17,7),(23,13),(29,7),(38,7),(44,13),(44,23),(24,42),(3,23)],'#bd4c42');p([(6,13),(10,10),(15,10),(14,14),(10,16),(8,19),(6,19)],'#ffe5aa');line([(9,25),(24,38),(39,24)],'#8f3940',3)
    elif kind=='potion':
        p([(19,5),(29,5),(29,18),(37,26),(38,38),(34,42),(14,42),(10,37),(12,26),(19,18)],'#c9dfd8');liq=['#cb5c56','#63a761','#528dc1','#c1b9ae','#68576e','#d3a24c'][(seed-18)%6];p([(15,29),(21,26),(29,29),(34,26),(35,37),(32,40),(16,40),(13,36)],liq);r((18,4,30,8),'#b98850');line([(15,29),(17,25),(20,23)],LIGHT,2);r((21,10,23,17),LIGHT)
    elif kind in ('helm','crown','chest','boots'):
        if kind=='helm':p([(7,24),(10,16),(16,10),(29,9),(37,15),(41,23),(39,34),(33,38),(33,27),(28,27),(25,33),(21,33),(20,25),(11,26),(11,35),(7,32)],c);line([(10,22),(17,15),(29,13)],h,3);line([(15,23),(34,21)],s,3)
        if kind=='crown':p([(7,15),(16,22),(23,8),(31,22),(40,13),(36,36),(11,36)],GOLD);r((12,30,35,34),s);e((21,24,26,29),c)
        if kind=='chest':p([(7,16),(14,9),(20,8),(23,15),(28,14),(32,8),(39,12),(44,19),(38,27),(33,24),(32,39),(15,39),(14,25),(9,27),(4,22)],c);p([(15,17),(20,20),(30,18),(29,24),(23,28),(16,24)],h);line([(17,34),(30,34)],s,3);line([(8,18),(15,12)],h,2)
        if kind=='boots':
            for x,y in [(6,5),(24,2)]:p([(x+4,y+9),(x+15,y+9),(x+13,y+26),(x+15,y+31),(x+13,y+34),(x,y+34),(x-2,y+30),(x+5,y+26)],c);r((x+4,y+10,x+14,y+13),h);line([(x+1,y+32),(x+13,y+32)],s,2)
    elif kind in ('sword','spear','staff','hammer','axe','horn'):
        line([(9,39),(35,12)],'#825836',4);line([(10,39),(32,15)],GOLD,1)
        if kind in ('sword','spear'):p([(15,30),(32,10),(41,5),(37,16),(19,33)],STEEL);line([(20,29),(35,13)],LIGHT,2);line([(12,25),(23,36)],GOLD,3)
        if kind in ('hammer','axe'):p([(23,8),(28,5),(42,17),(38,25),(32,22),(29,17),(22,15)],c);line([(25,8),(39,20)],h,2)
        if kind=='staff':p([(25,13),(30,4),(39,6),(42,14),(34,20)],c);line([(30,7),(34,8),(30,14)],LIGHT,2)
        if kind=='horn':p([(9,34),(16,34),(25,28),(29,20),(27,14),(38,10),(40,19),(32,30),(20,39),(11,39)],h)
    elif kind in ('bow','crossbow'):line([(8,10),(21,10),(32,17),(38,28),(39,40)],c,4);line([(8,10),(39,40)],LIGHT,1);line([(12,37),(32,15)],s,3);p([(28,16),(35,11),(32,19)],STEEL)
    elif kind in ('lantern','bell'):e((18,5,29,16),GOLD);p([(14,16),(32,16),(36,34),(39,37),(9,37),(12,33)],c);p([(19,20),(28,20),(30,30),(17,30)],'#ffe39f');r((21,37,26,40),s)
    elif kind=='book':p([(7,11),(24,15),(40,10),(40,35),(23,39),(7,34)],c);line([(23,16),(23,36)],GOLD);line([(11,19),(19,21)],h);line([(28,19),(36,17)],h)
    elif kind=='eye':e((5,15,42,33),h);e((17,15,31,33),c);e((21,18,27,29),INK)
    elif kind=='coin':e((8,8,39,39),GOLD);d.ellipse((12,12,35,35),outline=s,width=2);line([(26,16),(19,23),(28,24),(21,31)],LIGHT,2)
    elif kind in ('knot','rune','spark'):p([(24,4),(39,19),(34,35),(24,43),(10,33),(8,20)],c);line([(25,11),(17,24),(29,22),(22,35)],LIGHT,3);line([(11,22),(14,32),(23,38)],s,2)
    elif kind=='portal':d.arc((6,5,41,49),180,360,fill=c,width=6);r((6,24,11,40),c);r((36,24,41,40),c);p([(24,10),(29,15),(24,20),(19,15)],GOLD)
    else:raise ValueError(kind)
    out=Image.new('RGBA',im.size,INK);out.putalpha(im.getchannel('A').filter(ImageFilter.MaxFilter(3)));out.alpha_composite(im);return out
