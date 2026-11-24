"""A four-sheet, true-scale travel board. Geometry and type sizes are in millimetres."""
import io
from math import cos, pi, sin

from PIL import Image
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

from web_atlas import atlas_image
from world import coords, edges, realms, sea


TILE_W, TILE_H = 268, 180
W, H = 2 * TILE_W, 2 * TILE_H
BLEED = 5
FIELD_TOP = 337
FIELD_H = W * 1041 / 1902
TOKEN_R = 13.3
INK, MUTED, PAPER = "#213f3b", "#5c6859", "#f6ead1"
GOLD, TEAL = "#835531", "#18576b"
TILES = ((0,1,"А1"),(1,1,"А2"),(0,0,"Б1"),(1,0,"Б2"))


def label(c,x,y,value,size=3.5,face="S",color=INK,anchor="left"):
    c.setFont(face,size)
    c.setFillColor(color)
    draw = {"left":c.drawString,"center":c.drawCentredString,"right":c.drawRightString}[anchor]
    draw(x,y,value)


def box(c,x,y,w,h,fill,radius=0,outline=None):
    c.setFillColor(fill)
    if outline:
        c.setStrokeColor(outline)
        c.setLineWidth(.35)
    c.roundRect(x,y,w,h,radius,fill=1,stroke=bool(outline))


def node_points():
    pts = {i:(x*W/100,FIELD_TOP-y*FIELD_H/100)
           for i,(x,y) in enumerate(coords,1)}
    # Keep the two central used-as-stands nodes and their readings off the paper seam.
    pts[7] = (pts[7][0]+23,pts[7][1])
    pts[8] = (pts[8][0]-5,pts[8][1])
    return pts


def route(c,a,b,pair=None,water=False):
    water = water or pair in sea
    path = c.beginPath()
    path.moveTo(*a)
    if pair == (1,4):
        path.curveTo(a[0]-19,a[1]-5,b[0]-12,b[1]+14,*b)
    elif pair == (4,8):
        path.curveTo(a[0]+38,a[1]-7,b[0]-41,b[1]-31,*b)
    else:
        path.lineTo(*b)
    c.setLineCap(1)
    for color, width, dash in [(PAPER,3.9,()), (TEAL if water else "#634a35",2.35,()),
                               ("#d5f1e7" if water else "#e5b369",.95,(2.2,2.6) if water else ())]:
        c.setStrokeColor(color)
        c.setLineWidth(width)
        c.setDash(dash)
        c.drawPath(path)
    c.setDash()


def node(c,i,x,y):
    title,village = realms[i-1][0],realms[i-1][3]
    for r,fill,outline in [(TOKEN_R+1.7,PAPER,"#60523b"),(TOKEN_R,"#f9edd3","#826845")]:
        c.setFillColor(fill); c.setStrokeColor(outline); c.setLineWidth(.5)
        c.circle(x,y,r,fill=1)
    c.setStrokeColor("#aa9870"); c.setLineWidth(.26)
    for j in range(12):
        angle = j*pi/6
        c.line(x+(TOKEN_R+.35)*cos(angle),y+(TOKEN_R+.35)*sin(angle),
               x+(TOKEN_R+1.15)*cos(angle),y+(TOKEN_R+1.15)*sin(angle))
    label(c,x,y-2.6,f"{i:02}",8.2,"GB","#806b48","center")
    name = f"{i:02}  {title}"
    name_width = stringWidth(name,"GB",4.05)
    sub_width = stringWidth(village,"S",3.35)
    width = max(name_width,sub_width,33)+6
    label_x = min(TILE_W-2-width/2,x) if x<TILE_W else max(TILE_W+2+width/2,x)
    y0 = y-TOKEN_R-16.1
    box(c,label_x-width/2,y0,width,15.8,PAPER,1.6,"#63593d")
    label(c,label_x,y0+10.65,name,4.05,"GB",INK,"center")
    label(c,label_x,y0+6.1,village,3.35,"S",MUTED,"center")
    x0=label_x-width/2+2.7
    label(c,x0,y0+1.65,"Вход",2.7,"S",MUTED)
    c.setLineWidth(.2);c.setStrokeColor("#97896d")
    c.line(x0+8,y0+2,label_x+width/2-2.7,y0+2)


