#!/usr/bin/env python3
"""Route the staged charge-inhibit control path; native DRC is the acceptance check.
Lattice helpers derived from route_handset_power_entry; no RF/power routing.
"""
import heapq,json,math,shutil
from pathlib import Path
import numpy as np
import pcbnew as p
from sync_handset_schematic_rebuild import geometry
OUT=Path('/tmp/handset-charge-inhibit')
p.SwigPyIterator.next=p.SwigPyIterator.__next__
b=p.LoadBoard(str(OUT/'charge-inhibit-unrouted.kicad_pcb'))
fps={f.GetReference():f for f in b.GetFootprints()}
P=lambda xy:p.VECTOR2I(*(p.FromMM(v) for v in xy))
xy=lambda pos:(p.ToMM(pos.x),p.ToMM(pos.y))
X0,Y0,STEP=98.,60.,.05
NX,NY=521,1201
LAYERS=[p.F_Cu,p.B_Cu,p.In2_Cu]
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
    # Trackball cutout plus 0.5 mm routing/edge margin on every copper layer.
    xx=X0+np.arange(NX)[None,:]*STEP; yy=Y0+np.arange(NY)[:,None]*STEP
    opening=(xx<114.15)&(xx>85.85)&(yy>79.35)&(yy<104.65)
    masks |= opening[None,:,:]; vm |= opening
    return (masks, vm)

def search(start, goal, masks, vm):
    if masks[start] or masks[goal]:
        raise RuntimeError(f'Blocked endpoint {start} -> {goal}')

    def heuristic(n):
        return max(abs(n[1] - goal[1]), abs(n[2] - goal[2])) + (0 if n[0] == goal[0] else 16)
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

def connect(ref1,pin1,ref2,pin2):
    a=next(q for q in fps[ref1].Pads() if q.GetNumber()==pin1)
    z=next(q for q in fps[ref2].Pads() if q.GetNumber()==pin2)
    assert a.GetNetname()==z.GetNetname()
    net=a.GetNetname();masks,vm=obstacles(net)
    start=idx(xy(a.GetPosition()),a.GetParentFootprint().GetLayer())
    goal=idx(xy(z.GetPosition()),z.GetParentFootprint().GetLayer())
    path=search(start,goal,masks,vm)
    tr(net,[xy(a.GetPosition()),loc(start)],.15,a.GetParentFootprint().GetLayer())
    emit(net,path)
    tr(net,[loc(goal),xy(z.GetPosition())],.15,z.GetParentFootprint().GetLayer())
    print('Connected',ref1+'.'+pin1,ref2+'.'+pin2,flush=True)

connect('Q5','2','Q8','3')
connect('Q8','2','R7','2')
connect('R79','2','Q8','2')
connect('R79','1','Q8','1')
connect('U25','6','R79','1')
p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
shutil.copy2(Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated/handset.kicad_pro',OUT/'handset.kicad_pro')

source=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
original=geometry(p.LoadBoard(str(source/'handset.kicad_pcb')))
final=geometry(p.LoadBoard(str(OUT/'handset.kicad_pcb')))
meta=json.loads((OUT/'charge-inhibit-update.json').read_text())
for ident,entry in original['copper'].items():
    if ident not in meta['removed_copper']:assert final['copper'][ident]==entry,ident
for ref,entry in original['footprints'].items():assert final['footprints'][ref]==entry,ref
new_ids=set(final['copper'])-set(original['copper'])
meta['added_copper_items']=len(new_ids)
meta['routed_nets']=['CHG_ARM','CHG_CE_RETURN','local GND returns']
meta['routing_complete_for_inhibit']=True
meta['scope']='Independent CE permission routed; remaining supervisor power/I2C routing and target firmware incomplete'
(OUT/'charge-inhibit-update.json').write_text(json.dumps(meta,indent=2)+'\n')
