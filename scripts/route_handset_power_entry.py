#!/usr/bin/env python3
"""Route the staged power-entry cell. Native DRC remains the acceptance test.

Power paths are explicit. Low-speed control traces use a conservative lattice
search; this is not a router for RF, USB differential pairs or switching nodes.
"""
from collections import defaultdict
import heapq
import json
import math
import shutil
from pathlib import Path
import numpy as np
import pcbnew as p

OUT=Path('/tmp/handset-power-entry')
p.SwigPyIterator.next=p.SwigPyIterator.__next__
b=p.LoadBoard(str(OUT/'power-entry-unrouted.kicad_pcb'))
fps={f.GetReference():f for f in b.GetFootprints()}
P=lambda xy:p.VECTOR2I(*(p.FromMM(v) for v in xy))
xy=lambda pos:(p.ToMM(pos.x),p.ToMM(pos.y))
def tr(net,points,width=.18,layer=p.B_Cu):
    for a,z in zip(points,points[1:]):
        if a==z:continue
        t=p.PCB_TRACK(b);t.SetStart(P(a));t.SetEnd(P(z));t.SetWidth(p.FromMM(width));t.SetLayer(layer);t.SetNet(b.FindNet(net));b.Add(t)
def via(net,x,y,diam=.6,drill=.3):
    if any(t.GetClass()=='PCB_VIA' and t.GetNetname()==net and math.dist(xy(t.GetPosition()),(x,y))<.001 for t in b.GetTracks()):return
    v=p.PCB_VIA(b);v.SetPosition(P((x,y)));v.SetWidth(p.FromMM(diam));v.SetDrill(p.FromMM(drill));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet(net));b.Add(v)

# Local charger power and capacitor connections.
tr('VSYS',[(121.8,62.1),(121.8,62.8),(122.3,63.3)])
tr('VSYS',[(122.3,63.3),(122.5,63.5),(123.05,63.5)],.5)
tr('VBAT',[(121.4,62.1),(121.4,62.8),(120.9,63.3)])
tr('VBAT',[(120.9,63.3),(120.6,63.6),(118.025,63.6),(118.025,64.5)],.4)
tr('USB_PROTECTED',[(121.8,59.9),(122.4,59.9)])
tr('USB_PROTECTED',[(122.4,59.9),(123.35,58.95),(124,58.95)],.4)
tr('USB_PROTECTED',[(122.4,59.9),(123.9,59.9),(124.3,60.3)],.4)
via('USB_PROTECTED',124.3,60.3,.8,.4)
tr('USB_PROTECTED',[(124.3,60.3),(124.3,61.7)],.4,p.F_Cu)
tr('USB_PROTECTED',[(124.3,61.7),(124.1125,61.8875),(124.1125,62.35)],.2,p.F_Cu)

# Battery positive is fused before reaching any VBAT load.
tr('BAT_PACK_POS',[(124,102.5),(122.7,101.2),(118.2125,101.2),(118.2125,107.5)],.6)
tr('VBAT',[(119.7875,107.5),(120.8,107.5)],.6)
via('VBAT',120.8,107.5,.8,.4)
tr('VBAT',[(118.025,64.5),(117.7,64.5),(117,63.8)],.4)
tr('VBAT',[(117.7,64.5),(117,63.8)],.4)
via('VBAT',117,63.8,.8,.4)
tr('VBAT',[(117,63.8),(117,65.8),(130.3,65.8),(130.3,107.5),(120.8,107.5)],1.0,p.In2_Cu)

# Both USB VBUS contact pairs feed one fuse. No direct USB-to-battery path.
for y in (53.6,58.4):
    tr('USB_VBUS',[(126.32,y),(125.4,y)],.3,p.F_Cu);via('USB_VBUS',125.4,y)
tr('USB_VBUS',[(125.4,53.6),(125.4,58.4)],.6)
tr('USB_VBUS',[(125.4,56),(129.2125,56)],.6)
tr('USB_FUSED',[(130.7875,56),(130.7875,57.2),(129.6,58.3875),(129.6,62.4)],.6)
via('USB_FUSED',129.6,62.4,.8,.4)
tr('USB_FUSED',[(129.6,62.4),(125.8875,62.4),(125.8875,62.35)],.4,p.F_Cu)
tr('USB_FUSED',[(128.725,62.4),(128.725,63.5),(127.8,64.425),(127.8,70.4),(130,70.4)],.5,p.F_Cu)

# Thermal-pad vias require filled/capped via-in-pad fabrication and assembly review.
for y in (60.7,61.3):via('GND',121.25,y,.5,.3)
for y in (62.65,63.35):via('GND',125,y,.6,.3)
tr('GND',[(130,67.6),(131.5,67.6)],.8,p.F_Cu)
for y in (67.2,68):
    via('GND',131.5,y,.8,.4);tr('GND',[(131.5,67.6),(131.5,y)],.8,p.F_Cu)
