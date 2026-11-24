"""H04, a trial sculpt of Brom as a dwarven miner and tunnel shorer."""

from math import acos, atan2, degrees, hypot, pi

from PIL import Image
from trimesh.transformations import rotation_matrix

from k1c_plates import arrange, write_plate
from maps import OUT
from models import M, cyl, idrel, union
from scenery_sample import mesh


def oval(x,y,z,a,b,c):
    return M.sphere(1,36).scale((a,b,c)).translate((x,y,z))


def track(points, radii):
    shapes = [oval(*point,r,r,r) for point,r in zip(points,radii)]
    for a,b,r,s in zip(points,points[1:],radii,radii[1:]):
        x,y,z = (j-i for i,j in zip(a,b))
        length = hypot(x,y,z)
        shapes.append(M.cylinder(length,r,s,24).rotate((0,degrees(acos(z/length)),0))
                      .rotate((0,0,degrees(atan2(y,x)))).translate(a))
    return union(shapes)


def armour():
    parts = [oval(.1,.78,19.3,5.8,4.14,6.05),oval(-.45,1.25,23.57,6.55,4.08,4.66),
             oval(-.85,1.74,26.12,3.22,2.5,3.3),oval(0,0,14.8,5.35,3.73,3.66)]
    for side,foot,knee in [(-1,(-3.9,-2.12,4.1),(-4.55,-1.73,9.6)),(1,(3.58,2.15,4.08),(4.54,2.5,10.3))]:
        x,y,z = foot
        parts += [oval(x,y-1.0,z,2.46,3.22,1.98),
                  track([foot,knee,(side*3.28,.39,15.25)],[2.19,2.43,2.84]),
                  oval(knee[0],knee[1]-1.9,knee[2]+.55,1.77,1.31,1.78)]
        for layer in range(3):
            parts.append(oval(x+.08*side,y-.75,4.65+layer*1.20,2.29,2.11,.81))
        # Three overlapping skirt plates with rounded lower edges and bosses.
        for row in range(3):
            parts.append(oval(side*(2.72+.33*row),-2.62+.1*row,15.2-row*1.31,2.02,1.17,1.23))
            parts.append(oval(side*(3.42+.26*row),-3.57+.15*row,15.2-row*1.31,.48,.45,.50))
    front = [(-5.,-2.05,23.65),(-2.95,-3.15,22.1),(.30,-3.44,21.0),(3.1,-2.75,22.21),(4.90,-1.92,23.5)]
    parts.append(track(front,[.84,1.02,1.11,.99,.82]))
    parts += [oval(0,-3.56,16.38,2.30,.94,1.29),oval(.2,-4.41,16.4,.88,.47,.82)]
    for row in range(2):
        for x in (-3.8,-2,-.35,1.3,3):
            parts.append(oval(x,-2.92+abs(x)*.17,18.56+row*1.08,.76,.89,.79))
    return union(parts)


def head():
    parts = [oval(-.93,.75,28.93,4.29,3.78,4.65),oval(-.85,-2.29,28.49,3.46,1.65,2.75),
             oval(-.81,-3.83,28.65,1.02,1.28,1.44),oval(-.84,.83,32.07,4.58,3.96,2.77),
             oval(-.83,-2.41,31.12,4.14,1.69,1.07)]
    for side in (-1,1):
        parts += [oval(-.9+side*3.68,.18,29.27,1.1,1.21,1.37),
                  oval(-.81+side*1.31,-3.16,29.57,1.04,.86,.44),
                  track([(-.81+side*.32,-3.85,27.22),(-.81+side*1.28,-4.06,27.0),
                         (-.81+side*2.56,-3.24,26.35)],[.83,.82,.49])]
    for i in range(7):
        offset = i-3
        low = 21.18+abs(offset)*.40
        parts.append(track([(-.9+offset*.88,-2.53+abs(offset)*.16,27.48),
                            (-.86+offset*.87,-3.48,25.11),(-.42+offset*.81,-2.48,low)], [.81,.89,.52]))
    parts += [oval(-.85,-3.70,31.89,1.28,1.18,1.17),oval(-.85,-4.58,31.88,.76,.65,.76)]
    return union(parts)


