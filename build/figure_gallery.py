"""One illustrated index of the exact printable meshes per kingdom, plus heroes."""

from concurrent.futures import ProcessPoolExecutor
from textwrap import wrap

from PIL import Image, ImageDraw

from foes import foes
from k1c_plates import BOSSES, ENEMIES, OUTPUT, POSED
from maps import font
from party import heroes
from workshop import render_stl
from world import realms


PALE = '#eee8d8'
INK = '#223c39'
LINE = '#c7b691'
CELL_W, CELL_H = 223, 186
COLORS = {POSED:'#be9672', ENEMIES:'#8b9e84', BOSSES:'#9f7e93'}
COLS = 5


def draw_sheet(task):
    destination, title, records = task
    rows = (len(records)+COLS-1)//COLS
    picture = Image.new('RGB',(CELL_W*COLS+40,rows*CELL_H+100),PALE)
    draw = ImageDraw.Draw(picture)
    draw.text((22,17),title,font=font(35,True,True),fill=INK)
    draw.text((24,61),'Рендеры печатных фигурок · коды совпадают с карточками',font=font(17),fill=INK)
    code_font, name_font = font(15,True), font(14)
    for i,(group,key,name) in enumerate(records):
        x = 20+(i%COLS)*CELL_W
        y = 92+(i//COLS)*CELL_H
        image = render_stl(group,key,(CELL_W,130),COLORS[group])
        picture.paste(image,(x,y))
        center = x+CELL_W/2
        draw.text((center,y+130),key,font=code_font,fill=INK,anchor='ma')
        for line,text in enumerate(wrap(name,29)):
            draw.text((center,y+149+line*15),text,font=name_font,fill=INK,anchor='ma')
        draw.line((x+8,y+CELL_H-2,x+CELL_W-8,y+CELL_H-2),fill=LINE,width=1)
    picture.save(destination)
    print(destination.name,flush=True)


def main():
    directory = OUTPUT/'Все фигурки'/'Атлас фигурок'
    directory.mkdir(parents=True,exist_ok=True)
    mob,bosses = foes()
    roster = [(POSED,f'H{i:02}',h[0]) for i,h in enumerate(heroes,1)]
    tasks = [(directory/'00 Герои.png','Герои островов и побережья',roster)]
    for i,realm in enumerate(realms):
        locals_ = [(ENEMIES,c['id'],c['name']) for c in mob if c['area']==i]
        locals_ += [(BOSSES,c['id'],c['name']) for c in bosses if c['area']==i]
        name = f'{i+1:02} {realm[0]}'
        tasks.append((directory/(name+'.png'),name,locals_))
    with ProcessPoolExecutor(max_workers=4) as pool:
        list(pool.map(draw_sheet,tasks))


if __name__ == '__main__':
    main()