tr('GND',[(126,102.5),(127,101.5)],.6)
via('GND',127,101.5,.8,.4)
tr('GND',[(127,101.5),(129.2,101.5),(129.2,70)],1.2,p.In1_Cu)

# Reserve outward pin escapes before searching other control nets.
for ref, directions in {
    'U21': {'2':(-.6,0),'3':(-.6,0),'4':(.6,0),'5':(.6,0)},
}.items():
    for pad in fps[ref].Pads():
        if pad.GetNumber() in directions:
            x,y=xy(pad.GetPosition()); dx,dy=directions[pad.GetNumber()]
            tr(pad.GetNetname(),[(x,y),(x+dx,y+dy)],.15,pad.GetParentFootprint().GetLayer())

tr('CHG_CE_N',[(120.6,62.1),(120.6,62.75)],.15)
via('CHG_CE_N',120.6,62.75,.5,.3)
tr('GND',[(120.2,62.1),(120.2,62.3),(119.7,62.8),(119.5,62.8)],.15)
via('GND',119.5,62.8,.5,.3)
tr('I2C_SCL',[(121,59.9),(121,58.85)],.15)
via('I2C_SCL',121,58.85,.5,.3)
tr('I2C_SDA',[(120.6,59.9),(120.6,59.35),(120.2,58.95)],.15)
via('I2C_SDA',120.2,58.95,.5,.3)
tr('BAT_TS',[(120.2,59.9),(119.65,59.9),(119.35,59.6)],.15)
via('BAT_TS',119.35,59.6,.5,.3)
# Capacitor returns sized separately from logic/control traces.
tr('GND',[(124,57.05),(124,56.0),(123.6,56.0)],.4)
tr('GND',[(124,56.0),(124.3,56.0)],.4)
via('GND',123.6,56.0);via('GND',124.3,56.0)
tr('GND',[(124.95,63.5),(125,63.35)],.5)
tr('GND',[(119.575,64.5),(119.6,64.5)],.5)
via('GND',119.6,64.5,.8,.4)

# Fan out the X2QFN before other routes can enclose its 0.4 mm pitch pads.
for pin,points in {
    '1':[(120.275,56.8),(119.8,56.8),(119.2,56.2)],
    '2':[(120.275,57.2),(119.5,57.2),(119,57.7)],
    '3':[(120.4,57.825),(120.4,58.0),(119.6,58.0),(119.2,58.4)],
    '4':[(120.8,57.825),(120.8,58.4),(122.8,58.4)],
    '7':[(121.725,57.2),(122.55,57.2)],
    '10':[(121.2,56.175),(121.2,55.3),(121,55.3)],
    '11':[(120.8,56.175),(120.8,55.3),(121,55.3)],
    '12':[(120.4,56.175),(120.4,55.7),(120,55.3)],
}.items():
    pad=next(pad for pad in fps['U22'].Pads() if pad.GetNumber()==pin)
    tr(pad.GetNetname(),points,.15,p.F_Cu)
    if pin!='11':via(pad.GetNetname(),*points[-1],.5,.3)

# Routing window excludes RF areas and the display/trackball opening.
X0,Y0,STEP=99.,50.,.05
NX,NY=661,451
LAYERS=[p.F_Cu,p.B_Cu,p.In2_Cu]
def idx(pos,layer):
    x,y=pos;return (LAYERS.index(layer),round((y-Y0)/STEP),round((x-X0)/STEP))
def loc(node):return (X0+node[2]*STEP,Y0+node[1]*STEP)

def paint(mask,cx,cy,w,h,angle,margin,circle=False):
    radius=math.hypot(w,h)/2+margin
    xa=max(0,int((cx-radius-X0)/STEP)-1);xz=min(NX,int((cx+radius-X0)/STEP)+2)
    ya=max(0,int((cy-radius-Y0)/STEP)-1);yz=min(NY,int((cy+radius-Y0)/STEP)+2)
    if xz<=xa or yz<=ya:return
    xx=X0+np.arange(xa,xz)[None,:]*STEP-cx;yy=Y0+np.arange(ya,yz)[:,None]*STEP-cy
    a=math.radians(angle);u=xx*math.cos(a)-yy*math.sin(a);v=xx*math.sin(a)+yy*math.cos(a)
    if circle:hit=np.hypot(u,v)<=w/2+margin
    else:hit=np.hypot(np.maximum(abs(u)-w/2,0),np.maximum(abs(v)-h/2,0))<=margin
    mask[ya:yz,xa:xz]|=hit
def capsule(mask,a,z,r):
    dx,dy=z[0]-a[0],z[1]-a[1];length=math.hypot(dx,dy)
    paint(mask,(a[0]+z[0])/2,(a[1]+z[1])/2,length,0,-math.degrees(math.atan2(dy,dx)),r)

