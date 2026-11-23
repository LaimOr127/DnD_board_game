from printkit import *
from appendix import levels,landmarks
from maps import font
import numpy as np,trimesh
from PIL import ImageOps

def render_stl(group,name,size=(500,320),color='#bb8d5d',vertical=False):
    o=trimesh.load_mesh(OUT/'3D'/group/(name+'.stl'),process=False);v=o.vertices.copy()
    if vertical:v=v[:,[0,2,1]]*np.array([1,-1,1])
    direction=np.array([.69,-1.45,1.30] if not vertical else [.49,-1.7,.62]);direction/=np.linalg.norm(direction);right=np.cross([0,0,1],direction);right/=np.linalg.norm(right);up=np.cross(direction,right)
    q=np.column_stack((v@right,-v@up));w,h=size;ext=np.ptp(q,axis=0);scale=min((w-32)/max(ext[0],1),(h-32)/max(ext[1],1));q=(q-(q.min(0)+q.max(0))/2)*scale+[w/2,h/2];f=o.faces;tri=v[f];normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);normal/=np.maximum(1e-8,np.linalg.norm(normal,axis=1))[:,None];light=np.array([-.6,-.8,1.7]);light/=np.linalg.norm(light);intens=np.clip(.59+.48*(normal@light),.26,1.16);rgb=np.array(tuple(bytes.fromhex(color[1:])));im=Image.new('RGB',size,'#eee8d8');d=ImageDraw.Draw(im)
    for j in np.argsort(tri.mean(1)@direction):
        if normal[j]@direction<=.001:continue
        zorig=o.vertices[o.faces[j],2].mean();surface=rgb
        if vertical:
            if zorig>2.77:surface=np.array([239,200,132])
            elif zorig>2.32:surface=np.array([86,121,113])
            elif zorig>1.93:surface=np.array([63,76,74])
        pp=[tuple(x) for x in q[f[j]]];col=tuple(np.clip(surface*intens[j],0,255).astype(int));d.polygon(pp,fill=col)
    return im

