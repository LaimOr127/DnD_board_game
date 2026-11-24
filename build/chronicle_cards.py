"""Illustrated story backs, duplex A4 decks and single-card print sheets."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas

from printkit import (
    INK, LINE, MUTED, OUT, ROOT, art_for, card, cards, fitted,
    img, pal, rect, stroke, txt, wrap,
)


CW, CH = 63 * mm, 88 * mm
SX, SY = (A4[0] - 3 * CW) / 2, (A4[1] - 3 * CH) / 2
SINGLE_X, SINGLE_Y = (A4[0] - 2 * CW) / 2, A4[1] - 60 * mm - CH
DECKS = {"H": "Герои", "M": "Существа", "B": "Боссы"}
SINGLE_FOLDER = "Карты"
OUTPUT = OUT / "Истории"
PRINT_GUIDE = """Море имён. Иллюстрированные истории

В папке три двусторонние колоды. Герои — 18 карточек, существа — 300, боссы — 100.
На лицевой стороне находятся игровые правила. На обороте — история и подсказка к встрече.

Печать колоды
1. Откройте «Герои.pdf», «Существа.pdf» или «Боссы.pdf». Для пробы выберите страницы 1–2.
2. Выберите A4, книжную ориентацию, фактический размер (100 %) и двустороннюю печать с переворотом по длинной стороне. Одна страница PDF занимает одну сторону листа.
3. На первой стороне первого листа героев H01 находится вверху слева. Переверните лист, как страницу книги. H01 окажется вверху справа, на обороте того же прямоугольника. Проверьте совпадение рамок на просвет.
4. Распечатайте остальные пары в порядке страниц. Разрезайте лист после печати обеих сторон по меткам. Размер готовой карточки 63 × 88 мм.

