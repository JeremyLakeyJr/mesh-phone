#!/usr/bin/env python3
"""Validate ASCII STL topology and render a headless preview of the actual meshes."""
from pathlib import Path
import os
import tempfile
os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="mesh-phone-mpl-"))
from collections import Counter, defaultdict
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
out = Path(__file__).resolve().parents[1] / 'mechanical/enclosure/exports'
meshes = {}
fig = plt.figure(figsize=(14, 12))
for index, name in enumerate(('rear', 'front', 'port_cover', 'module_pod'), 1):
    vertices = [tuple(map(float, line.split()[1:])) for line in
                (out / f'{name}.stl').read_text().splitlines()
                if line.strip().startswith('vertex ')]
    triangles = np.array(vertices).reshape(-1, 3, 3)
    meshes[name] = triangles
    edges = Counter()
    graph = defaultdict(set)
    for tri in triangles:
        for a, b in zip(tri, np.roll(tri, -1, axis=0)):
            a, b = tuple(a), tuple(b)
            edges[tuple(sorted((a, b)))] += 1
            graph[a].add(b); graph[b].add(a)
    assert set(edges.values()) == {2}, f'{name}: non-manifold edge'
    seen = set(); todo = [next(iter(graph))]
    while todo:
        v = todo.pop()
        if v not in seen:
            seen.add(v); todo.extend(graph[v] - seen)
    assert len(seen) == len(graph), f'{name}: disconnected part'
    print(f'{name}: connected, closed mesh; {len(triangles)} triangles')
    ax = fig.add_subplot(2, 2, index, projection='3d')
    ax.add_collection3d(Poly3DCollection(triangles, facecolor='#86a7b7',
                                        edgecolor='none', linewidth=0))
    ax.set(xlim=(-55,55), ylim=(-85,85), zlim=(0,45), title=name.replace('_', ' ').title())
    ax.set_box_aspect((110,170,45)); ax.view_init(elev=55, azim=-65)
    ax.set_axis_off()
fig.suptitle('MESH-PHONE — pocket enclosure / 3000 mAh / removable module', fontsize=20)
fig.tight_layout()
fig.savefig(out / 'preview.png', dpi=120)

def rasterize(triangles, colors, rear_view=False):
    # Orthographic software depth buffer avoids mplot3d triangle sorting artifacts.
    camera = np.array([0.32, -0.46, -0.83 if rear_view else 0.83])
    camera /= np.linalg.norm(camera)
    right = np.cross([0, 1, 0], camera); right /= np.linalg.norm(right)
    up = np.cross(camera, right)
    tri = np.asarray(triangles) @ np.array([right, up, camera]).T
    low = tri[:,:,:2].min(axis=(0,1)); high = tri[:,:,:2].max(axis=(0,1))
    scale = min(540/(high[0]-low[0]), 840/(high[1]-low[1]))
    tri[:,:,0] = (tri[:,:,0]-(high[0]+low[0])/2)*scale+300
    tri[:,:,1] = 450-(tri[:,:,1]-(high[1]+low[1])/2)*scale
    pixels = np.ones((900,600,3)); depth = np.full((900,600), -np.inf)
    for t, color in zip(tri, colors):
        x0=max(0,int(np.floor(t[:,0].min()))); x1=min(599,int(np.ceil(t[:,0].max())))
        y0=max(0,int(np.floor(t[:,1].min()))); y1=min(899,int(np.ceil(t[:,1].max())))
        if x1<x0 or y1<y0: continue
        xx,yy=np.meshgrid(np.arange(x0,x1+1)+0.5,np.arange(y0,y1+1)+0.5)
        a,b,c=t
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-9: continue
        w0=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
        w1=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
        w2=1-w0-w1; z=w0*a[2]+w1*b[2]+w2*c[2]
        region=depth[y0:y1+1,x0:x1+1]
        mask=(w0>=-1e-7)&(w1>=-1e-7)&(w2>=-1e-7)&(z>region)
        region[mask]=z[mask]; pixels[y0:y1+1,x0:x1+1][mask]=color
    return pixels

# Assembly transforms match enclosure.scad; derive height from exported surfaces.
height = float(meshes['rear'][:,:,2].max()) + 2.4
fig = plt.figure(figsize=(16, 10))
for index, (title, pod, elevation) in enumerate([
    ('Front • 93 × 160 × 38.8 mm', False, 65),
    ('Rear • covered module port', False, -65),
    ('Rear • removable module pod', True, -65)], 1):
    ax = fig.add_subplot(1, 3, index)
    parts = [('rear', '#344c58'), ('front', '#78999d'),
             ('module_pod' if pod else 'port_cover', '#da9b48')]
    all_triangles, all_colors = [], []
    for name, color in parts:
        tri = meshes[name].copy()
        if name == 'front':
            tri[:,:,2] = height - tri[:,:,2]
        elif name in ('port_cover', 'module_pod'):
            tri[:,:,0] -= 3
            tri[:,:,1] -= 10
            if pod: tri[:,:,2] += 1.2 - 18
        from matplotlib.colors import to_rgb
        normals = np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0])
        normals /= np.maximum(np.linalg.norm(normals, axis=1)[:,None], 1e-12)
        brightness = 0.7 + 0.3*np.abs(normals @ np.array([0.3,-0.4,0.866]))
        all_triangles.extend(tri)
        all_colors.extend(np.array(to_rgb(color))[None,:]*brightness[:,None])
    ax.imshow(rasterize(all_triangles, all_colors, rear_view=elevation<0))
    ax.set_title(title)
    ax.set_axis_off()
fig.suptitle('MESH-PHONE • MakerFocus 3000 mAh • pocket enclosure', fontsize=20)
fig.tight_layout()
fig.savefig(out / 'assembled.png', dpi=140)