def obstacles(net,width=.15):
    masks=np.zeros((3,NY,NX),dtype=bool);vm=np.zeros((NY,NX),dtype=bool)
    clearance=.16
    for f in b.GetFootprints():
        for pad in f.Pads():
            x,y=xy(pad.GetPosition());w,h=xy(pad.GetSize());a=pad.GetOrientationDegrees()
            if pad.GetNetname()!=net:
                for i,layer in enumerate(LAYERS):
                    if pad.IsOnLayer(layer):paint(masks[i],x,y,w,h,a,clearance+width/2)
            # Keep new vias out of all paste pads, including same-net pads.
            paint(vm,x,y,w,h,a,.41 if pad.GetNetname()!=net else .30)
            dw,dh=xy(pad.GetDrillSize())
            if dw>0:
                for i in range(3):paint(masks[i],x,y,dw,dh,a,.26+width/2)
                paint(vm,x,y,dw,dh,a,.41)
    for t in b.GetTracks():
        if t.GetNetname()==net:
            if t.GetClass()=='PCB_VIA':
                x,y=xy(t.GetPosition());paint(vm,x,y,0,0,0,.56,True)
            continue
        if t.GetClass()=='PCB_VIA':
            x,y=xy(t.GetPosition());w=p.ToMM(t.GetWidth(p.F_Cu))
            for i in range(3):paint(masks[i],x,y,w,w,0,clearance+width/2,True)
            paint(vm,x,y,w,w,0,.41,True)
        else:
            a,z=xy(t.GetStart()),xy(t.GetEnd());w=p.ToMM(t.GetWidth())
            if t.GetLayer() in LAYERS:capsule(masks[LAYERS.index(t.GetLayer())],a,z,w/2+clearance+width/2)
            capsule(vm,a,z,w/2+.41)
    # Stay inside the board edge and clear of already planned thermal vias.
    for t in b.GetTracks():
        if t.GetClass()=='PCB_VIA' and t.GetNetname()==net:
            _,yy,xx=idx(xy(t.GetPosition()),p.F_Cu)
            if 0<=yy<NY and 0<=xx<NX:vm[yy,xx]=False
    return masks,vm

def search(start,goal,masks,vm):
    if masks[start] or masks[goal]:raise RuntimeError(f'Blocked endpoint {start} -> {goal}')
    def heuristic(n):return max(abs(n[1]-goal[1]),abs(n[2]-goal[2]))+(0 if n[0]==goal[0] else 16)
    heap=[(heuristic(start),0,start)];cost={start:0};prev={}
    directions=[(1,0,1),(0,1,1),(-1,0,1),(0,-1,1),(1,1,1.414),(1,-1,1.414),(-1,1,1.414),(-1,-1,1.414)]
    while heap:
        _,d,node=heapq.heappop(heap)
        if d!=cost.get(node):continue
        if node==goal:
            path=[node]
            while node!=start:node=prev[node];path.append(node)
            return path[::-1]
        layer,y,x=node
        for dy,dx,step in directions:
            yy,xx=y+dy,x+dx
            if not (0<=yy<NY and 0<=xx<NX) or masks[layer,yy,xx]:continue
            if dx and dy and (masks[layer,y,xx] or masks[layer,yy,x]):continue
            nxt=(layer,yy,xx);nd=d+step
            if nd<cost.get(nxt,float('inf')):
                cost[nxt]=nd;prev[nxt]=node;heapq.heappush(heap,(nd+heuristic(nxt),nd,nxt))
        if not vm[y,x]:
            for other in range(3):
                if other==layer or masks[other,y,x]:continue
                nxt=(other,y,x);nd=d+25
                if nd<cost.get(nxt,float('inf')):
                    cost[nxt]=nd;prev[nxt]=node;heapq.heappush(heap,(nd+heuristic(nxt),nd,nxt))
    p.SaveBoard(str(OUT/'routing-failure.kicad_pcb'),b)
    np.savez(OUT/'routing-failure.npz',masks=masks,vm=vm,start=start,goal=goal)
    raise RuntimeError(f'No path {start} -> {goal}')

def emit(net,path,width=.15):
    run=[path[0]];lastdir=None
    for before,after in zip(path,path[1:]):
        if before[0]!=after[0]:
            tr(net,[loc(run[0]),loc(before)],width,LAYERS[before[0]])
            via(net,*loc(before),.5,.3);run=[after];lastdir=None
        else:
            direction=(after[1]-before[1],after[2]-before[2])
            if lastdir and direction!=lastdir:
                tr(net,[loc(run[0]),loc(before)],width,LAYERS[before[0]]);run=[before]
            run.append(after);lastdir=direction
    tr(net,[loc(run[0]),loc(path[-1])],width,LAYERS[path[-1][0]])

