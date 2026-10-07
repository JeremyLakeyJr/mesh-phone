"""Conservative local grid search for the USB VBUS bridge on In1.Cu."""
import math,heapq
import numpy as np
import pcbnew as p
X0,Y0,STEP=119.,50.,.05
NX,NY=261,221
xy=lambda v:(p.ToMM(v.x),p.ToMM(v.y))
def paint(mask,cx,cy,w,h,angle,margin):
 r=math.hypot(w,h)/2+margin
 xa=max(0,int((cx-r-X0)/STEP)-1);xz=min(NX,int((cx+r-X0)/STEP)+2)
 ya=max(0,int((cy-r-Y0)/STEP)-1);yz=min(NY,int((cy+r-Y0)/STEP)+2)
 if xz<=xa or yz<=ya:return
 xx=X0+np.arange(xa,xz)[None,:]*STEP-cx;yy=Y0+np.arange(ya,yz)[:,None]*STEP-cy;a=math.radians(angle)
 u=xx*math.cos(a)-yy*math.sin(a);v=xx*math.sin(a)+yy*math.cos(a)
 mask[ya:yz,xa:xz]|=np.hypot(np.maximum(abs(u)-w/2,0),np.maximum(abs(v)-h/2,0))<=margin

def capsule(mask,a,z,r):
 d=(z[0]-a[0],z[1]-a[1]);paint(mask,(a[0]+z[0])/2,(a[1]+z[1])/2,math.hypot(*d),0,-math.degrees(math.atan2(d[1],d[0])),r)

def route(board,start,end):
 mask=np.zeros((NY,NX),dtype=bool)
 for f in board.GetFootprints():
  for pad in f.Pads():
   if pad.GetNetname()=='USB_VBUS':continue
   x,y=xy(pad.GetPosition());w,h=xy(pad.GetSize());angle=pad.GetOrientationDegrees()
   if pad.IsOnLayer(p.In1_Cu):paint(mask,x,y,w,h,angle,.46)
   w,h=xy(pad.GetDrillSize())
   if w:paint(mask,x,y,w,h,angle,.56)
 for t in board.GetTracks():
  if t.GetNetname()=='USB_VBUS':continue
  if isinstance(t,p.PCB_VIA):
   x,y=xy(t.GetPosition());paint(mask,x,y,0,0,0,p.ToMM(t.GetWidth(p.In1_Cu))/2+.46)
  elif t.GetLayer()==p.In1_Cu:capsule(mask,xy(t.GetStart()),xy(t.GetEnd()),p.ToMM(t.GetWidth())/2+.46)
  elif t.GetLayer()==p.F_Cu and t.GetNetname().startswith('USB_D_'):
   # Keep VBUS and its ground-plane clearance away from the front USB fanout.
   capsule(mask,xy(t.GetStart()),xy(t.GetEnd()),p.ToMM(t.GetWidth())/2+.76)
 idx=lambda q:(round((q[1]-Y0)/STEP),round((q[0]-X0)/STEP))
 loc=lambda q:(round(X0+q[1]*STEP,6),round(Y0+q[0]*STEP,6))
 a,z=idx(start),idx(end);assert not mask[a] and not mask[z],('Power endpoint obstructed',a,z)
 costs={a:0};prev={};heap=[(0,a)]
 while heap:
  _,q=heapq.heappop(heap)
  if q==z:break
  for dy,dx in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
   n=(q[0]+dy,q[1]+dx)
   if not (0<=n[0]<NY and 0<=n[1]<NX) or mask[n]:continue
   if dx and dy and (mask[q[0],n[1]] or mask[n[0],q[1]]):continue
   d=costs[q]+math.hypot(dx,dy)
   if d<costs.get(n,1e20):costs[n]=d;prev[n]=q;heapq.heappush(heap,(d+math.dist(n,z),n))
 else:raise RuntimeError('No local VBUS route')
 points=[z]
 while points[-1]!=a:points.append(prev[points[-1]])
 points.reverse()
 # Collapse grid stair-steps only when the whole chord clears the same mask.
 # Native DRC remains the final geometric check.
 def visible(a,z):
  count=max(1,math.ceil(math.dist(a,z)*4))
  return all(not mask[round(a[0]+(z[0]-a[0])*i/count),round(a[1]+(z[1]-a[1])*i/count)] for i in range(count+1))
 simple=[points[0]];i=0
 while i<len(points)-1:
  j=next(j for j in range(len(points)-1,i,-1) if visible(points[i],points[j]))
  simple.append(points[j]);i=j
 return [loc(q) for q in simple]
