"""Visible equipment and anatomy for the named foes and their variants."""

from hero_figures import loop, oval, sweep
from models import cyl, union


# Families using the same animal or humanoid start from a different outline.
FAMILY_BADGES = ('bell claw flame stone beak shell twig pollen twig sail shell foam '
                 'crest mirror staff horn ruff spear shell jaw claw brush furrow straw '
                 'quill coil fork ruff fin shield').split()

VARIANT_BADGES = 'crest split ring ridge shell hooks fan twin hood sail'.split()

BOSS_BADGES = tuple('''bell reeds oar flame quill coil bell cross book crown
flame drill twin stones furnace chain struts bell spoons lantern
scythe thorn antlers fox bark nest bowl leaf graft apples
buoy crown chart sail pearls compass wave muzzle trident light
net reeds mirror oar lily bubbles letters crack reed drowned
shield mast horn horns seal torch flag wall double helm
blade mouth eyelids vial choir crescent shell veil cradle heart
mill coin wheat rake shears well crown swarm scales loaf
book drill fork ribbon twin hand shelves tuning coils arch
ice song hearth crescent brazier moon lantern light mitten throne'''.splitlines())


def ornament(style, point, size=1):
    x, y, z = point

    def relative(path, radii):
        return sweep([(x+a*size, y+b*size, z+c*size) for a,b,c in path], [r*size for r in radii])

    if style in {'bell','bowl','buoy','flame','furnace','lantern','lily','vial','loaf','brazier','light','hearth','apples','cradle','heart','pollen','nest'}:
        shapes = {
            'bell': ((0,0,0, .87), (0,0,2.85,.66), (0,0,2.16,1.11), (0,0,1.57,1.69)),
            'bowl': ((0,0,0, .92), (0,0,1.35,2), (0,0,1.58,2.15)),
            'buoy': ((0,0,0,.92),(0,0,1.46,1.48),(0,0,3.1,.64)),
            'flame': ((0,0,0,1.06),(.1,0,1.65,1.18),(.68,0,3.27,.6)),
            'heart': ((0,0,0,1.1),(-.78,0,1.98,1.19),(.8,0,2.18,1.05)),
            'loaf': ((0,0,0,.96),(-1.12,0,1.7,1.37),(1.12,0,1.7,1.37)),
            'apples': ((0,0,0,.92),(-1.1,0,1.34,1.17),(.95,0,2.05,1.08)),
        }
        default = ((0,0,0,1.02),(0,0,1.76,1.68),(0,0,2.95,.88))
        steps = shapes.get(style, default)
        if style in {'light','lantern','vial','brazier'}:
            steps = (*steps, (1.12,0,3.4,.75))
        return union([relative([(0,0,0),(a,b,c)],[r,r]) if (a,b,c)!=(0,0,0)
                      else oval((x,y,z),(r*size,)*3) for a,b,c,r in steps])

    if style in {'ring','coil','coils','mirror','moon','scales','chain','coin','crescent','compass','mill','well','mouth','jaw','eyelids','pearls','bubbles','shell','net'}:
        loops = {'mirror':(1.55,2.1),'moon':(1.24,1.72),'scales':(2.4,1.19),'coil':(1.57,1.42),
                 'crescent':(2.04,1.1),'jaw':(2.22,1.0),'net':(2.05,1.54),'shell':(1.43,1.83)}
        rx,rz = loops.get(style,(1.55,1.55))
        rim = loop(x,y,z+rz*size,rx*size,rz*size,.62*size)
        if style in {'ring','net','scales','mouth','jaw','chain'}:
            return rim
        return rim + oval((x,y,z+rz*size),(rx*size,.65*size,rz*size))

    if style in {'cross','fork','twig','thorn','antlers','horns','hooks','split','twin','reeds','reed','straw','wheat','graft','struts','torch','ice','hand','shears','shelves','rake','choir','tuning'}:
        wide = 2.7 if style in {'antlers','fork','shears','rake','tuning','struts','hooks','split'} else 1.66
        height = 3.95 if style in {'reeds','ice','straw','wheat','antlers'} else 2.8
        if style == 'twin':
            return union([relative([(0,0,0),(side*1.28,0,2.85)],[1.15,1.19]) for side in (-1,1)])
        parts = [relative([(0,0,0),(0,0,2.27)], [1.04,.85])]
        for side in (-1,1):
            parts.append(relative([(0,0,.51),(side*wide*.62,.04,1.63),(side*wide,.18,height)], [.86,.85,.57]))
            if style == 'hooks':
                parts.append(relative([(side*wide,.18,height),(side*wide*.73,.31,height+.45)],[.57,.54]))
        if style in {'antlers','hand','wheat','thorn','choir','shelves'}:
            parts += [relative([(side*wide*.64,0,1.66),(side*wide*1.2,0,2.66)],[.82,.55]) for side in (-1,1)]
        return union(parts)

    tilt = {'oar':1.78,'spear':-.9,'scythe':-1.45,'horn':1.77,'beak':-1.65,'flag':1.3,'fin':1.8,'quill':1.1,'brush':2.0}.get(style,.55)
    width = {'sail':2.45,'fan':2.24,'shield':2.19,'flag':2.3,'wall':2.3,'arch':2.3,'book':2.14,'chart':2.12,
             'brush':1.27,'blade':.73,'spear':.69,'beak':.85,'ruff':1.95,'crest':.71,'ridge':.8,'hood':2.28}.get(style,1.35)
    height = {'spear':5.0,'mast':5.1,'oar':4.7,'scythe':4.4,'fin':3.8,'throne':3.8,'crown':2.6,'shell':1.64}.get(style,3.35)
    blade = relative([(0,0,0),(tilt*.28,.06,height*.49),(tilt,.14,height)], [1.04,min(width,1.2),.56])
    if style in {'sail','fan','shield','flag','wall','arch','book','chart','fin','throne','ruff','brush','oar','claw','crown','cap','hood','furrow','stones','muzzle','veil','wave'}:
        blade += oval((x+tilt*.43*size,y,z+height*.5*size),(width*size,.84*size,height*.52*size))
    return blade
