#!/usr/bin/env python3
"""Verify handset meshes and render the actual CAD with illustrative UI props."""
from pathlib import Path
from collections import Counter, defaultdict
import os, tempfile
os.environ.setdefault('MPLCONFIGDIR', tempfile.mkdtemp(prefix='mesh-phone-mpl-'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from mesh_render import rasterize
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'mechanical/handset/exports'
def load(name, check=True):
    pts=[tuple(map(float,l.split()[1:])) for l in (out/f'{name}.stl').read_text().splitlines() if l.strip().startswith('vertex ')]
    tri=np.array(pts).reshape(-1,3,3)
    if check:
        edges=Counter(); graph=defaultdict(set)
        for t in tri:
            for a,b in zip(t,np.roll(t,-1,axis=0)):
                a,b=tuple(a),tuple(b); edges[tuple(sorted((a,b)))]+=1
                graph[a].add(b);graph[b].add(a)
        assert set(edges.values())=={2},name+' has non-manifold edges'
        seen=set();todo=[next(iter(graph))]
        while todo:
            v=todo.pop()
            if v not in seen: seen.add(v);todo.extend(graph[v]-seen)
        assert len(seen)==len(graph),name+' has disconnected solids'
        print(name+': connected, closed mesh')
    return tri
meshes={n:load(n) for n in ['rear','front','keycap','port_cover','module_pod']}
props={n:load('visual_'+n,False) for n in ['display','ball','ring','screws','legends','ui']}
def render(pod=False,rear=False):
    triangles=[];colors=[]
    def add(t,color):
        normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-12)
        light=0.64+0.36*np.abs(normal@np.array([0.3,-0.4,0.866]))
        triangles.extend(t);colors.extend(np.array(to_rgb(color))[None,:]*light[:,None])
    add(meshes['rear'],'#343b41')
    front=meshes['front'].copy();front[:,:,2]=26-front[:,:,2];add(front,'#4c565d')
    for y in [-11,-26,-41,-56]:
        for x in [-22.5,-7.5,7.5,22.5]:
            key=meshes['keycap'].copy();key[:,:,2]=25.9-key[:,:,2];key[:,:,0]+=x;key[:,:,1]+=y;add(key,'#151b20')
    module=meshes['module_pod' if pod else 'port_cover'].copy();module[:,:,1]+=40
    if pod:module[:,:,2]+=1.2-18
    add(module,'#414b52')
    for n,c in [('display','#08272f'),('ball','#a6b6bc'),('ring','#87939a'),('screws','#abb5b9'),('legends','#dce2df'),('ui','#4cd9be')]:add(props[n],c)
    return rasterize(triangles,colors,rear_view=rear)
fig,axs=plt.subplots(1,3,figsize=(15,10),facecolor='#f2f3f2')
for ax,title,view in zip(axs,['HANDSET / 74 × 154 × 26 mm','FLUSH REAR / 3000 mAh INSIDE','LTE POD / EXPANSION STILL ACCESSIBLE'],[render(),render(rear=True),render(pod=True,rear=True)]):
    ax.imshow(view);ax.set_title(title,fontsize=10,pad=14);ax.axis('off')
fig.suptitle('MESH-PHONE  /  HANDSET CONCEPT',fontsize=23,y=.97)
fig.text(.5,.045,'NEW PCB + SMALLER TOUCH DISPLAY REQUIRED  •  UI AND HARDWARE PROPS ARE ILLUSTRATIVE',ha='center',fontsize=10,color='#555b60')
fig.tight_layout(rect=[0,.06,1,.93]);fig.savefig(out/'design-preview.png',dpi=150)
plt.imsave(out/'front-preview.png',render())
