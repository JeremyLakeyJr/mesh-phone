#!/usr/bin/env python3
"""Stage display-domain routing; retain existing placement and copper."""
import csv,hashlib,heapq,json,math,shutil,sys
from pathlib import Path
import numpy as np
import pcbnew as p
from sync_handset_schematic_rebuild import geometry
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hardware/handset-rev-a/generated'
OUT=Path('/tmp/handset-display-routing')
assert not (SOURCE/'display-routing.json').exists(),'Already installed; preserve subsequent edits'
OUT.mkdir(exist_ok=True)
source_hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in SOURCE.iterdir() if f.is_file()}
for f in SOURCE.iterdir():
 if f.is_file() and f.suffix not in ('.lck','.prl'):shutil.copy2(f,OUT/f.name)
shutil.copytree(SOURCE/'Handset.pretty',OUT/'Handset.pretty',dirs_exist_ok=True)
p.SwigPyIterator.next=p.SwigPyIterator.__next__
b=p.LoadBoard(str(SOURCE/'handset.kicad_pcb'));original=geometry(b)
if '--resume' in sys.argv:b=p.LoadBoard(str(OUT/'checkpoint.kicad_pcb'))
fps={f.GetReference():f for f in b.GetFootprints()}
P=lambda xy:p.VECTOR2I(*(p.FromMM(v) for v in xy))
xy=lambda pos:(p.ToMM(pos.x),p.ToMM(pos.y))
X0,Y0,STEP=68.,30.,.05
NX,NY=1281,2801
LAYERS=[p.F_Cu,p.B_Cu,p.In2_Cu]
route_evidence=json.loads((OUT/'checkpoint-routes.json').read_text()) if '--resume' in sys.argv else []
def tr(net, points, width=0.18, layer=p.B_Cu):
    for a, z in zip(points, points[1:]):
        if a == z:
            continue
        t = p.PCB_TRACK(b)
        t.SetStart(P(a))
        t.SetEnd(P(z))
        t.SetWidth(p.FromMM(width))
        t.SetLayer(layer)
        t.SetNet(b.FindNet(net))
        b.Add(t)

def via(net, x, y, diam=0.6, drill=0.3):
    if any((t.GetClass() == 'PCB_VIA' and t.GetNetname() == net and (math.dist(xy(t.GetPosition()), (x, y)) < STEP) for t in b.GetTracks())):
        return
    v = p.PCB_VIA(b)
    v.SetPosition(P((x, y)))
    v.SetWidth(p.FromMM(diam))
    v.SetDrill(p.FromMM(drill))
    v.SetViaType(p.VIATYPE_THROUGH)
    v.SetLayerPair(p.F_Cu, p.B_Cu)
    v.SetNet(b.FindNet(net))
    b.Add(v)

def idx(pos, layer):
    x, y = pos
    return (LAYERS.index(layer), round((y - Y0) / STEP), round((x - X0) / STEP))

def loc(node):
    return (X0 + node[2] * STEP, Y0 + node[1] * STEP)

def paint(mask, cx, cy, w, h, angle, margin, circle=False):
    radius = math.hypot(w, h) / 2 + margin
    xa = max(0, int((cx - radius - X0) / STEP) - 1)
    xz = min(NX, int((cx + radius - X0) / STEP) + 2)
    ya = max(0, int((cy - radius - Y0) / STEP) - 1)
    yz = min(NY, int((cy + radius - Y0) / STEP) + 2)
    if xz <= xa or yz <= ya:
        return
    xx = X0 + np.arange(xa, xz)[None, :] * STEP - cx
    yy = Y0 + np.arange(ya, yz)[:, None] * STEP - cy
    a = math.radians(angle)
    u = xx * math.cos(a) - yy * math.sin(a)
    v = xx * math.sin(a) + yy * math.cos(a)
    if circle:
        hit = np.hypot(u, v) <= w / 2 + margin
    else:
        hit = np.hypot(np.maximum(abs(u) - w / 2, 0), np.maximum(abs(v) - h / 2, 0)) <= margin
    mask[ya:yz, xa:xz] |= hit