metadata=json.loads((OUT/'power-entry-update.json').read_text())
refs=set(metadata['added_refs']+metadata['changed_refs']+['J2','USB1','U17'])
groups=defaultdict(list)
for ref in sorted(refs):
    for pad in fps[ref].Pads():
        net=pad.GetNetname()
        if not pad.GetNumber() or not net or net.startswith('unconnected-(') or net in ('USB_D_P','USB_D_N'):continue
        groups[net].append(pad)

# Add a local ground-reference/thermal plane. Its boundary stops before the
# trackball cutout and stays outside the ESP32 antenna area.
zone=p.ZONE(b);zone.SetLayer(p.In1_Cu);zone.SetNet(b.FindNet('GND'))
zone.SetLocalClearance(p.FromMM(.2));zone.SetPadConnection(p.ZONE_CONNECTION_FULL)
zone.SetMinThickness(p.FromMM(.2));poly=zone.Outline();poly.NewOutline()
for pos in [(100,50),(131.9,50),(131.9,72),(100,72)]:poly.Append(*P(pos))
b.Add(zone)

# Route only the low-speed branches and controls after the explicit power paths.
priority=['USB_VBUS_DET','USB_ILIM','USB_CC_HIGH_N','I2C_SDA','I2C_SCL','CHG_CE_N','USB_AON_3V3','USB_CC1','USB_CC2']
for net,pads in sorted(groups.items(),key=lambda kv: (priority.index(kv[0]) if kv[0] in priority else len(priority),-len(kv[1]))):
    if net=='GND':continue
    b.BuildConnectivity()
    # Copper groups already completed by the hand-routed power paths need no work.
    attempts=0
    while True:
        attempts+=1
        if attempts>len(pads)*2:
            p.SaveBoard(str(OUT/'routing-failure.kicad_pcb'),b)
            raise RuntimeError('No connectivity progress '+net)
        anchor=pads[0];ids={t.m_Uuid.AsString() for t in b.GetConnectivity().GetConnectedItems(anchor)}|{anchor.m_Uuid.AsString()}
        connected=[pad for pad in pads if pad.m_Uuid.AsString() in ids];pending=[pad for pad in pads if pad.m_Uuid.AsString() not in ids]
        if not pending:break
        a,z=min(((a,z) for a in connected for z in pending),key=lambda pair:math.dist(xy(pair[0].GetPosition()),xy(pair[1].GetPosition())))
        if any(not (X0<=xy(pad.GetPosition())[0]<=132 and Y0<=xy(pad.GetPosition())[1]<=72.5) for pad in (a,z)):
            raise RuntimeError('Unrouted power connection outside local window '+net)
        masks,vm=obstacles(net)
        emit(net,search(idx(xy(a.GetPosition()),a.GetParentFootprint().GetLayer()),idx(xy(z.GetPosition()),z.GetParentFootprint().GetLayer()),masks,vm))
        b.BuildConnectivity();print('routed',net,a.GetParentFootprint().GetReference(),z.GetParentFootprint().GetReference(),flush=True)

# Every local surface ground reaches the plane. Existing thermal/PTH returns
# are retained; no new microvias or blind vias are used.
for pad in groups['GND']:
    b.BuildConnectivity();connected=b.GetConnectivity().GetConnectedItems(pad)
    if pad.GetAttribute()==p.PAD_ATTRIB_PTH or any(t.GetClass()=='PCB_VIA' for t in connected):continue
    start=idx(xy(pad.GetPosition()),pad.GetParentFootprint().GetLayer())
    masks,vm=obstacles('GND')
    candidates=[]
    for dy in range(-35,36):
        for dx in range(-35,36):
            layer,y,x=start; yy,xx=y+dy,x+dx
            if 0<=yy<NY and 0<=xx<NX and not vm[yy,xx] and not masks[layer,yy,xx] and Y0+yy*STEP>50.4:
                candidates.append((dx*dx+dy*dy,(layer,yy,xx)))
    for _,goal in sorted(candidates)[:80]:
        try:path=search(start,goal,masks,vm)
        except RuntimeError:continue
        emit('GND',path);via('GND',*loc(goal),.5,.3);break
    else:raise RuntimeError('No ground escape '+pad.GetParentFootprint().GetReference()+'.'+pad.GetNumber())
    print('ground',pad.GetParentFootprint().GetReference(),pad.GetNumber(),flush=True)


p.ZONE_FILLER(b).Fill(b.Zones())
p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
shutil.copy2(Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated/handset.kicad_pro',OUT/'handset.kicad_pro')
metadata['routed_local_refs']=sorted(refs)
(OUT/'power-entry-update.json').write_text(json.dumps(metadata,indent=2)+'\n')
print('Saved candidate; run native DRC and continuity verification.',flush=True)