def tracker(c,x,y,width,title,maximum,notes):
    box(c,x,y,width,35,"#f9f0d9",2,"#b5a37c")
    label(c,x+4,y+27,title,4.3,"GB")
    gap = min(13.2,(width-14)/(maximum+1))
    for value in range(maximum+1):
        xx=x+9+value*gap
        c.setLineWidth(.36); c.setStrokeColor("#8f805d"); c.setFillColor("#fff7e7")
        c.circle(xx,y+17,4.9,fill=1)
        label(c,xx,y+15.4,str(value),3.7,"SB",INK,"center")
    label(c,x+4,y+4.1,notes,3.1,"S",MUTED)


def master_board(c):
    c.beginForm("travel-board",0,0,W,H)
    box(c,0,0,W,H,PAPER)
    art = atlas_image()
    # Retain the biome silhouettes while keeping the playing routes unmistakable.
    art = Image.blend(art,Image.new("RGB",art.size,"#f4e5c4"),.46)
    buf = io.BytesIO(); art.save(buf,format="JPEG",quality=88); buf.seek(0)
    c.drawImage(ImageReader(buf),0,FIELD_TOP-FIELD_H,W,FIELD_H)
    points = node_points()
    for a,b in edges:
        route(c,points[a],points[b],(a,b))
    for i,(x,y) in points.items():
        node(c,i,x,y)
    box(c,0,FIELD_TOP,W,H-FIELD_TOP,INK)
    label(c,8,H-7,"МОРЕ ИМЁН     /     ПОЛЕ ПУТЕШЕСТВИЙ",3.2,"SB","#e4c490")
    label(c,8,H-18,"Десять королевств",8.5,"GB","#fff1d0")
    label(c,TILE_W+6,H-9,"ОТ ЦЕНТРА ОДНОГО КРУГА ДО СОСЕДНЕГО  •  1 ДЕНЬ",3.5,"SB","#fff1dc")
    label(c,TILE_W+6,H-17,"Под названием области указана местная деревня.",3.6,"S","#e8e4cd")
    for x,word,water in [(W-101,"Дорога",False),(W-56,"Переправа",True)]:
        route(c,(x,H-12),(x+13,H-12),water=water)
        label(c,x+16,H-13.6,word,3.8,"SB","#fff1dc")
    tracker(c,7,5,123,"Прилив",6,"На 6 запишите шрам, закройте лавку и вернитесь на 0.")
    tracker(c,135,5,125,"Общие припасы",6,"На старте 3. Один морской переход можно оплатить припасом.")
    box(c,TILE_W+7,5,120,35,"#f9f0d9",2,"#b5a37c")
    label(c,TILE_W+11,32,"День пути",4.3,"GB")
    label(c,TILE_W+11,21,"День __________",4.6,"SB")
    label(c,TILE_W+71,21,"Шрамы ______",4.2,"SB")
    label(c,TILE_W+11,9.1,"Каждый третий день добавьте 1 прилив.",3.1,"S",MUTED)
    tracker(c,TILE_W+132,5,129,"Общее подозрение",4,"На 4 начинается суд. Его исход запишите в хронике.")
    c.setLineWidth(.8);c.setStrokeColor(INK);c.rect(.4,.4,W-.8,H-.8)
    c.endForm()


