"""Orthographic, depth-buffered triangle renderer for CAD previews."""
import numpy as np

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