def capsule(mask, a, z, r):
    dx, dy = (z[0] - a[0], z[1] - a[1])
    length = math.hypot(dx, dy)
    paint(mask, (a[0] + z[0]) / 2, (a[1] + z[1]) / 2, length, 0, -math.degrees(math.atan2(dy, dx)), r)

def obstacles(net, width=0.15):
    masks = np.zeros((3, NY, NX), dtype=bool)
    vm = np.zeros((NY, NX), dtype=bool)
    clearance = 0.16
    for f in b.GetFootprints():
        for pad in f.Pads():
            x, y = xy(pad.GetPosition())
            w, h = xy(pad.GetSize())
            a = pad.GetOrientationDegrees()
            if pad.GetNetname() != net:
                for i, layer in enumerate(LAYERS):
                    if pad.IsOnLayer(layer):
                        paint(masks[i], x, y, w, h, a, clearance + width / 2)
            paint(vm, x, y, w, h, a, 0.41 if pad.GetNetname() != net else 0.3)
            dw, dh = xy(pad.GetDrillSize())
            if dw > 0:
                for i in range(3):
                    paint(masks[i], x, y, dw, dh, a, 0.26 + width / 2)
                paint(vm, x, y, dw, dh, a, 0.41)
    for t in b.GetTracks():
        if t.GetNetname() == net:
            if t.GetClass() == 'PCB_VIA':
                x, y = xy(t.GetPosition())
                paint(vm, x, y, 0, 0, 0, 0.56, True)
            continue
        if t.GetClass() == 'PCB_VIA':
            x, y = xy(t.GetPosition())
            w = p.ToMM(t.GetWidth(p.F_Cu))
            for i in range(3):
                paint(masks[i], x, y, w, w, 0, clearance + width / 2, True)
            paint(vm, x, y, w, w, 0, 0.41, True)
        else:
            a, z = (xy(t.GetStart()), xy(t.GetEnd()))
            w = p.ToMM(t.GetWidth())
            if t.GetLayer() in LAYERS:
                capsule(masks[LAYERS.index(t.GetLayer())], a, z, w / 2 + clearance + width / 2)
            capsule(vm, a, z, w / 2 + 0.41)
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA' and t.GetNetname() == net:
            _, yy, xx = idx(xy(t.GetPosition()), p.F_Cu)
            if 0 <= yy < NY and 0 <= xx < NX:
                vm[yy, xx] = False
    xx = X0 + np.arange(NX)[None, :] * STEP
    yy = Y0 + np.arange(NY)[:, None] * STEP
    opening = (xx < 114.6) & (xx > 85.4) & (yy > 78.9) & (yy < 105.1)
    antenna=(xx<75.85)&(yy<82.6)
    if net in ('LCD_DC','LCD_RESET','TOUCH_RESET','TOUCH_IRQ'):
        reserved=(xx>84)&(xx<116)&(yy>59)&(yy<77)
        masks[0]|=reserved;vm|=reserved
    # Physical microSD socket keepouts, expanded for trace width/clearance.
    for xa,ya,xz,yz in [(119.0,95.2,123.7,104.2),(117.0,98.2,119.4,101.2)]:
        socket=(xx>=xa-width/2)&(xx<=xz+width/2)&(yy>=ya-width/2)&(yy<=yz+width/2)
        masks[0]|=socket;vm|=socket
    masks |= (opening|antenna)[None, :, :]
    vm |= opening|antenna
    return (masks, vm)