def build_guide(c):
    c.setPageSize(landscape(A4));c.saveState();c.scale(mm,mm)
    box(c,0,0,297,210,"#fcf7e8")
    box(c,0,182,297,28,INK)
    label(c,11,201,"МОРЕ ИМЁН   /   МАРШРУТНОЕ ПОЛЕ",3.2,"SB","#dfbc83")
    label(c,11,188,"Как собрать и разыграть переход",7.4,"GB","#fff0d1")
    label(c,286,190,"4 ЛИСТА А4   /   536 × 360 ММ",3.45,"SB","#e8ccb0","right")
    label(c,11,171,"Сборка поля",5.9,"GB")
    # A miniature of the actual assembled art fixes both orientation and the tile order.
    x,y,scale = 11,111,.14
    c.saveState();c.translate(x,y);c.scale(scale,scale);c.doForm("travel-board");c.restoreState()
    c.setStrokeColor("#f8f0ce");c.setLineWidth(.8)
    c.line(x+TILE_W*scale,y,x+TILE_W*scale,y+H*scale)
    c.line(x,y+TILE_H*scale,x+W*scale,y+TILE_H*scale)
    for col,row,name in TILES:
        lx,ly=x+col*TILE_W*scale+1,y+(row+1)*TILE_H*scale-6
        box(c,lx,ly,8,5,INK,1)
        label(c,lx+4,ly+1,name,3.1,"SB",PAPER,"center")
    def lines(x,y,seq,size=3.4,leading=5.25):
        for j,line in enumerate(seq):
            label(c,x,y-j*leading,line,size)
    lines(11,103,["1. Распечатайте следующие четыре листа","   на А4 в альбомной ориентации.","   Выберите «Фактический размер» или 100%.",
                  "2. На листах А2 и Б2 срежьте левое поле","   по тонким меткам. На Б1 и Б2 так же","   срежьте верхнее поле.",
                  "3. Совместите одинаковые рисунки","   соседей на полосе 5 мм. Склейте верхний","   и нижний ряды, затем соедините ряды.",
                  "4. По внешним меткам подрежьте край.","   Можно обрезать все листы по меткам","   и соединить их с изнанки лентой."],3.45,5.6)
    label(c,11,26,"Проверка масштаба линейкой",3.65,"SB")
    c.setStrokeColor(INK); c.setLineWidth(.5);c.line(11,15,61,15)
    for j in range(6): c.line(11+10*j,13.5,11+10*j,17)
    label(c,64,13.6,"50 мм",3.5,"SB")
    c.setLineWidth(.3); c.setStrokeColor("#c9b994")
    c.line(96,12,96,173); c.line(186,12,186,173)
    label(c,103,171,"Связи королевств",5.9,"GB")
    label(c,103,157,"13 сухопутных дорог",4.2,"SB",GOLD)
    land=[p for p in edges if p not in sea]
    for i,(a,b) in enumerate(land):
        xx = 104+(i//7)*39
        yy = 146-(i%7)*7.1
        label(c,xx,yy,f"{a:02}  —  {b:02}",4.1,"SB")
    label(c,103,92,"2 морские переправы",4.2,"SB",TEAL)
    for i,(a,b) in enumerate(p for p in edges if p in sea):
        label(c,104,81-i*7.1,f"{a:02}  ≈  {b:02}",4.1,"SB",TEAL)
    c.setLineWidth(.25);c.setFillColor(INK);c.setStrokeColor(INK)
    c.circle(163,76.5,12.5,fill=1)
    c.setStrokeColor("#d9b879");c.circle(163,76.5,10.9,stroke=1,fill=0)
    label(c,163,77,"ОТРЯД",3.7,"SB","#f7e9c8","center")
    label(c,163,71.8,"Ø 25 мм",2.75,"S","#e7cf9b","center")
    lines(103,61,["За весь отряд заплатите 1 серебро","или 1 припас при каждом морском","переходе. В пути пройдёт один день."],3.5)
    label(c,103,36,"Старт кампании",4.2,"SB",GOLD)
    lines(103,27,["01 Вельн, деревня Три Ивы.","На большой круг поставьте фишку","всего отряда диаметром до 25 мм.","Фишку «Отряд» можно вырезать."],3.45)
    label(c,193,171,"День в пути",5.9,"GB")
    lines(193,158,["Выберите линию между соседними кругами.","Перенесите фишку, отметьте день и бросьте d6","на этом ребре один раз за день."],3.45)
    events=["Столкновение с местным существом.","Встреча с путником.","Добавьте 1 общий припас.","Найден след местной арки.","Погода. Потратьте припас или потеряйте день.","Дорога спокойна."]
    for i,event in enumerate(events,1):
        yy=135-(i-1)*6.7
        box(c,193,yy-1.3,5.3,5.1,INK,1)
        label(c,195.65,yy,str(i),3.2,"SB","#fff1d0","center")
        label(c,201,yy,event,3.28)
    lines(193,91,["За потерянный день новое событие не бросают.","На приливе 6 закройте лавку последней области","до конца следующей сцены. Отметьте шрам."],3.4)
    label(c,193,65,"Подземелья и тайные арки",4.5,"GB")
    lines(193,55,["Под областью подписана деревня. После местного","дела впишите открывшееся название входа.","Подземелье начинайте с глубины I на поле стр. 3.",
                      "После следа исследуйте ориентир из ключа.","Только при открытии поставьте арку рядом с","номером области. Между двумя открытыми арками","переход без дня стоит 1 припас или +1 прилив.","Во время боя пользоваться аркой нельзя."],3.35,5.1)
    c.restoreState();c.showPage()


def tile_page(c,col,row,name):
    c.setPageSize(landscape(A4));c.saveState();c.scale(mm,mm)
    left,bottom=14.5,15
    bleed_l = BLEED if col else 0
    bleed_r = 0 if col else BLEED
    bleed_b = 0 if row==0 else BLEED
    bleed_t = BLEED if row==0 else 0
    c.saveState()
    clip = c.beginPath()
    clip.rect(left-bleed_l,bottom-bleed_b,TILE_W+bleed_l+bleed_r,TILE_H+bleed_b+bleed_t)
    c.clipPath(clip,stroke=0,fill=0)
    c.translate(left-col*TILE_W,bottom-row*TILE_H)
    c.doForm("travel-board")
    c.restoreState()
    c.setLineWidth(.27);c.setStrokeColor(INK)
    for x,dx in [(left,-1),(left+TILE_W,1)]:
        for y,dy in [(bottom,-1),(bottom+TILE_H,1)]:
            c.line(x+dx*6,y,x+dx*9,y);c.line(x,y+dy*6,x,y+dy*9)
    label(c,left+4,202.5,"МОРЕ ИМЁН    /    "+name,3.65,"SB")
    label(c,left+TILE_W-4,202.5,"СЕВЕР  ↑     •     ПЕЧАТЬ 100%",3.3,"SB",MUTED,"right")
    horiz = "А2" if name=="А1" else "Б2" if name=="Б1" else "А1" if name=="А2" else "Б1"
    vert = ("Б" if row else "А")+name[1]
    text=(f"{'Слева' if col else 'Справа'} соседний лист {horiz}. "
          f"{'Снизу' if row else 'Сверху'} лист {vert}.")
    label(c,left+4,5.7,text,3.2,"S",MUTED)
    c.setLineWidth(.3);c.setStrokeColor(INK)
    c.line(112,6.3,162,6.3);c.line(112,5,112,7.6);c.line(162,5,162,7.6)
    label(c,165,5.4,"50 мм",2.9,"SB",MUTED)
    label(c,left+TILE_W-4,5.7,"Тонкие метки задают готовый край 268 × 180 мм.",3.1,"S",MUTED,"right")
    c.restoreState();c.showPage()


def append_travel_board(c):
    master_board(c)
    build_guide(c)
    for col,row,name in TILES:
        tile_page(c,col,row,name)
