"""Render the assembled travel case and the relief markers from actual meshes."""

import numpy as np
from PIL import Image, ImageDraw

from compact_case import AY, AZ, CROWDS, DEST, FLOOR, TRAY_H, W, figure_tray, lid, marker, texture_sample, token_tray, tub
from maps import font


def render(shape, size, color, front=True, accent=None):
    mesh = (shape.rotate((0,0,180)) if front else shape).to_mesh()
    vertices, faces = mesh.vert_properties, mesh.tri_verts
    view = np.array([.58,-1.5,1.4])
    view /= np.linalg.norm(view)
    right = np.cross([0,0,1],view)
    right /= np.linalg.norm(right)
    up = np.cross(view,right)
    points = vertices @ np.stack([right,-up,view]).T
    w,h = size
    pixels = points[:,:2]
    scale = min((w-32)/(np.ptp(pixels[:,0])),(h-32)/(np.ptp(pixels[:,1])))
    pixels[:] = (pixels-(pixels.min(0)+pixels.max(0))/2)*scale+[w/2,h/2]
    image = np.full((h,w,3),[238,232,216],dtype=np.uint8)
    depth = np.full((h,w),-np.inf)
    light = np.array([-.24,-.47,.85])
    for face in faces:
        tri = vertices[face]
        normal = np.cross(tri[1]-tri[0],tri[2]-tri[0])
        if normal @ view <= 0:
            continue
        a,b,c = points[face]
        left,top = np.maximum(np.floor(np.min([a[:2],b[:2],c[:2]],axis=0)).astype(int),0)
        right,bottom = np.minimum(np.ceil(np.max([a[:2],b[:2],c[:2]],axis=0)).astype(int)+1,(w,h))
        x,y = np.meshgrid(np.arange(left,right)+.5,np.arange(top,bottom)+.5)
        ab,ac = b-a,c-a
        area = ab[0]*ac[1]-ab[1]*ac[0]
        u = ((x-a[0])*ac[1]-(y-a[1])*ac[0])/area
        v = (ab[0]*(y-a[1])-ab[1]*(x-a[0]))/area
        z = a[2]+u*ab[2]+v*ac[2]
        tile = depth[top:bottom,left:right]
        valid = (u>=0)&(v>=0)&(u+v<=1)&(z>tile)
        tile[valid] = z[valid]
        paint = accent[2] if accent and normal[2]>0 and accent[0]<tri[:,2].mean()<accent[1] else color
        shade = np.clip(.65+.38*(normal @ light)/np.linalg.norm(normal),.36,1)
        image[top:bottom,left:right][valid] = np.array(tuple(bytes.fromhex(paint[1:])))*shade
    return Image.fromarray(image)


def texture_preview():
    paper,ink = '#eee8d8','#263c39'
    page = Image.new('RGB',(1060,485),paper)
    draw = ImageDraw.Draw(page)
    draw.rectangle((0,0,1060,95),fill=ink)
    draw.text((34,28),'Фактура наружных стенок',font=font(36,True,True),fill=paper)
    for i,caption in enumerate(('Гладкий образец','Образец с фактурой')):
        x = 26+515*i
        page.paste(render(texture_sample(bool(i)),(484,300),'#83a36b'),(x,111))
        draw.text((x+242,421),caption,font=font(22,True),fill=ink,anchor='ma')
    page.save(DEST/'Фактура.png',optimize=True)


def main():
    paper, ink, muted = '#eee8d8', '#263c39', '#526862'
    page = Image.new('RGB',(1250,965),paper)
    draw = ImageDraw.Draw(page)
    draw.rectangle((0,0,1250,128),fill=ink)
    draw.text((40,29),'Море имён',font=font(50,True,True),fill=paper)
    draw.text((1210,70),'Дорожный кейс · 328 × 197 × 124 мм',font=font(23,True),fill=paper,anchor='ra')
    body = tub(False)+tub(True).translate((W,0,0))
    top = lid(False)+lid(True).translate((W,0,0))
    open_top = top.translate((0,-AY,-AZ)).rotate((103,0,0)).translate((0,AY,AZ))
    insert = figure_tray(False).translate((W+6.2,4.2,FLOOR+TRAY_H))
    page.paste(render(body+open_top+insert,(710,460),'#739085'),(0,151))
    draw.text((32,620),'Вертикальные карманы и верхний лоток героев',font=font(22,True),fill=ink)
    draw.text((32,651),'Крышка открыта. Кассета жетонов снята для доступа к картам.',font=font(17),fill=muted)
    page.paste(render(body+top,(496,310),'#739085',accent=(123.2,123.4,'#dfc394')),(736,151))
    page.paste(render(token_tray(),(484,170),'#b78b5c'),(742,459))
    draw.text((755,651),'Съёмная кассета над картами',font=font(18,True),fill=ink)
    draw.line([(35,701),(1215,701)],fill='#b4aa91',width=2)
    draw.text((34,724),'Жетоны толпы',font=font(30,True,True),fill=ink)
    for i,(code,creature,name) in enumerate(CROWDS):
        x = 24+246*i
        page.paste(render(marker(code+'1',creature),(220,128),'#a98554',False,(2.45,3.5,'#f3dfb5')),(x,767))
        draw.text((x+110,908),f'{code}1–{code}3 · {name}',font=font(18,True),fill=ink,anchor='ma')
    page.paste(render(marker('B1'),(215,128),'#a98554',False,(2.45,3.5,'#f3dfb5')),(1009,767))
    draw.text((1117,908),'B1–B2 · боссы',font=font(18,True),fill=ink,anchor='ma')
    page.save(DEST/'Схема.png',optimize=True)
    texture_preview()


if __name__ == '__main__':
    main()