Одна карточка на обычном принтере
В папке «Карты» найдите PDF по коду, например H01.pdf, M001.pdf или B100.pdf. Выберите одностороннюю печать, A4 и 100 %. Проверьте линейкой контрольные 50 мм. Вырежьте обе половины одним прямоугольником и сложите по центру печатью наружу.
"""


def position(slot, back=False):
    row, col = divmod(slot, 3)
    return SX + (2-col if back else col) * CW, SY + (2-row) * CH


def story_lines(text, size, thumb_w, thumb_h):
    """Wrap around the image for its full height, then across the whole card."""
    lines, line = [], ""
    for word in text.split():
        width = CW - 18 - (thumb_w + 7 if len(lines)*(size+2) < thumb_h else 0)
        candidate = (line + " " + word).strip()
        if line and pdfmetrics.stringWidth(candidate, "G", size) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def back_layout(key, record):
    name = cards[key][0]
    width = CW - 18
    sections = [("В ОТРЯДЕ" if key.startswith("H") else "КОНТРМЕРА", record["counter"]),
                ("ОСЛАБЛЕНИЯ И УСЛОВИЯ", record["debuff"])]
    for tenths in range(94, 72, -1):
        size = tenths / 10
        blocks = [(title,wrap(body,width,"S",size)) for title,body in sections if body]
        for compact in ((False,True) if size <= 8.5 else (False,)):
            if compact:
                thumb_w, thumb_h = 27, 26
                titles = wrap(name,width-thumb_w-5,"GB",10.6)
                top = CH-max(34,30+(len(titles)-1)*12)
                lines = wrap(record["story"],width,"G",size)
                story_height = len(lines)*(size+1.1)
            else:
                thumb_w, thumb_h = 48,63
                titles = wrap(name,width,"GB",12)
                top = CH-24-(len(titles)-1)*13.5-12
                lines = story_lines(record["story"],size,thumb_w,thumb_h)
                story_height = max(thumb_h,len(lines)*(size+2))
            section_step = size + (1.0 if compact else 1.5)
            gap = 3 if compact else 6
            used = story_height + 6 + sum(10 + len(rows)*section_step + gap for _,rows in blocks)
            if top - used >= 16:
                return titles,top,size,thumb_w,thumb_h,lines,story_height,blocks,compact
    raise ValueError(f"{key}: текст оборота не помещается в 63 × 88 мм")


def draw_back(c, key, record, x, y):
    area = cards[key][2]
    titles,top,size,thumb_w,thumb_h,lines,story_h,blocks,compact = back_layout(key,record)
    accent = pal[area]
    c.saveState()
    c.translate(x,y)
    rect(c,0,0,CW,CH,"#fcf8ec")
    stroke(c,LINE)
    c.setLineWidth(.55)
    c.rect(.9,.9,CW-1.8,CH-1.8)
    rect(c,8,CH-10,18,2,accent)
    txt(c,30,CH-11,"БЕРЕГОВАЯ ХРОНИКА",6.3,"SB",MUTED)
    txt(c,CW-9-(thumb_w+5 if compact else 0),CH-11,key,8,"SB",INK,"right")
    for i,line in enumerate(titles):
        txt(c,9,CH-(26+i*12 if compact else 25+i*13.5),line,10.6 if compact else 12,"GB",INK)
    # Preserve the whole source silhouette and its original paper background.
    art = art_for(key)
    scale = min(thumb_w/art.width,thumb_h/art.height)
    iw, ih = art.width*scale, art.height*scale
    art.thumbnail((max(1, round(iw*4)),max(1,round(ih*4))), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    art.save(buffer,"JPEG",quality=89,optimize=True)
    buffer.seek(0)
    art_x,art_top = (CW-9-thumb_w, CH-4) if compact else (9,top)
    img(c,buffer,art_x+(thumb_w-iw)/2,art_top-(thumb_h+ih)/2,iw,ih)
    for i,line in enumerate(lines):
        alongside = not compact and i*(size+2) < thumb_h
        xx = 9 + (thumb_w + 7 if alongside else 0)
        assert pdfmetrics.stringWidth(line,"G",size) <= CW-9-xx+.2, (key,line)
        txt(c,xx,top-size-i*(size+(1.1 if compact else 2)),line,size,"G",INK)
    yy = top - story_h - 6
    for label, rows in blocks:
        stroke(c,LINE)
        c.line(9,yy,CW-9,yy)
        txt(c,9,yy-8,label,6.5,"SB",MUTED)
        yy -= 10
        for line in rows:
            txt(c,9,yy-size,line,size,"S",INK)
            yy -= size+(1 if compact else 1.5)
        yy -= 3 if compact else 6
    passive_label = {"H":"Талант", "M":"Особенность", "B":"Закон арены"}[key[0]]
    footer = passive_label + "   /   " + record["passive_name"]
    stroke(c,LINE)
    c.line(9,14,CW-9,14)
    fitted(c,9,5.5,footer,CW-18,7,"SB",MUTED)
    c.restoreState()


def crop_marks(c, x0, y0, cols, rows):
    stroke(c,MUTED)
    c.setLineWidth(.35)
    for i in range(cols+1):
        x = x0+i*CW
        c.line(x,y0-6,x,y0-1.2)
        c.line(x,y0+rows*CH+1.2,x,y0+rows*CH+6)
    for i in range(rows+1):
        y = y0+i*CH
        c.line(x0-6,y,x0-1.2,y)
        c.line(x0+cols*CW+1.2,y,x0+cols*CW+6,y)


def new_pdf(destination, title):
    c = Canvas(str(destination) if isinstance(destination,Path) else destination,
               pagesize=A4,pageCompression=1,invariant=1)
    c.setTitle(title+" · Море имён")
    c.setAuthor("Море имён")
    return c


def single_pdf(folder, key, record):
    name = cards[key][0]
    buffer = BytesIO()
    c = new_pdf(buffer,key+" · "+name)
    x,y = SINGLE_X,SINGLE_Y
    txt(c,x,A4[1]-65,"МОРЕ ИМЁН     /     КАРТОЧКА ДЛЯ СТОЛА",8,"SB",MUTED)
    fitted(c,x,A4[1]-98,name,2*CW,22)
    txt(c,x,A4[1]-117,key+"   ·   "+cards[key][1],10,"S",MUTED)
    txt(c,x,y+CH+10,"ЛИЦЕВАЯ СТОРОНА",7,"SB",MUTED)
    txt(c,x+CW,y+CH+10,"ОБОРОТ",7,"SB",MUTED)
    card(c,key,x,y)
    draw_back(c,key,record,x+CW,y)
    crop_marks(c,x,y,2,1)
    txt(c,x,y-27,"Печать одной карточки",14,"GB")
    for i,line in enumerate((
        "1. Выберите A4 и масштаб 100 % («Фактический размер»).",
        "2. Вырежьте обе половины одним прямоугольником по внешним меткам.",
        "3. Сложите по центральной линии печатью наружу. Размер 63 × 88 мм.",
    )):
        txt(c,x,y-46-i*15,line,9,"S")
    ruler_y = y-110
    stroke(c,MUTED)
    c.setLineWidth(.65)
    c.line(x,ruler_y,x+50*mm,ruler_y)
    for n in range(6):
        c.line(x+n*10*mm,ruler_y-3,x+n*10*mm,ruler_y+3)
    txt(c,x+54*mm,ruler_y-3,"Контрольный отрезок 50 мм",8,"S",MUTED)
    c.showPage()
    c.save()
    with pymupdf.open(stream=buffer.getvalue(),filetype="pdf") as pdf:
        # A single card only needs the glyphs it actually prints.
        pdf.subset_fonts()
        pdf.save(folder/(key+".pdf"),garbage=4,deflate=True,use_objstms=1,no_new_id=True)


def build(folder):
    from card_lore import card_lore
    singles = folder / SINGLE_FOLDER
    singles.mkdir(parents=True,exist_ok=True)
    (folder/"Как печатать.txt").write_text(PRINT_GUIDE,encoding="utf-8")
    for prefix, group in DECKS.items():
        keys = [key for key in cards if key.startswith(prefix)]
        c = new_pdf(folder/(group+".pdf"),group+" · Двусторонние карточки")
        for i in range(0,len(keys),9):
            batch = keys[i:i+9]
            for back in (False,True):
                for slot,key in enumerate(batch):
                    x,y = position(slot,back)
                    if back:
                        record = card_lore(key)
                        draw_back(c,key,record,x,y)
                        single_pdf(singles,key,record)
                    else:
                        card(c,key,x,y)
                crop_marks(c,SX,SY,3,3)
                side = "ОБОРОТ" if back else "ЛИЦО"
                txt(c,SX,27,f"{group.upper()}   /   {batch[0]} – {batch[-1]}",8,"SB")
                txt(c,A4[0]-SX,27,f"Лист {i//9+1}   ·   {side}",8,"SB",INK,"right")
                txt(c,SX,15,"A4 · 100 % · Двусторонняя печать · Переворот по длинной стороне",7.3,"S",MUTED)
                c.showPage()
        c.save()


def pdf_clip(x, y):
    return pymupdf.Rect(x,A4[1]-y-CH,x+CW,A4[1]-y)


def validate_chronicles(folder=OUTPUT):
    """Validate identity, text, artwork, size and duplex placement for every cut card."""
    from card_lore import card_lore
    keys = {key for key in cards if key[0] in DECKS}
    singles = folder / SINGLE_FOLDER
    assert keys == {path.stem for path in singles.glob("*.pdf")} and len(keys)==418
    pages = {}
    def contents(page, rect, text_page):
        return " ".join(page.get_textbox(rect,textpage=text_page).split())
    def illustration(images, rect):
        return [im["digest"] for im in images if rect.contains(pymupdf.Rect(im["bbox"]))]
    for slot in range(9):
        x,y = position(slot)
        mirrored_x,mirrored_y = position(slot,True)
        assert abs(x+CW+mirrored_x-A4[0])<.001 and y==mirrored_y
    for prefix,group in DECKS.items():
        order = sorted(key for key in keys if key.startswith(prefix))
        with pymupdf.open(folder/(group+".pdf")) as deck:
            pages[group] = len(deck)
            assert len(deck)==2*((len(order)+8)//9)
            for i,key in enumerate(order):
                if i%9 == 0:
                    pair = [deck[2*(i//9)+side] for side in (0,1)]
                    text_pages = [page.get_textpage() for page in pair]
                    images = [page.get_image_info(hashes=True) for page in pair]
                record = card_lore(key)
                with pymupdf.open(singles/(key+".pdf")) as single:
                    assert len(single)==1 and all(abs(v-w)<.02 for v,w in zip(single[0].rect[2:],A4))
                    spread = single[0]
                    single_text = spread.get_textpage()
                    single_images = spread.get_image_info(hashes=True)
                    for back in (False,True):
                        page = pair[back]
                        rect = pdf_clip(*position(i%9,back))
                        text = contents(page,rect,text_pages[back])
                        other = pdf_clip(SINGLE_X+int(back)*CW,SINGLE_Y)
                        assert text==contents(spread,other,single_text), ("single",key,back)
                        art = illustration(images[back],rect)
                        assert len(art)==1 and art==illustration(single_images,other), ("art",key,back)
                        assert key in text and cards[key][0] in text, ("identity",key,back)
                        fields = [record[s] for s in (("story","counter","debuff","passive_name") if back else ("passive","defeat"))]
                        if not back:
                            fields += [cards[key][3],cards[key][5],*(body for _,body in cards[key][4])]
                        for value in fields:
                            assert " ".join(value.split()) in text, (key,value,text)
    return {"карточки":len(keys),"страницы":pages}


def build_chronicles():
    scratch = ROOT / "qa-temp"
    scratch.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="chronicles-",dir=scratch) as temp:
        folder = Path(temp)
        build(folder)
        result = validate_chronicles(folder)
        (OUTPUT/SINGLE_FOLDER).mkdir(parents=True,exist_ok=True)
        for asset in folder.rglob("*"):
            if asset.is_file():
                asset.replace(OUTPUT/asset.relative_to(folder))
    return result


if __name__ == "__main__":
    print(build_chronicles())