def search(start, goal, masks, vm):
    if masks[start] or masks[goal]:
        raise RuntimeError(f'Blocked endpoint {start} -> {goal}')

    def heuristic(n):
        dy, dx = (abs(n[1] - goal[1]), abs(n[2] - goal[2]))
        return max(dx, dy) + 0.414 * min(dx, dy) + (0 if n[0] == goal[0] else 16)
    heap = [(heuristic(start), 0, start)]
    cost = {start: 0}
    prev = {}
    directions = [(1, 0, 1), (0, 1, 1), (-1, 0, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    while heap:
        if len(cost)>400000:
            p.SaveBoard(str(OUT/'routing-failure.kicad_pcb'),b)
            raise RuntimeError(f'Search budget: {start} -> {goal}')
        _, d, node = heapq.heappop(heap)
        if d != cost.get(node):
            continue
        if node == goal:
            path = [node]
            while node != start:
                node = prev[node]
                path.append(node)
            return path[::-1]
        layer, y, x = node
        for dy, dx, step in directions:
            yy, xx = (y + dy, x + dx)
            if not (0 <= yy < NY and 0 <= xx < NX) or masks[layer, yy, xx]:
                continue
            if dx and dy and (masks[layer, y, xx] or masks[layer, yy, x]):
                continue
            nxt = (layer, yy, xx)
            nd = d + step
            if nd < cost.get(nxt, float('inf')):
                cost[nxt] = nd
                prev[nxt] = node
                heapq.heappush(heap, (nd + 1.5*heuristic(nxt), nd, nxt))
        if not vm[y, x]:
            for other in range(3):
                if other == layer or masks[other, y, x]:
                    continue
                nxt = (other, y, x)
                nd = d + 25
                if nd < cost.get(nxt, float('inf')):
                    cost[nxt] = nd
                    prev[nxt] = node
                    heapq.heappush(heap, (nd + 1.5*heuristic(nxt), nd, nxt))
    p.SaveBoard(str(OUT / 'routing-failure.kicad_pcb'), b)
    np.savez(OUT / 'routing-failure.npz', masks=masks, vm=vm, start=start, goal=goal)
    raise RuntimeError(f'No path {start} -> {goal}')

def emit(net, path, width=0.15):
    run = [path[0]]
    lastdir = None
    for before, after in zip(path, path[1:]):
        if before[0] != after[0]:
            tr(net, [loc(run[0]), loc(before)], width, LAYERS[before[0]])
            via(net, *loc(before), 0.5, 0.3)
            run = [after]
            lastdir = None
        else:
            direction = (after[1] - before[1], after[2] - before[2])
            if lastdir and direction != lastdir:
                tr(net, [loc(run[0]), loc(before)], width, LAYERS[before[0]])
                run = [before]
            run.append(after)
            lastdir = direction
    tr(net, [loc(run[0]), loc(path[-1])], width, LAYERS[path[-1][0]])

def pad(key):
    ref, pin = key.split('.')
    return next((q for q in fps[ref].Pads() if q.GetNumber() == pin))

def route_points(net, startpos, startlayer, endpos, endlayer, width=0.15):
    masks, vm = obstacles(net, width)
    start, goal = (idx(startpos, startlayer), idx(endpos, endlayer))
    np.savez(OUT/'route-mask.npz',masks=masks,vm=vm,start=start,goal=goal)
    path = search(goal, start, masks, vm)[::-1]
    tr(net, [startpos, loc(start)], width, startlayer)
    emit(net, path, width)
    tr(net, [loc(goal), endpos], width, endlayer)
    return dict(trace_length_mm=round(sum(math.dist(loc(a),loc(z)) for a,z in zip(path,path[1:]) if a[0]==z[0])+math.dist(startpos,loc(start))+math.dist(endpos,loc(goal)),3),layer_transitions=sum(a[0]!=z[0] for a,z in zip(path,path[1:])))

def connect(a, z, width=0.15):
    if {a,z}=={'U31.7','U30.8'}:a,z='C89.1','C87.1'
    if {a,z}=={'C26.1','J26.1'}:a,z,width='C26.1','C84.1',.4
    pa, pz = (pad(a), pad(z))
    assert pa.GetNetname() == pz.GetNetname(), (a, z)
    b.BuildConnectivity()
    if pz.m_Uuid.AsString() in {q.m_Uuid.AsString() for q in b.GetConnectivity().GetConnectedItems(pa)}:return
    endpoints=[]
    for key,q in [(a,pa),(z,pz)]:
        if key.startswith('J26.') and q.GetNetname().startswith('PANEL_'):
            found=next((r for r in route_evidence if r['start']==key and r.get('end')=='fanout via'),None)
            if found is None:
                pin_escape(key);found=route_evidence[-1]
            endpoints.append((tuple(found['via_xy_mm']),p.B_Cu))
        else:endpoints.append((xy(q.GetPosition()),q.GetParentFootprint().GetLayer()))
    metrics=route_points(pa.GetNetname(),*endpoints[0],*endpoints[1],width)
    route_evidence.append(dict(start=a,end=z,net=pa.GetNetname(),width_mm=width,**metrics))
    print('Connected', a, z, flush=True)
    p.SaveBoard(str(OUT/'checkpoint.kicad_pcb'),b)
    (OUT/'checkpoint-routes.json').write_text(json.dumps(route_evidence,indent=2)+'\n')


# Explicit endpoints keep unrelated branches of shared buses outside this pass.
groups={
 'LCD_3V0':'U28.5 C85.1 U29.20 C86.1 U31.3 U31.6 C88.1 R81.1 C47.1 C48.1 J26.7 J26.8 J26.9 J26.35 J26.40 J26.41 J26.42',
 '+3V3':'U1.2 C89.1 U31.7 C87.1 U30.8 R58.1',
 '+5V_RF':'C26.1 U28.1 C84.1 J26.1 C49.1',
 'SYS_EN':'Q4.1 U28.3',
 'SPI_SCK':'U1.20 U29.2', 'SPI_MOSI':'U1.21 U29.4', 'SPI_MISO':'U1.22 U30.6',
 'LCD_CS':'U1.19 U29.6 U30.1 R58.2',
 'LCD_DC':'U2.1 U29.8', 'LCD_RESET':'U2.2 U29.11', 'TOUCH_RESET':'U2.3 U29.13', 'TOUCH_IRQ':'U2.15 U30.3',
 'I2C_SDA':'U1.18 U31.1','I2C_SCL':'U1.17 U31.8',
 'PANEL_SPI_SCK':'U29.18 J26.37','PANEL_SPI_MOSI':'U29.16 J26.34','PANEL_SPI_MISO':'U30.2 R80.1 J26.33',
 'PANEL_LCD_CS':'U29.14 J26.38','PANEL_LCD_DC':'U29.12 J26.36','PANEL_LCD_RESET':'U29.9 J26.10',
 'PANEL_TOUCH_RESET':'U29.7 J26.47','PANEL_TOUCH_IRQ':'U30.5 R81.2 J26.46',
 'PANEL_I2C_SDA':'U31.4 J26.45','PANEL_I2C_SCL':'U31.5 J26.44',
}
def pin_escape(key):
    q=pad(key);net=q.GetNetname()
    pos=xy(q.GetPosition());start=idx(pos,p.F_Cu)
    masks,vm=obstacles(net,.15)
    if key.startswith('J26.') and net!='GND':
        for other in fps['J26'].Pads():
            if other.GetNetname() in (net,'GND') or other.GetNetname().startswith('unconnected-(') or not other.GetNumber():continue
            xx,yy=xy(other.GetPosition())
            capsule(masks[0],(xx,yy),(xx,70.0),.235)
            capsule(vm,(xx,yy),(xx,70.0),.485)
    assert not masks[start],('Ground pad blocked',key)
    queue=[(0,start)];cost={start:0};prev={};goal=None
    while queue:
        dist,node=heapq.heappop(queue)
        if dist!=cost[node]:continue
        layer,y,x=node
        if not vm[y,x]:goal=node;break
        for dy,dx,weight in [(1,0,1),(-1,0,1),(0,1,1),(0,-1,1),(1,1,1.414),(1,-1,1.414),(-1,1,1.414),(-1,-1,1.414)]:
            yy,xx=y+dy,x+dx;nxt=(layer,yy,xx)
            if not (0<=yy<NY and 0<=xx<NX) or masks[nxt] or math.dist(loc(start),loc(nxt))>5:continue
            if dx and dy and (masks[layer,y,xx] or masks[layer,yy,x]):continue
            nd=dist+weight
            if nd<cost.get(nxt,float('inf')):cost[nxt]=nd;prev[nxt]=node;heapq.heappush(queue,(nd,nxt))
    assert goal is not None,('No local ground via site',key)
    path=[goal]
    while path[-1]!=start:path.append(prev[path[-1]])
    path.reverse();tr(net,[pos,loc(start)],.15,p.F_Cu);emit(net,path,.15);via(net,*loc(goal),.5,.3)
    route_evidence.append(dict(start=key,end='fanout via',net=net,width_mm=.15,trace_length_mm=round(cost[goal]*STEP+math.dist(pos,loc(start)),3),via_xy_mm=loc(goal)))
    print('Pin escape',key,flush=True)


# Pre-plan dense pin escapes so later branches cannot trap neighboring pins.
if '--resume' not in sys.argv:
 for pin in range(1,21):
  q=pad('U29.'+str(pin));net=q.GetNetname()
  if net.startswith('unconnected-('):continue
  x,y=xy(q.GetPosition());vx=(89.4 if pin%2 else 90.1) if pin<=10 else (92.6 if pin%2 else 91.9)
  tr(net,[(x,y),(vx,y)],.15,p.F_Cu);via(net,vx,y,.5,.3)
 for pin in [45,47,46,44,33,34,35,36,37,38,40,41,42,1,7,8,9,10]:
  pin_escape('J26.'+str(pin))
 p.SaveBoard(str(OUT/'checkpoint.kicad_pcb'),b)
 (OUT/'checkpoint-routes.json').write_text(json.dumps(route_evidence,indent=2)+'\n')
if '--fanout-only' in sys.argv:
 p.ZONE_FILLER(b).Fill(b.Zones())
 p.SaveBoard(str(OUT/'handset.kicad_pcb'),b);shutil.copy2(SOURCE/'handset.kicad_pro',OUT/'handset.kicad_pro');sys.exit(0)
# Extend the reference plane under the left-side display return buffers.
zone=p.ZONE(b);zone.SetLayer(p.In1_Cu);zone.SetNet(b.FindNet('GND'));zone.SetLocalClearance(p.FromMM(.2));zone.SetThermalReliefGap(p.FromMM(.2));zone.SetThermalReliefSpokeWidth(p.FromMM(.25));zone.SetMinThickness(p.FromMM(.2));zone.SetZoneName('Display interface ground extension')
poly=zone.Outline();poly.NewOutline()
for x,y in [(75.9,72),(85.3,72),(85.3,82.6),(75.9,82.6)]:poly.Append(int(p.FromMM(x)),int(p.FromMM(y)))
if not any(z.GetZoneName()=='Display interface ground extension' for z in b.Zones()):b.Add(zone)
# Connector return pins require copper too; adjacent ground pins share short buses.
for pins in [range(11,33),range(48,51)]:
 for aa,zz in zip(list(pins),list(pins)[1:]):
  b.BuildConnectivity()
  qa,qz=pad('J26.'+str(aa)),pad('J26.'+str(zz))
  if qz.m_Uuid.AsString() not in {v.m_Uuid.AsString() for v in b.GetConnectivity().GetConnectedItems(qa)}:tr('GND',[xy(qa.GetPosition()),xy(qz.GetPosition())],.2,p.F_Cu)
for key in ['J26.6','J26.11','J26.32','J26.43','J26.48']:
 if not any(r['start']==key and r.get('end')=='fanout via' for r in route_evidence):pin_escape(key)
if not any(r['start']=='U31.2' and r.get('end')=='fanout via' for r in route_evidence):pin_escape('U31.2')

# Route short decoupling connections before longer branches.
for a,z,w in [('U28.1','C84.1',.3),('U28.5','C85.1',.3),('U29.20','C86.1',.25),('U30.8','C87.1',.25),('U31.3','C88.1',.2),('U31.7','C89.1',.2)]:connect(a,z,w)
for net,names in sorted(groups.items(),key=lambda item:(item[0] in ('LCD_3V0','+3V3','+5V_RF','SYS_EN'),list(groups).index(item[0]))):
 ordered=names.split();remaining=set(ordered[1:]);done={ordered[0]}
 while remaining:
  a,z=min(((a,z) for a in done for z in remaining),key=lambda az:(math.dist(xy(pad(az[0]).GetPosition()),xy(pad(az[1]).GetPosition())),az))
  b.BuildConnectivity();connected={x.m_Uuid.AsString() for x in b.GetConnectivity().GetConnectedItems(pad(a))}
  if pad(z).m_Uuid.AsString() not in connected:connect(a,z,.15 if a.startswith('J26.') or z.startswith('J26.') else .3 if net=='+5V_RF' else .25 if net in ('LCD_3V0','+3V3') else .15)
  remaining.remove(z);done.add(z)
def ground_escape(key):
    q=pad(key);assert q.GetNetname()=='GND'
    pos=xy(q.GetPosition());start=idx(pos,p.F_Cu)
    width=.15 if key.startswith('U') else .25
    masks,vm=obstacles('GND',width)
    assert not masks[start],('Ground pad blocked',key)
    queue=[(0,start)];cost={start:0};prev={};goal=None
    while queue:
        dist,node=heapq.heappop(queue)
        if dist!=cost[node]:continue
        layer,y,x=node
        if not vm[y,x]:goal=node;break
        for dy,dx,weight in [(1,0,1),(-1,0,1),(0,1,1),(0,-1,1),(1,1,1.414),(1,-1,1.414),(-1,1,1.414),(-1,-1,1.414)]:
            yy,xx=y+dy,x+dx;nxt=(layer,yy,xx)
            if not (0<=yy<NY and 0<=xx<NX) or masks[nxt] or math.dist(loc(start),loc(nxt))>5:continue
            if dx and dy and (masks[layer,y,xx] or masks[layer,yy,x]):continue
            nd=dist+weight
            if nd<cost.get(nxt,float('inf')):cost[nxt]=nd;prev[nxt]=node;heapq.heappush(queue,(nd,nxt))
    if goal is None:
        route_evidence.append(dict(start=key,end='existing ground pour; must pass physical continuity check',net='GND',dedicated_via_added=False))
        print('Check existing ground pour',key,flush=True);return
    path=[goal]
    while path[-1]!=start:path.append(prev[path[-1]])
    path.reverse();tr('GND',[pos,loc(start)],width,p.F_Cu);emit('GND',path,width);via('GND',*loc(goal),.5,.3)
    route_evidence.append(dict(start=key,end='In1.Cu ground plane via',net='GND',width_mm=width,trace_length_mm=round(cost[goal]*STEP+math.dist(pos,loc(start)),3),via_xy_mm=loc(goal)))
    print('Ground return',key,flush=True)

for key in ['U28.2','C84.2','C85.2','C86.2','C87.2','C88.2','C89.2','U29.1','U29.10','U29.15','U29.17','U29.19','U30.4','U30.7','U31.2','R80.2','C47.2','C48.2','C49.2']:
    if not any(r['start']==key and r['net']=='GND' and r.get('end') in ('In1.Cu ground plane via','fanout via') for r in route_evidence):ground_escape(key)

p.ZONE_FILLER(b).Fill(b.Zones())
p.SaveBoard(str(OUT/'handset.kicad_pcb'),b);shutil.copy2(SOURCE/'handset.kicad_pro',OUT/'handset.kicad_pro')
final=geometry(p.LoadBoard(str(OUT/'handset.kicad_pcb')))
assert original['footprints']==final['footprints']
for ident,entry in original['copper'].items():assert final['copper'][ident]==entry,ident
meta=dict(source_hashes=source_hashes,routes=route_evidence,groups=groups,preserved_copper_items=len(original['copper']),added_copper_items=len(final['copper'])-len(original['copper']),fabrication_released=False,scope='Display-domain physical routing only; electrical, thermal and timing qualification pending')
(OUT/'display-routing.json').write_text(json.dumps(meta,indent=2)+'\n')