def tools_and_arms():
    brace = [(7.95,-3.82,2.73),(7.95,-3.60,17.87),(8.82,-3.40,34.65)]
    stave = track(brace,[1.29,1.29,1.40])
    stave += track([(5.58,-3.49,32.8),(8.53,-3.42,32.86),(11.24,-3.07,32.39)],[.92,1.45,.92])
    stave += track([(7.46,-4.78,3.6),(7.0,-4.23,17.89),(7.79,-4.51,33.43)],[.44,.59,.39])
    parts=[stave]
    for hand,wrist,elbow,shoulder in [((7.8,-4.02,18.88),(7.63,-3.46,19.71),(7.91,-.37,20.34),(4.92,1.27,23.26)),
                                      ((-6.25,-4.46,16.31),(-6.09,-3.90,17.59),(-7.12,-.48,19.98),(-5.59,1.42,23.37))]:
        parts.append(track([shoulder,elbow,wrist,hand],[2.5,1.9,1.53,1.55]))
        parts.append(oval(shoulder[0],shoulder[1],shoulder[2]+.62,3.11,2.68,1.81))
        parts.append(oval(wrist[0],wrist[1]+.25,wrist[2]+.75,1.83,1.65,1.16))
        for i in range(3):
            parts.append(oval(hand[0]+(i-1)*.67,hand[1]-.78,hand[2]-.2,.51,.87,.76))
    # The short sword stays sheathed at the hip. Its weight supports the broad stance.
    parts.append(track([(-5.1,.26,8.2),(-5.43,-.14,12.5),(-5.02,-.74,17.24)],[.80,1.24,1.14]))
    parts.append(track([(-7.15,-.68,16.11),(-5.34,-.76,16.36),(-3.74,-.65,16.58)],[.54,.8,.58]))
    return union(parts)


def sculpt():
    base = cyl(0,0,0,12.4,.58,13.1,n=64)+cyl(0,0,.50,13.1,1.71,n=64)+cyl(0,0,2.03,13.1,.69,12.35,n=64)
    # Broken slabs on the rock face of the base leave the front label readable.
    rubble = [oval(-8.96,4.4,2.57,2.55,2.1,1.46),oval(-8.7,5.88,2.67,1.7,1.44,1.29),
              oval(7.85,4.4,2.5,2.42,1.78,1.07),oval(9.67,-4.4,2.48,1.64,1.39,.85)]
    # Close the small gap behind the beard where it meets the cuirass.
    collar = oval(-.46,-2.53,25.25,.49,.58,.74)
    return union([base,*rubble,armour(),head(),collar,tools_and_arms(),idrel('H04',.43,-4.3,-10.05,2.65)])


def main():
    from workshop import render_mesh

    destination = OUT/'Пластины K1C'
    directory = destination/'Бром'
    directory.mkdir(exist_ok=True)
    solid = mesh(sculpt())
    if not solid.is_volume or abs(solid.bounds[0,2])>1e-5 or solid.extents[2]>50:
        raise ValueError('Check base and maximum height of H04')
    (directory/'H04-Brom.stl').write_bytes(solid.export(file_type='stl'))
    solid.apply_translation(-solid.bounds[0])
    key = ('hero','H04-Brom',1)
    meshes = {key:solid}
    write_plate(destination/'11-brom.3mf',meshes,arrange([key],meshes,1))
    solid_front = render_mesh(solid,(480,580),'#a69279')
    sheet = Image.new('RGB',(960,580),'#eee8d8')
    sheet.paste(solid_front,(0,0))
    solid.apply_transform(rotation_matrix(pi,(0,0,1)))
    sheet.paste(render_mesh(solid,(480,580),'#a69279'),(480,0))
    sheet.save(directory/'Бром H04.png')
    print('H04',solid.extents.round(2).tolist())


if __name__ == '__main__':
    main()
