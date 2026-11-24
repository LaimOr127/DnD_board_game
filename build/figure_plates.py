"""Place the complete series on K1C plates and index every item by card code."""

import csv
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np

from foes import families, foes
from k1c_plates import BOSSES, CORE, ENEMIES, OUTPUT, POSED, arrange, geometry, pieces, write_plate
from party import heroes
from world import realms


COLLECTION = OUTPUT / 'Все фигурки'
SAMPLE = ['H01', 'H04', 'H07', 'M001', 'M002', 'B001']


def batches():
    mobs, bosses = foes()
    catalog = {f'H{i:02}': (POSED, row[0], row[1]) for i,row in enumerate(heroes,1)}
    catalog.update({r['id']:(ENEMIES,r['name'],families[i//10][0]) for i,r in enumerate(mobs)})
    catalog.update({r['id']:(BOSSES,r['name'],realms[r['area']][0]) for r in bosses})
    plates = [('H-01-09', [f'H{i:02}' for i in range(1,10)], 3),
              ('H-10-18', [f'H{i:02}' for i in range(10,19)], 3)]
    for a in range(len(realms)):
        for f in range(3):
            start = 30*a + 10*f
            plates.append((f'{a+1:02}-M{start+1:03}-M{start+10:03}',[r['id'] for r in mobs[start:start+10]],4))
        start = 10*a
        plates.append((f'{a+1:02}-B{start+1:03}-B{start+10:03}',[r['id'] for r in bosses[start:start+10]],4))
    codes = [code for _, group, _ in plates for code in group]
    assert len(codes) == len(set(codes)) == 418 and set(codes) == set(catalog)
    return catalog, [('00-sample', SAMPLE, 3), *plates]


def check_plate(path, keys, meshes, placements):
    with ZipFile(path) as archive:
        assert archive.testzip() is None, path
        model = ET.fromstring(archive.read('3D/3dmodel.model'))
    ns = {'m':CORE}
    assert model.get('unit') == 'millimeter', path
    object_nodes = {obj.get('id'):obj for obj in model.findall('m:resources/m:object',ns)}
    items = model.findall('m:build/m:item',ns)
    assert [object_nodes[i.get('objectid')].get('name') for i in items] == keys, path
    for item,(part,offset) in zip(items,placements):
        transform = [float(data) for data in item.get('transform').split()]
        assert transform[:9] == [1,0,0,0,1,0,0,0,1] and np.allclose(transform[9:],offset), (path,part)
        model = object_nodes[item.get('objectid')]
        vertices = model.findall('m:mesh/m:vertices/m:vertex',ns)
        triangles = model.findall('m:mesh/m:triangles/m:triangle',ns)
        mesh = meshes[part]
        assert len(vertices) == len(mesh.vertices) and len(triangles) == len(mesh.faces), (path,part)
        payload = np.array([[float(v.get(axis)) for axis in 'xyz'] for v in vertices])
        assert np.allclose(payload, mesh.vertices, atol=1e-6), (path,part)
        indices = np.array([[int(t.get(key)) for key in ('v1','v2','v3')] for t in triangles])
        assert np.array_equal(indices,mesh.faces), (path,part)


def main():
    COLLECTION.mkdir(exist_ok=True)
    catalog, plates = batches()
    available = {name+'.3mf' for name,_,_ in plates}
    extra = {p.name for p in COLLECTION.glob('*.3mf')} - available
    if extra:
        raise ValueError(f'Extra print plates in {COLLECTION}: {sorted(extra)}')
    with (COLLECTION/'Указатель.csv').open('w',encoding='utf-8-sig',newline='') as index:
        writer = csv.writer(index,delimiter=';')
        writer.writerow(['Файл 3MF','Код','Имя на карточке','Семейство или королевство','Ряд от задней кромки',
                         'Место слева','Ширина, мм','Глубина, мм','Высота с базой, мм'])
        for name,codes,columns in plates:
            parts = [pieces(catalog[key][0],[key])[0] for key in codes]
            meshes = geometry(parts)
            placements = arrange(parts,meshes,columns)
            for pos,(part,_) in enumerate(placements):
                code = part[1]
                mesh = meshes[part]
                assert 0 < mesh.extents[2] <= 50, (code,mesh.extents)
                writer.writerow([name+'.3mf',code,*catalog[code][1:],pos//columns+1,pos%columns+1,
                                 *(f'{number:.2f}' for number in mesh.extents)])
            path = COLLECTION / (name+'.3mf')
            write_plate(path,meshes,placements)
            check_plate(path,codes,meshes,placements)
            print(name,len(parts),flush=True)


if __name__ == '__main__':
    main()
