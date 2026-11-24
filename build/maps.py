"""Printed atlas frame, settlement symbols and the original three tactical zone graphs."""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from web_atlas import FIELD_SIZE, atlas_image
from world import coords, edges, realms, sea

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Море имён"
OUT.mkdir(exist_ok=True)
PLOT = (54, 184, 1956, 1225)
INK = "#263c39"
PAPER = "#f5e7c7"


def font(size, bold=False, serif=False):
    name = ("georgiab" if bold else "georgia") if serif else ("arialbd" if bold else "arial")
    return ImageFont.truetype("C:/Windows/Fonts/" + name + ".ttf", size)


def settlement(draw, x, y, capital):
    """Keep the castle and the paired roofs recognizable without relying on colour."""
    if capital:
        draw.ellipse((x-18,y-18,x+18,y+18),fill=INK,outline="#fbe1a1",width=2)
        for offset in (-9,0,9):
            tower=y-6 if offset else y-11
            draw.rectangle((x+offset-3,tower,x+offset+3,y+9),fill=PAPER)
            draw.rectangle((x+offset-4,tower-2,x+offset+4,tower+1),fill=PAPER)
        draw.rectangle((x-10,y+1,x+10,y+9),fill=PAPER)
        draw.ellipse((x-3,y+2,x+3,y+10),fill=INK)
        draw.line((x,y-12,x,y-16),fill=PAPER,width=1)
        draw.polygon([(x,y-16),(x+6,y-15),(x,y-13)],fill="#e4aa68")
    else:
        draw.ellipse((x-14,y-14,x+14,y+14),fill=PAPER,outline=INK,width=2)
        for xx,yy in [(x-4,y+1),(x+4,y-1)]:
            draw.rectangle((xx-4,yy-1,xx+4,yy+6),fill="#d0a15f",outline=INK)
            draw.polygon([(xx-6,yy),(xx,yy-6),(xx+6,yy)],fill="#994f37",outline=INK)
            draw.line((xx+1,yy+2,xx+1,yy+5),fill=INK,width=2)


def road(draw, a, b, water):
    dx,dy=b[0]-a[0],b[1]-a[1]
    length=math.hypot(dx,dy)
    ink="#163f50" if water else "#694129"
    step=14 if water else 20
    dash=4 if water else 11
    for start in range(0,math.ceil(length),step):
        t=start/length; u=min(length,start+dash)/length
        pair=[(a[0]+k*dx,a[1]+k*dy) for k in (t,u)]
        draw.line(pair,fill="#fae8b9",width=7)
        draw.line(pair,fill=ink,width=3)


def worldmap():
    left,top,right,bottom=PLOT
    w,h=FIELD_SIZE
    page=Image.new("RGB",(2010,1350),PAPER)
    d=ImageDraw.Draw(page)
    d.rectangle((26,26,1984,1324),outline="#847b59",width=2)
    d.rectangle((32,32,1978,1318),outline="#c7b98c",width=1)
    d.text((62,49),"КАРТА СТРАНСТВИЙ",font=font(20,True),fill="#735a34")
    d.text((61,69),"Море имён",font=font(74,True,True),fill=INK)
    d.text((1945,67),"Десять королевств",font=font(38,True,True),anchor="ra",fill=INK)
    d.text((1945,123),"Общий атлас игроков",font=font(23),anchor="ra",fill="#615b45")

    page.paste(atlas_image(),(left,top))
    d.rectangle(PLOT,outline=INK,width=3)
    point=lambda p:(round(left+p[0]*w/100),round(top+p[1]*h/100))
    places=[point(p) for p in coords]
    for a,b in edges:
        road(d,places[a-1],places[b-1],(a,b) in sea or (b,a) in sea)
    for x,y in places:
        d.line((x+17,y-3,x+54,y-11),fill=PAPER,width=5)
        d.line((x+17,y-3,x+54,y-11),fill=INK,width=1)
        settlement(d,x,y,True)
        settlement(d,x+65,y-13,False)

    title, caption = font(23,True,True),font(19)
    # Offset the island label onto open water, leaving the port and barrel crab visible.
    shifts=[(15,26),(10,28),(-7,24),(123,29),(32,29),(29,28),(5,27),(12,32),(-3,27),(30,27)]
    for i,((x,y),realm,(sx,sy)) in enumerate(zip(places,realms,shifts),1):
        area=realm[0]
        names=realm[2]+"  /  "+realm[3]
        width=max(d.textlength(area,font=title)+46,d.textlength(names,font=caption))+22
        cx=int(max(left+width/2+6,min(right-width/2-6,x+sx)));y+=sy
        x0=int(cx-width/2);x1=int(cx+width/2)
        d.rounded_rectangle((x0+2,y+3,x1+2,y+60),radius=5,fill="#665943")
        d.rounded_rectangle((x0,y,x1,y+57),radius=5,fill="#f7e9c8",outline="#5e503a",width=2)
        d.text((x0+10,y+2),f"{i:02}",font=font(17,True),fill="#805937")
        d.text((x0+39,y-1),area,font=title,fill=INK)
        d.text((x0+10,y+30),names,font=caption,fill="#3b4439")

    y=1260
    settlement(d,76,y,True);d.text((103,y),"Столица",font=font(22,True),fill=INK,anchor="lm")
    settlement(d,292,y,False);d.text((315,y),"Деревня",font=font(22,True),fill=INK,anchor="lm")
    road(d,(503,y),(555,y),False);d.text((568,y),"Дорога",font=font(22,True),fill=INK,anchor="lm")
    road(d,(741,y),(798,y),True);d.text((811,y),"Морской путь",font=font(22,True),fill=INK,anchor="lm")
    d.text((1946,y),"Один переход между королевствами занимает день",font=font(22,False,True),anchor="rm",fill=INK)
    d.text((60,1291),"В подписях первым идёт название столицы, следом — деревни. Найденную арку отметьте на своём экземпляре.",font=font(18),fill="#655c42")
    page.save(OUT/"Карта мира.png",dpi=(200,200))
    return page


fields=[('Колокол у брода',['Площадь','Мостки','Звонница','Отмель','Амбар','Лодка'],[(1,2),(2,3),(2,4),(1,5),(5,3),(4,6),(6,3)]),('Подземелье',['Вход','Развилка','Архив','Обвал','Цистерна','Затвор'],[(1,2),(2,3),(2,4),(3,5),(4,5),(5,6)]),('Застава',['Двор','Ворота','Бомбарда','Катапульта','Дорога','Склон'],[(1,2),(1,3),(1,4),(2,3),(2,4),(2,5),(2,6),(5,6)])]
