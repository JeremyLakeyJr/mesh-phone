#!/usr/bin/env python3
"""Stage supervisor power, buses and SWD routing. Native DRC and continuity required.
Lattice is for low-speed control only. Existing copper is immutable.
"""
import csv,hashlib,heapq,json,math,shutil
from pathlib import Path
import numpy as np
import pcbnew as p
from sync_handset_schematic_rebuild import geometry
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hardware/handset-rev-a/generated'
OUT=Path('/tmp/handset-supervisor-routing')
assert not (SOURCE/'supervisor-routing.json').exists(), 'Already installed; preserve subsequent edits.'
OUT.mkdir(exist_ok=True)
for f in SOURCE.iterdir():
    if f.is_file() and f.suffix not in ('.lck','.prl'):shutil.copy2(f,OUT/f.name)
shutil.copytree(SOURCE/'Handset.pretty',OUT/'Handset.pretty',dirs_exist_ok=True)
p.SwigPyIterator.next=p.SwigPyIterator.__next__
b=p.LoadBoard(str(SOURCE/'handset.kicad_pcb'))
original=geometry(b)
fps={f.GetReference():f for f in b.GetFootprints()}
P=lambda xy:p.VECTOR2I(*(p.FromMM(v) for v in xy))
xy=lambda pos:(p.ToMM(pos.x),p.ToMM(pos.y))
X0,Y0,STEP=76.,49.,.05
NX,NY=1081,1781
LAYERS=[p.F_Cu,p.B_Cu,p.In2_Cu]
# Only unrouted bypass parts move; retain ICs, existing copper and inhibit route.
moved={'C77':(95,109.8,0),'C78':(87.4,109.8,180),
       'C79':(103.8,110.5,0),'C80':(105,109,0),
       'C81':(115.2,113.2,0),'C82':(106.4,114,180)}
for ref,(x,y,angle) in moved.items():
    fps[ref].SetPosition(P((x,y)));fps[ref].SetOrientationDegrees(angle)
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
    if any((t.GetClass() == 'PCB_VIA' and t.GetNetname() == net and (math.dist(xy(t.GetPosition()), (x, y)) < 0.001) for t in b.GetTracks())):
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
    opening = (xx < 114.15) & (xx > 85.85) & (yy > 79.35) & (yy < 104.65)
    masks |= opening[None, :, :]
    vm |= opening
    return (masks, vm)

