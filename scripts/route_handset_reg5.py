#!/usr/bin/env python3
"""Stage U10 local 5 V boost converter layout; preserve existing circuit copper."""
import csv,hashlib,heapq,json,math,shutil
from pathlib import Path
import numpy as np
import pcbnew as p
from sync_handset_schematic_rebuild import geometry
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hardware/handset-rev-a/generated'
OUT=Path('/tmp/handset-reg5-routing')
assert not (SOURCE/'reg5-routing.json').exists(),'Already installed; preserve later edits'
OUT.mkdir(exist_ok=True)
for f in SOURCE.iterdir():
 if f.is_file() and f.suffix not in ('.lck','.prl'):shutil.copy2(f,OUT/f.name)
shutil.copytree(SOURCE/'Handset.pretty',OUT/'Handset.pretty',dirs_exist_ok=True)
p.SwigPyIterator.next=p.SwigPyIterator.__next__
b=p.LoadBoard(str(SOURCE/'handset.kicad_pcb'));original=geometry(b)
fps={f.GetReference():f for f in b.GetFootprints()}
P=lambda xy:p.VECTOR2I(*(p.FromMM(v) for v in xy))
xy=lambda pos:(p.ToMM(pos.x),p.ToMM(pos.y))
X0,Y0,STEP=68.,49.,.05
NX,NY=1281,1881
LAYERS=[p.F_Cu,p.B_Cu,p.In2_Cu]
route_evidence=[]
escape_evidence={}
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
            paint(vm, x, y, w, h, a, 0.56 if pad.GetNetname() != net else 0.45)
            dw, dh = xy(pad.GetDrillSize())
            if dw > 0:
                for i in range(3):
                    paint(masks[i], x, y, dw, dh, a, 0.26 + width / 2)
                paint(vm, x, y, dw, dh, a, 0.56)
    for t in b.GetTracks():
        if t.GetNetname() == net:
            if t.GetClass() == 'PCB_VIA':
                x, y = xy(t.GetPosition())
                paint(vm, x, y, 0, 0, 0, 0.76, True)
            continue
        if t.GetClass() == 'PCB_VIA':
            x, y = xy(t.GetPosition())
            w = p.ToMM(t.GetWidth(p.F_Cu))
            for i in range(3):
                paint(masks[i], x, y, w, w, 0, clearance + width / 2, True)
            paint(vm, x, y, w, w, 0, 0.76, True)
        else:
            a, z = (xy(t.GetStart()), xy(t.GetEnd()))
            w = p.ToMM(t.GetWidth())
            if t.GetLayer() in LAYERS:
                capsule(masks[LAYERS.index(t.GetLayer())], a, z, w / 2 + clearance + width / 2)
            capsule(vm, a, z, w / 2 + 0.56)
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA' and t.GetNetname() == net:
            _, yy, xx = idx(xy(t.GetPosition()), p.F_Cu)
            if 0 <= yy < NY and 0 <= xx < NX:
                vm[yy, xx] = False
    xx = X0 + np.arange(NX)[None, :] * STEP
    yy = Y0 + np.arange(NY)[:, None] * STEP
    opening = (xx < 114.6) & (xx > 85.4) & (yy > 78.9) & (yy < 105.1)
    antenna=(xx<75.85)&(yy<82.6)
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
            via(net, *loc(before), 0.8, 0.4)
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
    if net=='VSYS':masks[0,:,:]=True;masks[2,:,:]=True
    start, goal = (idx(startpos, startlayer), idx(endpos, endlayer))
    path = search(start, goal, masks, vm)
    tr(net, [startpos, loc(start)], width, startlayer)
    emit(net, path, width)
    tr(net, [loc(goal), endpos], width, endlayer)
    return dict(trace_length_mm=round(sum(math.dist(loc(a),loc(z)) for a,z in zip(path,path[1:]) if a[0]==z[0])+math.dist(startpos,loc(start))+math.dist(endpos,loc(goal)),3),layer_transitions=sum(a[0]!=z[0] for a,z in zip(path,path[1:])))

