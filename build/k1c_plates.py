"""Arrange the existing FDM pieces as separate objects on Creality K1C plates."""

from itertools import batched, combinations
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from PIL import Image, ImageDraw
import numpy as np
import trimesh

from maps import OUT, font


MODELS = OUT / '3D'
OUTPUT = OUT / 'Пластины K1C'
BED, HEIGHT, MARGIN, GAP = 220, 250, 12, 10
CORE = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
STARTER = ('H01', 'H04', 'H07', 'H10', 'H13', 'H16')
POSED = 'объёмные герои'
ENEMIES = 'объёмные существа'
BOSSES = 'объёмные боссы'
TERRAIN = 'местность'
TOKENS = 'жетоны'


def pieces(group, names, scale=1):
    return [(group, name, scale) for name in names]


PLATES = (
    ('00-test', 'Проба: герой, крепость, деревня', 3, pieces(POSED, ['H01']) + pieces(TERRAIN, ['K01', 'V01'], 2 / 3)),
    ('01-prologue', 'Пролог', 3, pieces(POSED, STARTER) + pieces(ENEMIES, ['M001'] * 3)),
    ('02-heroes', 'Остальные герои', 4, pieces(POSED, [f'H{i:02}' for i in range(1, 19) if f'H{i:02}' not in STARTER])),
    ('03-capitals', 'Десять столиц', 5, pieces(TERRAIN, [f'K{i:02}' for i in range(1, 11)], 2 / 3)),
    ('04-villages', 'Десять деревень', 5, pieces(TERRAIN, [f'V{i:02}' for i in range(1, 11)], 2 / 3)),
    ('05-enemies', 'Осада и Хранитель', 4, pieces(ENEMIES, ['M002', *['M151'] * 3, *['M161'] * 3]) +
        pieces(BOSSES, ['B001', 'B003', 'B005', 'B007', 'B009'])),
    ('06-terrain', 'Местность и застава', 4, pieces(TERRAIN, ['gate', 'wall', 'wall', 'bombard', 'catapult',
        'forest', 'forest', 'mountain', 'cavern', 'portal', 'portal', 'lake', 'field', 'sea'])),
    ('07-health', 'Сердца для шестерых', 5, pieces(TOKENS, ['health-1'] * 18 + ['health-5'] * 6 + ['max-health'] * 6)),
    ('08-markers', 'Искры, припасы и сигналы', 6, pieces(TOKENS, ['spark'] * 18 + ['supply'] * 6 + ['ward'] * 4 + ['danger'] * 3)),
    ('09-relief', 'Плоский пролог и подставки', 5, pieces('герои', STARTER) + pieces('существа', ['M001'] * 3) +
        pieces('планшет', ['base-slot'] * 9 + ['fit-test'])),
)


def geometry(parts):
    meshes = {}
    for part in dict.fromkeys(parts):
        group, name, scale = part
        mesh = trimesh.load_mesh(MODELS / group / f'{name}.stl')
        if not mesh.is_volume or len(mesh.split(only_watertight=False)) != 1:
            raise ValueError(f'Expected one closed solid: {group}/{name}')
        mesh.apply_scale(scale)
        mesh.apply_translation(-mesh.bounds[0])
        meshes[part] = mesh
    return meshes


def arrange(parts, meshes, columns, gap=GAP):
    rows = list(batched(parts, columns))
    depth = [max(meshes[part].extents[1] for part in row) for row in rows]
    y = (BED + sum(depth) + gap * (len(rows) - 1)) / 2
    placements = []
    for row, row_depth in zip(rows, depth):
        width = [meshes[part].extents[0] for part in row]
        x = (BED - sum(width) - gap * (len(row) - 1)) / 2
        y -= row_depth
        for part, part_width in zip(row, width):
            offset = (x, y + (row_depth - meshes[part].extents[1]) / 2, 0)
            placements.append((part, offset))
            x += part_width + gap
        y -= gap
    bounds = [np.array(offset) + meshes[part].bounds for part, offset in placements]
    for low, high in bounds:
        if (low[:2] < MARGIN).any() or (high[:2] > BED - MARGIN).any() or high[2] > HEIGHT:
            raise ValueError(f'Model outside the reserved print area: {low}–{high}')
    for (low, high), (other_low, other_high) in combinations(bounds, 2):
        axis_gap = np.maximum(other_low - high, low - other_high)
        if max(axis_gap[:2]) < gap - 1e-5:
            raise ValueError(f'Insufficient clearance: {low}, {other_low}')
    return placements


