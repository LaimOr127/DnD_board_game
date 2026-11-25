"""Fine exterior relief with smooth recesses and joining faces."""

import numpy as np
from manifold3d import Manifold, Mesh


def relief_panel(width, height, seed, keepouts=()):
    """A shallow solid with its flat back below y=0 and its relief facing +Y."""
    xs = np.linspace(0,width,int(width/.54)+2)
    zs = np.linspace(0,height,int(height/.71)+2)
    x,z = np.meshgrid(xs,zs)
    y = np.random.default_rng(seed).uniform(.015,.24,x.shape)
    y[[0,-1],:] = 0
    y[:,[0,-1]] = 0
    for left,bottom,right,top in keepouts:
        y[(x>=left)&(x<=right)&(z>=bottom)&(z<=top)] = 0
    back = [(0,-.35,0),(0,-.35,height),(width,-.35,height),(width,-.35,0)]
    verts = np.vstack((back,np.stack((x,y,z),axis=-1).reshape(-1,3))).astype(np.float32)
    grid = np.arange(4,4+x.size).reshape(x.shape)
    a,b,c,d = grid[:-1,:-1],grid[:-1,1:],grid[1:,:-1],grid[1:,1:]
    skin = np.stack((np.stack((a,c,b),axis=-1),np.stack((b,c,d),axis=-1)),axis=-2).reshape(-1,3)
    faces = [(0,2,1),(0,3,2)]
    for i,edge in enumerate((grid[:,0],grid[-1,:],grid[::-1,-1],grid[0,::-1])):
        faces.append((i,(i+1)%4,edge[-1]))
        faces.extend((i,high,low) for low,high in zip(edge[:-1],edge[1:]))
    solid = Manifold(Mesh(verts,np.vstack((skin,faces)).astype(np.uint32)))
    assert solid.num_tri() > 0 and solid.volume() > 0
    return solid


def exterior_edges(width, depth, base, top, sides, seed, inset=2.6, rear_hinge=None):
    """Front, back and selected exposed end panels of one case section."""
    z = base+inset
    w,d,h = width-2*inset,depth-2*inset,top-base-2*inset
    keepout = ()
    if rear_hinge:
        left,right,lowest = rear_hinge
        keepout = ((width-inset-right,lowest-z,width-inset-left,h),)
    parts = [relief_panel(w,h,seed).translate((inset,depth,z)),
             relief_panel(w,h,seed+1,keepout).rotate((0,0,180)).translate((width-inset,0,z))]
    if 'left' in sides:
        parts.append(relief_panel(d,h,seed+2).rotate((0,0,90)).translate((0,inset,z)))
    if 'right' in sides:
        parts.append(relief_panel(d,h,seed+3).rotate((0,0,-90)).translate((width,depth-inset,z)))
    return parts


def lid_face(width, depth, top, seed):
    inset = 2.6
    # Keep the title field and the two elastic slots smooth.
    keepouts = ((width/2-69-inset,depth-123-inset,width/2+69-inset,depth-87-inset),
                *((width/2-12-inset,depth-y-4-inset,width/2+12-inset,depth-y+4-inset)
                  for y in (7,depth-7)))
    return relief_panel(width-2*inset,depth-2*inset,seed,keepouts).rotate((90,0,0)).translate(
        (inset,depth-inset,top))
