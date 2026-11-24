"""Draw the assembly overview for the printable case."""

from PIL import Image, ImageDraw

from case_k1c import DESTINATION, figure_trays
from maps import font


def draw_case():
    paper, ink, dark = '#f6efdf', '#25413f', '#162e2e'
    light, brass, muted = '#d6e1ce', '#bf9147', '#536761'
    img = Image.new('RGB', (1300, 1020), paper)
    draw = ImageDraw.Draw(img)

    def label(xy, value, size=19, color=ink, **options):
        draw.text(xy, value, font=font(size, options.pop('bold', False), options.pop('serif', False)),
                  fill=color, **options)

    def slab(y, front, top):
        face = [(90,y),(510,y),(633,y+61),(213,y+61)]
        draw.polygon(face, fill=top, outline=ink, width=2)
        draw.polygon([face[3],face[2],(633,y+75),(213,y+75)], fill=front, outline=ink, width=2)
        draw.polygon([face[0],face[3],(213,y+75),(90,y+14)], fill=front, outline=ink, width=2)

    draw.rectangle((0,0,1300,140), fill=dark)
    label((62,33), 'Море имён', 55, paper, bold=True, serif=True)
    label((64,104), 'Разборный кейс для Creality K1C', 20, '#cfdfd7')
    label((1236,73), '404 × 340 × 352 мм', 26, '#efe0b9', bold=True, anchor='ra')

    # Open lid and the paper pocket are schematic. The layers underneath are pulled up.
    draw.polygon([(87,203),(485,203),(523,316),(109,316)], fill=ink, outline=dark, width=3)
    draw.polygon([(149,222),(440,222),(464,296),(165,296)], fill='#e8d9b7')
    for y in (230,287):
        draw.line([(149+(y-222)//4,y),(441+(y-222)//3,y)], fill=brass, width=6)
    label((305,259), 'ПОЛЕ', 20, ink, bold=True, anchor='mm')
    for x in (131,237,343,449):
        draw.rounded_rectangle((x,309,x+38,322), 4, fill=brass, outline=dark, width=1)
    label((531,220), 'Крышка', 23, bold=True)
    label((531,254), 'Карман для поля', 17, muted)
    label((531,280), 'Четыре петли', 17, muted)

    _, trays = figure_trays()
    for level in range(6,0,-1):
        y = 354+(6-level)*84
        slab(y, '#59786c', light)
        draw.line([(300,y),(423,y+61)], fill=ink, width=2)
        draw.line([(151,y+30),(571,y+30)], fill=ink, width=2)
        tags = [tray[0] for tray in trays if tray[1] == level] if level < 6 else ['H','C1','C2','C3']
        for code,x,dy in zip(tags,(229,439,289,499),(16,16,46,46)):
            label((x,y+dy), code, 19, bold=True, anchor='mm')
        label((66,y+34), str(level), 24, bold=True, anchor='mm')

    slab(875, '#355854', '#9ab0a3')
    label((376,961), 'ДНО · 4 СЕКЦИИ', 19, bold=True, anchor='mm')
    draw.line([(699,185),(699,955)], fill='#ded1b7', width=2)
    label((742,191), 'Верхний ярус', 30, bold=True, serif=True)

    blocks = [('H','18 героев','Две запасные ячейки'),
              ('C1','158 карт','Герои, вещи и боссы'),
              ('C2','200 карт','Существа M001–M200'),
              ('C3','100 карт и жетоны','M201–M300 · четыре отсека')]
    for i,(code,heading,caption) in enumerate(blocks):
        x, y = 742+(i%2)*250, 250+(i//2)*111
        draw.rounded_rectangle((x,y,x+235,y+96), 8, fill='#e4eadc')
        label((x+14,y+11), code, 17, '#653d18', bold=True)
        label((x+14,y+35), heading, 21, bold=True)
        label((x+14,y+66), caption, 16, muted)

    label((742,513), 'Лоток бестиария', 30, bold=True, serif=True)
    label((743,556), '20 мест на лоток · лотки подбираются по области', 17, muted)
    for i in range(20):
        row,col = divmod(i,5)
        x,y = 744+col*93, 603+row*66
        draw.rounded_rectangle((x,y,x+82,y+56), 5, fill='#d3e2d6' if i<15 else '#ebdcc0', outline='#9b9580')
        draw.ellipse((x+36,y+8,x+46,y+18), fill=paper)
        label((x+41,y+37), f'M{i+1:03}' if i<15 else f'B{i-14:03}', 16, bold=True, anchor='mm')
    label((744,887), 'Лоток 01A · пример размещения', 17, muted)
    label((744,916), 'Номер выгравирован под основанием фигурки.', 17, muted)
    img.save(DESTINATION/'Схема.png', optimize=True)


if __name__ == '__main__':
    draw_case()