def plate(name,title,sub,records,cols=4):
    width=1520;cellwidth=width//cols;rows=math.ceil(len(records)/cols);hh=212;im=Image.new('RGB',(width,145+rows*(hh+43)+38),'#eee8d8');d=ImageDraw.Draw(im);d.text((34,28),title,font=font(43,True,True),fill=INK);d.text((37,92),sub,font=font(20),fill=MUTED)
    for i,(group,k,label,clr0,vert) in enumerate(records):
        x=(i%cols)*cellwidth;y=134+(i//cols)*(hh+43);thumb=render_stl(group,k,(cellwidth-14,hh),clr0,vert);im.paste(thumb,(x+7,y));d.text((x+cellwidth//2,y+hh+11),label,font=font(20,True),fill=INK,anchor='ma');d.line((x+20,y+hh+36,x+cellwidth-20,y+hh+36),fill='#ccbea7',width=1)
    (OUT/'Галерея').mkdir(exist_ok=True);im.save(OUT/'Галерея'/(name+'.png'));return im

def overlay():
    im=Image.open(OUT/'Карта мира.png').copy();d=ImageDraw.Draw(im);w,h=im.size;d.rectangle((55,40,1150,171),fill='#f2e8ce');d.text((68,48),'АТЛАС  /  ЛИСТ 02     •     ДЛЯ ВЕДУЩЕГО',font=font(19,True),fill='#816445');d.text((65,78),'Опасные рубежи',font=font(59,True,True),fill=INK);d.rectangle((880,h-108,w-60,h-40),fill='#f2e8ce');d.text((w-68,h-83),'I–V  =  фиксированная ступень вылазки',font=font(22,True),fill='#844c3c',anchor='ra')
    for i,(cx,cy) in enumerate(coords):
        x=54+int(cx*(w-108)/100)+37;y=184+int(cy*(h-309)/100)-35;d.polygon([(x,y-15),(x+20,y),(x,y+15),(x-20,y)],fill='#813f37',outline='#f0d7a3',width=2);d.text((x,y),['I','II','III','IV','V'][levels[i]-1],font=font(14,True),anchor='mm',fill='#fff5d6')
    im.save(OUT/'Карта угроз.png');return im

def main():
    scenery=[('планшет','A-hero','Планшет: герой','#bc8c5b',False),('планшет','B-loadout','Планшет: снаряжение','#bc8c5b',False),('местность','K02','Кремноград','#a59d89',False),('местность','V03','Лисья Гать','#ad8d66',False),('местность','mountain','Горный перевал','#a5a896',False),('местность','forest','Ольховая роща','#82967c',False),('местность','portal','Скрытая арка','#659a96',False),('местность','gate','Ворота заставы','#a8977d',False),('местность','bombard','Бомбарда','#908e84',False),('местность','catapult','Катапульта','#ae885f',False),('герои','H07','Мара • рельеф','#ba8c6c',True),('боссы','B001','Медный Вдовец • рельеф','#9f907e',True)]
    spread=plate('Мастерская','С литейного двора','Изображения построены по готовым STL. Цвет условный; миниатюры персонажей — рельефные фишки.',scenery)
    plates=[]
    for batch in range(2):
        records=[]
        for i in range(batch*5,batch*5+5):
            records.extend([('местность',f'K{i+1:02}',realms[i][2],pal[i],False),('местность',f'V{i+1:02}',realms[i][3],mix(pal[i],'#dcc498',.4),False)])
        plates.append(plate('Поселения '+str(batch+1),'Столицы и деревни · '+str(batch+1),'Пары K (крепость столицы) и V (поселение). Региональный номер соответствует общей карте.',records,cols=5))
    figs=plate('Герои на базах','Свидетели десяти корон','Все 18 объёмных вариантов H. Имена и снаряжение соответствуют картам.',[('объёмные герои',f'H{i+1:02}',h[0],pal[i//3],False) for i,h in enumerate(heroes)],cols=6)
    best=plate('Бестиарий на базах','Обитатели побережья','Примеры объёмных фигур; рядом с ними в архиве лежат облегчённые рельефные варианты.',[('объёмные существа' if k[0]=='M' else 'объёмные боссы',k,cards[k][0].split(' · ')[0],pal[cards[k][2]],False) for k in ['M001','M019','M049','M058','M075','M093','M145','M194','B001','B032','B068','B100']],cols=4)
    threat=overlay();c=Canvas(str(OUT/'08 Мастерская.pdf'));c.setTitle('Литейный двор · Комплект для 3D-печати');
    blocks=[('p','Файлы STL заданы в миллиметрах. Это настольные игровые компоненты. Для каждого героя, существа и босса есть два варианта: объёмная миниатюра на круглой базе и плоская рельефная фишка с ножкой. Здания и местность объёмные. Короны, знаки и формы читаются в одноцветном пластике. Цвет в каталоге дан как идея покраски.'),('h','Первая печать'),('p','Начните с fit-test и base-slot. Ножка 12 × 1,8 мм; паз 12,7 × 2,3 мм и глубиной 3,55 мм. Если пробник встал, напечатайте H-карты своего отряда, M001 в количестве из пролога, несколько сердец и по одной подставке на фигуру. STL-фишку печатают плашмя рельефом вверх, затем ставят вертикально в базу. У каждого вида и босса есть личный код. Установка масштаба 100%; при изменении масштаба одинаково масштабируйте базу и фишку.'),('h','Планшет, жетоны, коробка'),('p','A-hero и B-loadout — независимые модули по 150 × 105 мм, укладываются рядом. На A есть углубление 90 × 64 мм для горизонтального хранения карты 88 × 63, две малые чаши и стойки. На B три ряда пазов: разложите оружие, три части брони, усиление, пояс и запас. У стоек A зазор 1,6 мм, B — 1,8 мм; перед печатью сравните со своим протектором. Для листа без пластика в PDF полей есть бумажная версия. Коробка и крышка — одна неполная колода на коробку; внутренняя площадь 67,6 × 91,6 мм, полезная высота 32 мм. Не пытайтесь поместить весь бестиарий в один короб.'),('h','Номиналы и масштабы'),('p','health-1 = 1 ОЗ; health-5 с пятью точками = 5 ОЗ; max-health с отверстием отмечает максимум на записи, не ещё одно лечение. Для каждого на старте: например, одно сердце 5 и три по 1, плюс монеты для сдачи. spark — искра, ward — щит, danger — сигнал. I01–I40 — индивидуальные предметные жетоны. K01–K10 — столицы, V01–V10 — деревни. Рельефные H/M высотой около 26 мм вместе с ножкой, боссы около 31 мм. Для объёмного варианта берите папку «объёмные …»: подставка уже часть модели. Полностью разложенный большой бой удобнее вести на тактических листах формата A3; расстояние определяют рёбра зон, не миллиметры.')];bookpage(c,'Что ставить на стол',blocks,1,'Мастерская')
    for im in [spread,figs,best]+plates+[threat]:
        ww,hh=landscape(A4);c.setPageSize((ww,hh));sw=min(ww-24,(hh-24)*im.width/im.height);sh=sw*im.height/im.width;img(c,im,(ww-sw)/2,(hh-sh)/2,sw,sh);c.showPage()
    bookpage(c,'Что печатать дальше',[('h','Местность для общего стола'),('p','Для походной карты возьмите крепости K и деревни V нужных областей, лес, гору, озеро, поле и морской тайл. Арку portal держите вне поля до раскрытия. Один жетон опасности кладите у текущего места вылазки; уровень на карте угроз фиксирован. Наборы depth-1 … depth-5 обозначают номера глубин числом ступеней. В пещеру ставьте cavern и нужную лестницу, а сам бой ведите по схеме зон.'),('h','Осада'),('p','Поставьте gate в зону 2, wall по бокам, bombard в 3, catapult в 4. Орудия монолитные: поворот на четверть оборота означает разрядку, возврат — зарядку. Урон и область действия заданы на стр. 10 правил. Для ворот подойдут дополнительные сердца или бумажный счётчик.'),('h','Карты и бумага'),('p','Колоды по девять карт 63 × 88 мм на A4; односторонняя печать при 100%, без «подогнать под страницу». Для проверки линейкой ширина трёх карт вместе должна быть 189 мм. Толстую рамку можно оставить на краю. Для дубликатов и старта есть прозрачная система кодов: отдельные изображения лежат в папке «Карточки PNG», карточка M001 соответствует фигурке M001.stl. Рисунок на экране и рисунок на рельефе относятся к одной игровой записи.'),('h','Перед большой партией'),('p','В этом наборе проверена цифровая геометрия. Реальная посадка, стойкость мелких деталей и удобство зависит от принтера, материала и толщины карты: начните с одной базы, одного пробника и одного персонажа. Если фишка болтается, тонкую бумагу можно использовать как прокладку. На объёмной фигуре проверьте в слайсере выступы и необходимость поддержек; рельефная альтернатива печатается плоской спиной вниз.')],8,'Мастерская');c.save()
if __name__=='__main__':main()