def write_plate(path, meshes, placements):
    model = ET.Element('model', xmlns=CORE, unit='millimeter')
    resources = ET.SubElement(model, 'resources')
    ids = {part: str(i) for i, part in enumerate(meshes, 1)}
    for part, solid in meshes.items():
        obj = ET.SubElement(resources, 'object', id=ids[part], type='model', name=part[1])
        mesh = ET.SubElement(obj, 'mesh')
        vertices = ET.SubElement(mesh, 'vertices')
        for x, y, z in solid.vertices:
            ET.SubElement(vertices, 'vertex', x=f'{x:.9g}', y=f'{y:.9g}', z=f'{z:.9g}')
        triangles = ET.SubElement(mesh, 'triangles')
        for a, b, c in solid.faces:
            ET.SubElement(triangles, 'triangle', v1=str(a), v2=str(b), v3=str(c))
    build = ET.SubElement(model, 'build')
    for part, (x, y, z) in placements:
        ET.SubElement(build, 'item', objectid=ids[part], transform=f'1 0 0 0 1 0 0 0 1 {x:.8f} {y:.8f} {z:.8f}')
    with ZipFile(path, 'w') as archive:
        entries = {
            '[Content_Types].xml': '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>',
            '_rels/.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="model" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>',
            '3D/3dmodel.model': ET.tostring(model, encoding='utf-8', xml_declaration=True),
        }
        for name, data in entries.items():
            archive.writestr(ZipInfo(name), data, ZIP_DEFLATED)


def draw_layout(draw, top, name, title, meshes, placements):
    left, heading = top
    size = 440
    y0 = heading + 47
    draw.text((left, heading), f'{name[:2]}  {title}', font=font(26, True), fill='#223c39')
    draw.rectangle((left, y0, left + size, y0 + size), fill='#faf4e5', outline='#b7a67d', width=2)
    draw.rectangle((left + MARGIN * 2, y0 + MARGIN * 2, left + size - MARGIN * 2, y0 + size - MARGIN * 2),
                   outline='#d6c7a5', width=1)
    colors = {POSED: '#946440', ENEMIES: '#a25a52', BOSSES: '#79485a', TERRAIN: '#456d62', TOKENS: '#967445'}
    for part, (x, y, _) in placements:
        w, d, _ = meshes[part].extents
        lx, ly = left + 2 * x, y0 + size - 2 * (y + d)
        xx, yy = lx + 2 * w, ly + 2 * d
        shape = draw.ellipse if part[0] in {POSED, ENEMIES, BOSSES, TOKENS} else draw.rounded_rectangle
        shape((lx, ly, xx, yy), fill=colors.get(part[0], '#64726b'))
        label = {'max-health': 'МАКС', 'health-1': 'ОЗ 1', 'health-5': 'ОЗ 5', 'spark': 'ИСКРА', 'ward': 'ЩИТ',
                 'supply': 'Еда', 'danger': '!', 'base-slot': 'БАЗА', 'fit-test': 'ПАЗ'}.get(part[1], part[1])
        draw.text(((lx + xx) / 2, (ly + yy) / 2), label, font=font(11, True), fill='#fff8ec', anchor='mm')


def main():
    OUTPUT.mkdir(exist_ok=True)
    overview = Image.new('RGB', (1020, 2680), '#eee5d1')
    draw = ImageDraw.Draw(overview)
    draw.text((30, 20), 'Море имён · пластины 220 × 220 мм', font=font(34, True), fill='#223c39')
    for index, (name, title, columns, parts) in enumerate(PLATES):
        meshes = geometry(parts)
        placements = arrange(parts, meshes, columns)
        write_plate(OUTPUT / f'{name}.3mf', meshes, placements)
        draw_layout(draw, (30 + (index % 2) * 500, 83 + (index // 2) * 520), name, title, meshes, placements)
        print(f'{name}: {len(parts)} objects')
    overview.save(OUTPUT / 'Схема пластин.png')


if __name__ == '__main__':
    main()
