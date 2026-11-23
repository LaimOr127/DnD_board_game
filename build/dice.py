"""Generate the 16 mm physical d6 used by the companion table."""
import math
from pathlib import Path

import manifold3d as md
import numpy as np
import trimesh


def main():
    solid = md.Manifold.cube((14, 14, 14), center=True).minkowski_sum(md.Manifold.sphere(1, 32))
    faces = [
        ((0, 0, 0), [(0, 0)]),
        ((0, 90, 0), [(-1, -1), (1, 1)]),
        ((90, 0, 0), [(-1, -1), (0, 0), (1, 1)]),
        ((-90, 0, 0), [(-1, -1), (-1, 1), (1, -1), (1, 1)]),
        ((0, -90, 0), [(-1, -1), (-1, 1), (0, 0), (1, -1), (1, 1)]),
        ((180, 0, 0), [(x, y) for x in (-1, 1) for y in (-1, 0, 1)]),
    ]
    for rotation, dots in faces:
        # The six faces lose equal volumes of material. All recesses are 0.6 mm deep.
        radius = 2.6 / math.sqrt(len(dots))
        for x, y in dots:
            pit = md.Manifold.cylinder(1.0, radius, radius, 32)
            solid -= pit.translate((3.7 * x, 3.7 * y, 7.4)).rotate(rotation)
    raw = solid.translate((0, 0, 8)).to_mesh()
    mesh = trimesh.Trimesh(raw.vert_properties[:, :3], raw.tri_verts, process=True)
    dest = Path(__file__).resolve().parents[1] / "Кубики" / "Береговой d6 — 16 мм.stl"
    dest.parent.mkdir(exist_ok=True)
    dest.write_bytes(mesh.export(file_type="stl"))
    printed = trimesh.load_mesh(dest)
    assert printed.is_volume and len(solid.decompose()) == 1
    assert np.allclose(printed.extents, [16, 16, 16]) and np.linalg.norm(printed.center_mass - [0, 0, 8]) < 0.01
    print(dest.name, "· 16 × 16 × 16 мм · замкнутая модель")


if __name__ == "__main__":
    main()