def search(start, goal, masks, vm):
    if masks[start] or masks[goal]:
        raise RuntimeError(f'Blocked endpoint {start} -> {goal}')

    def heuristic(n):
        dy,dx=abs(n[1]-goal[1]),abs(n[2]-goal[2])
        return max(dx,dy)+0.414*min(dx,dy)+(0 if n[0]==goal[0] else 16)
    heap = [(heuristic(start), 0, start)]
    cost = {start: 0}
    prev = {}
    directions = [(1, 0, 1), (0, 1, 1), (-1, 0, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    while heap:
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
                heapq.heappush(heap, (nd + heuristic(nxt), nd, nxt))
        if not vm[y, x]:
            for other in range(3):
                if other == layer or masks[other, y, x]:
                    continue
                nxt = (other, y, x)
                nd = d + 25
                if nd < cost.get(nxt, float('inf')):
                    cost[nxt] = nd
                    prev[nxt] = node
                    heapq.heappush(heap, (nd + heuristic(nxt), nd, nxt))
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
    ref,pin=key.split('.')
    return next(q for q in fps[ref].Pads() if q.GetNumber()==pin)

def route_points(net,startpos,startlayer,endpos,endlayer,width=.15):
    masks,vm=obstacles(net,width)
    start,goal=idx(startpos,startlayer),idx(endpos,endlayer)
    path=search(start,goal,masks,vm)
    tr(net,[startpos,loc(start)],width,startlayer);emit(net,path,width)
    tr(net,[loc(goal),endpos],width,endlayer)

def connect(a,z,width=.15):
    pa,pz=pad(a),pad(z);assert pa.GetNetname()==pz.GetNetname(),(a,z)
    route_points(pa.GetNetname(),xy(pa.GetPosition()),pa.GetParentFootprint().GetLayer(),xy(pz.GetPosition()),pz.GetParentFootprint().GetLayer(),width)
    print('Connected',a,z,flush=True)

# Connected local reference plane below the cutout, meeting existing ground trunk.
zone=p.ZONE(b);zone.SetLayer(p.In1_Cu);zone.SetNet(b.FindNet('GND'))
zone.SetLocalClearance(p.FromMM(.2));zone.SetPadConnection(p.ZONE_CONNECTION_FULL)
zone.SetMinThickness(p.FromMM(.2));poly=zone.Outline();poly.NewOutline()
for pos in [(85,105),(114.2,105),(114.2,100),(130,100),(130,137),(116,137),(116,127),(85,127)]:poly.Append(*P(pos))
b.Add(zone)

p.SaveBoard(str(OUT/'placement-check.kicad_pcb'),b)
shutil.copy2(SOURCE/'handset.kicad_pro',OUT/'placement-check.kicad_pro')
# Route short supply-to-bypass branches before the longer connections.
for a,z in [('U26.1','C77.1'),('U26.1','U26.3'),('U26.5','C78.1'),
            ('U25.3','C79.1'),('C79.1','C80.1'),('U27.1','C81.1'),
            ('U27.8','C82.1')]:connect(a,z)
# Every local return has its own nearby connection to the ground plane.
ground_keys=['U25.4','U26.2','U27.4']+['C'+str(i)+'.2' for i in range(77,84)]+['TP3.1']
ground_vias={}
for key in ground_keys:
    pa=pad(key);pos=xy(pa.GetPosition());masks,vm=obstacles('GND')
    center=idx(pos,p.B_Cu);candidates=[]
    for dy in range(-30,31):
        for dx in range(-30,31):
            n=(1,center[1]+dy,center[2]+dx)
            if not masks[n] and not vm[n[1],n[2]]:candidates.append((dx*dx+dy*dy,n))
    for _,n in sorted(candidates):
        try:path=search(center,n,masks,vm)
        except RuntimeError:continue
        target=loc(n);tr('GND',[pos,loc(center)],.15,p.B_Cu);emit('GND',path)
        via('GND',*target,.5,.3);ground_vias[key]=target;break
    else:raise RuntimeError('No local ground via for '+key)
    print('Ground return',key,ground_vias[key],flush=True)

# Short local signal branches, followed by the private charger bus.
for a,z in [('U25.5','C83.1'),('C83.1','R78.2'),('R78.2','TP6.1'),
            ('U25.20','TP4.1'),('U25.21','TP5.1'),
            ('U25.18','U27.7'),('U25.19','U27.6'),
            ('U25.28','R76.2'),('U25.27','R77.2')]:connect(a,z)
# Local AON distribution. Main +3V3 is a separate switched domain.
for a,z in [('U26.5','C79.1'),('C79.1','C82.1'),('C79.1','R76.1'),
            ('R76.1','R77.1'),('R77.1','R78.1'),('R78.1','TP2.1'),
            ('U27.1','U27.5'),('U27.1','R3.1'),('R3.1','R4.1')]:connect(a,z)
# Long low-current power/control paths; no changes to modem/battery load routing.
for a,z,w in [('C77.1','C6.1',.25),('C78.1','C60.1',.2),
              ('R76.2','U24.6',.15),('R77.2','U24.7',.15),
              ('C81.1','C21.1',.25),
              ('U27.2','R3.2',.15),('U27.3','R4.2',.15),
              ('R3.2','U1.17',.15),('R4.2','U1.18',.15)]:connect(a,z,w)

p.ZONE_FILLER(b).Fill(b.Zones())
p.SaveBoard(str(OUT/'handset.kicad_pcb'),b);shutil.copy2(SOURCE/'handset.kicad_pro',OUT/'handset.kicad_pro')
final=geometry(p.LoadBoard(str(OUT/'handset.kicad_pcb')))
for ident,entry in original['copper'].items():assert final['copper'][ident]==entry,ident
for ref,entry in original['footprints'].items():
    if ref not in moved:assert final['footprints'][ref]==entry,ref
spec=json.loads((SOURCE/'connectivity.json').read_text())
for c in spec:
    if c['ref'] in moved:c['x'],c['y'],c['angle']=moved[c['ref']]
(OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
with (OUT/'placement.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(spec)
meta=dict(source_hashes={str(f.relative_to(SOURCE)):hashlib.sha256(f.read_bytes()).hexdigest() for f in SOURCE.rglob('*') if f.is_file() and f.suffix in ('.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym','.kicad_mod','.json','.csv')},
    moved_bypass_parts=moved,ground_vias=ground_vias,preserved_copper_items=len(original['copper']),added_copper_items=len(final['copper'])-len(original['copper']),
    added_ground_zone=zone.m_Uuid.AsString(),fabrication_released=False,
    scope='Supervisor power, private/host bus and SWD routing; other host peripherals and power distribution remain incomplete')
(OUT/'supervisor-routing.json').write_text(json.dumps(meta,indent=2)+'\n')