def connect(a, z, width=0.15):
    pa, pz = (pad(a), pad(z))
    assert pa.GetNetname() == pz.GetNetname(), (a, z)
    metrics=route_points(pa.GetNetname(), xy(pa.GetPosition()), pa.GetParentFootprint().GetLayer(), xy(pz.GetPosition()), pz.GetParentFootprint().GetLayer(), width)
    route_evidence.append(dict(start=a,end=z,net=pa.GetNetname(),width_mm=width,**metrics))
    print('Connected', a, z, flush=True)

layout={'C26':(74.5,123,180),'R34':(69.6,121.4,0),'R35':(71.8,121.4,0)}
b.BuildConnectivity()
for ref,(x,y,a) in layout.items():
 f=fps[ref]
 for q in f.Pads():assert not b.GetConnectivity().GetConnectedTracks(q),ref+' already routed'
 f.SetPosition(P((x,y)));f.SetOrientationDegrees(a)
 f.Reference().SetLayer(p.B_Fab);f.Reference().SetPosition(P((x,y+1.8)))
tr('REG5_SW',[(73.7125,119),(74.6,119)],.3)
tr('REG5_SW',[(74.6,119),(76.815,119)],.6)
tr('+5V_RF',[(73.7125,119.5),(74.2,119.9875)],.3)
tr('+5V_RF',[(74.2,119.9875),(75.45,121.2375),(75.45,123)],.6)
tr('VSYS',[(72.2875,118.5),(71.05,118.5),(71.05,115)],.35)
tr('REG5_FB',[(72.2875,119.5),(71.29,120.4975),(71.29,121.4),(70.11,121.4)],.15)
tr('+5V_RF',[(75.45,123),(75.45,124.7),(69.09,124.7),(69.09,121.4)],.2)
tr('GND',[(73.7125,118.5),(74,118.2125),(74,117)],.3)
tr('GND',[(72.95,115),(73.8,115)],.5)
tr('GND',[(73.55,123),(72.8,123)],.5)
for pos in [(74,117),(73.8,115),(72.8,123)]:via('GND',*pos,.6,.3)
connect('L2.1','C25.1',.6)
connect('U10.2','SW19.2',.15)
for layer,right in [(p.B_Cu,83),(p.In1_Cu,86)]:
 z=p.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet('GND'));z.SetAssignedPriority(3)
 z.SetLocalClearance(p.FromMM(.2));z.SetPadConnection(p.ZONE_CONNECTION_FULL);z.SetMinThickness(p.FromMM(.15))
 poly=z.Outline();poly.NewOutline()
 for pos in [(68,113),(right,113),(right,125),(68,125)]:poly.Append(*P(pos))
 b.Add(z)
p.ZONE_FILLER(b).Fill(b.Zones())
p.SaveBoard(str(OUT/'handset.kicad_pcb'),b);shutil.copy2(SOURCE/'handset.kicad_pro',OUT/'handset.kicad_pro')
final=geometry(p.LoadBoard(str(OUT/'handset.kicad_pcb')))
for ident,entry in original['copper'].items():assert final['copper'][ident]==entry,ident
for ref,entry in original['footprints'].items():
 if ref not in layout:assert final['footprints'][ref]==entry,ref
spec=json.loads((OUT/'connectivity.json').read_text())
for c in spec:
 if c['ref'] in layout:c['x'],c['y'],c['angle']=layout[c['ref']]
(OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
with (OUT/'placement.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec)
meta=dict(source_hashes={str(f.relative_to(SOURCE)):hashlib.sha256(f.read_bytes()).hexdigest() for f in SOURCE.rglob('*') if f.is_file() and f.suffix in ('.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym','.kicad_mod','.json','.csv')},routes=route_evidence,moved_refs=layout,preserved_copper_items=len(original['copper']),added_copper_items=len(final['copper'])-len(original['copper']),fabrication_released=False,scope='U10 local boost and switch enable; external VSYS input/load distribution and qualification remain')
(OUT/'reg5-routing.json').write_text(json.dumps(meta,indent=2)+'\n')
