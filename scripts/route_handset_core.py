#!/usr/bin/env python3
"""Stage core bring-up routing; retain prior copper except one recorded matrix segment."""
import csv,hashlib,heapq,json,math,shutil,sys
from pathlib import Path
import numpy as np
import pcbnew as p
from sync_handset_schematic_rebuild import geometry
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'hardware/handset-rev-a/generated';OUT=Path('/tmp/handset-core-routing')
assert not (SOURCE/'core-routing.json').exists(),'Already installed; preserve subsequent edits'
shutil.copytree(SOURCE,OUT,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.history','.git','*.lck','*.prl'))
b=p.LoadBoard(str(SOURCE/'handset.kicad_pcb'));original=geometry(b)
b.BuildConnectivity()
source_pads={q.m_Uuid.AsString():q for f in b.GetFootprints() for q in f.Pads()}
source_groups=[];seen=set()
for uid,q in source_pads.items():
 if uid in seen:continue
 group={v.m_Uuid.AsString() for v in b.GetConnectivity().GetConnectedItems(q)}&source_pads.keys();group.add(uid)
 source_groups.append(group);seen|=group

# Rework only the pre-existing matrix trunk that crosses the new through-via fanout.
xy=lambda pos:(p.ToMM(pos.x),p.ToMM(pos.y))
reworked=[]
for t in list(b.GetTracks()):
 if t.GetClass()=='PCB_TRACK' and t.GetNetname()=='KEY_COL3' and abs(p.ToMM(t.GetLength())-45)<.01:
  reworked.append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname(),start=xy(t.GetStart()),end=xy(t.GetEnd()),layer=t.GetLayer(),width=p.ToMM(t.GetWidth())))
assert len(reworked)==1
from cad_sexpr import parse,dump,child
tree=parse((SOURCE/'handset.kicad_pcb').read_text());removed={r['uuid'] for r in reworked}
tree[:]=[n for n in tree if not (isinstance(n,list) and n and n[0]=='segment' and child(n,'uuid')[1] in removed)]
(OUT/'routing-input.kicad_pcb').write_text(dump(tree)+'\n')
b=p.LoadBoard(str(OUT/'routing-input.kicad_pcb'))
fps={f.GetReference():f for f in b.GetFootprints()};b.BuildConnectivity()
for q in fps['C4'].Pads():assert all(isinstance(i,p.PAD) and i.m_Uuid==q.m_Uuid for i in b.GetConnectivity().GetConnectedItems(q)),'C4 already routed'
fps['R2'].SetPosition(p.VECTOR2I(p.FromMM(98.8),p.FromMM(63.3)))
fps['R2'].SetOrientationDegrees(0)
fps['C4'].SetPosition(p.VECTOR2I(p.FromMM(123.5),p.FromMM(117.6)))
fps['C4'].Flip(fps['C4'].GetPosition(),False)
fps['C4'].SetOrientationDegrees(0)
P=lambda xy:p.VECTOR2I(*(p.FromMM(v) for v in xy))
xy=lambda pos:(p.ToMM(pos.x),p.ToMM(pos.y))
X0,Y0,STEP=68.,30.,.05
NX,NY=1281,2801
LAYERS=[p.F_Cu,p.B_Cu,p.In1_Cu,p.In2_Cu]
route_evidence=[]
def tr(net, points, width=0.18, layer=p.B_Cu):
    for a, z in zip(points, points[1:]):
        if P(a) == P(z):
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
    masks = np.zeros((len(LAYERS), NY, NX), dtype=bool)
    vm = np.zeros((NY, NX), dtype=bool)
    clearance = 0.16
    for f in b.GetFootprints():
        for pad in f.Pads():
            x, y = xy(pad.GetPosition())
            w, h = xy(pad.GetSize())
            a = pad.GetOrientationDegrees()
            if pad.GetShape() == p.PAD_SHAPE_CUSTOM:
                box = pad.GetBoundingBox()
                x = p.ToMM(box.GetX() + box.GetWidth() / 2)
                y = p.ToMM(box.GetY() + box.GetHeight() / 2)
                w = p.ToMM(box.GetWidth())
                h = p.ToMM(box.GetHeight())
                a = 0
            if pad.GetNetname() != net:
                for i, layer in enumerate(LAYERS):
                    if pad.IsOnLayer(layer):
                        paint(masks[i], x, y, w, h, a, clearance + width / 2)
            vip = False
            if not (vip and pad.GetNetname() == net):
                paint(vm, x, y, w, h, a, 0.41 if pad.GetNetname() != net else 0.3)
            dw, dh = xy(pad.GetDrillSize())
            if dw > 0:
                for i in range(len(LAYERS)):
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
            for i in range(len(LAYERS)):
                paint(masks[i], x, y, w, w, 0, clearance + width / 2, True)
            paint(vm, x, y, w, w, 0, 0.41, True)
        else:
            a, z = (xy(t.GetStart()), xy(t.GetEnd()))
            w = p.ToMM(t.GetWidth())
            if t.GetLayer() in LAYERS:
                capsule(masks[LAYERS.index(t.GetLayer())], a, z, w / 2 + clearance + width / 2)
            capsule(vm, a, z, w / 2 + (0.7 if t.GetNetname().startswith('USB_D_') else 0.41))
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA' and t.GetNetname() == net:
            _, yy, xx = idx(xy(t.GetPosition()), p.F_Cu)
            if 0 <= yy < NY and 0 <= xx < NX:
                vm[yy, xx] = False
    xx = X0 + np.arange(NX)[None, :] * STEP
    yy = Y0 + np.arange(NY)[:, None] * STEP
    opening = (xx < 114.6) & (xx > 85.4) & (yy > 78.9) & (yy < 105.1)
    opening &= ~((xx >= 89.5) & (xx <= 108.5) & (yy <= 79.49 - width / 2))
    antenna = (xx < 75.85) & (yy < 82.6)
    if net in ('LCD_DC', 'LCD_RESET', 'TOUCH_RESET', 'TOUCH_IRQ'):
        reserved = (xx > 84) & (xx < 116) & (yy > 59) & (yy < 77)
        masks[0] |= reserved
        vm |= reserved
    for xa, ya, xz, yz in [(119.0, 95.2, 123.7, 104.2), (117.0, 98.2, 119.4, 101.2)]:
        socket = (xx >= xa - width / 2) & (xx <= xz + width / 2) & (yy >= ya - width / 2) & (yy <= yz + width / 2)
        masks[0] |= socket
        vm |= socket
    masks[2:] |= ((yy < 61) & (xx > 88))[None,:,:]
    masks |= (opening | antenna)[None, :, :]
    vm |= opening | antenna
    vm |= (xx >= 85.4) & (xx <= 114.6) & (yy > 79.24) & (yy < 105.1)
    return (masks, vm)

def search(start, goal, masks, vm):
    if masks[start] or masks[goal]:
        raise RuntimeError(f'Blocked endpoint {start} -> {goal}')

    def heuristic(n):
        dy, dx = (abs(n[1] - goal[1]), abs(n[2] - goal[2]))
        return max(dx, dy) + 0.414 * min(dx, dy) + (0 if n[0] == goal[0] else 16)
    local=math.dist(start[1:],goal[1:])<300
    ymin,ymax=min(start[1],goal[1])-160,max(start[1],goal[1])+160
    xmin,xmax=min(start[2],goal[2])-160,max(start[2],goal[2])+160
    heap = [(heuristic(start), 0, start)]
    cost = {start: 0}
    prev = {}
    directions = [(1, 0, 1), (0, 1, 1), (-1, 0, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    while heap:
        if len(cost) > 2000000:
            p.SaveBoard(str(OUT / 'routing-failure.kicad_pcb'), b)
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
            if local and not(ymin<=yy<=ymax and xmin<=xx<=xmax):continue
            if not (0 <= yy < NY and 0 <= xx < NX) or masks[layer, yy, xx]:
                continue
            if dx and dy and (masks[layer, y, xx] or masks[layer, yy, x]):
                continue
            nxt = (layer, yy, xx)
            nd = d + step * (8 if layer == 3 else 1)
            if nd < cost.get(nxt, float('inf')):
                cost[nxt] = nd
                prev[nxt] = node
                heapq.heappush(heap, (nd + 4 * heuristic(nxt), nd, nxt))
        if not vm[y, x]:
            for other in range(len(LAYERS)):
                if other == layer or masks[other, y, x]:
                    continue
                nxt = (other, y, x)
                nd = d + 25
                if nd < cost.get(nxt, float('inf')):
                    cost[nxt] = nd
                    prev[nxt] = node
                    heapq.heappush(heap, (nd + 4 * heuristic(nxt), nd, nxt))
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
    np.savez(OUT / 'route-mask.npz', masks=masks, vm=vm, start=start, goal=goal)
    path = search(goal, start, masks, vm)[::-1]
    tr(net, [startpos, loc(start)], width, startlayer)
    emit(net, path, width)
    tr(net, [loc(goal), endpos], width, endlayer)
    return dict(trace_length_mm=round(sum((math.dist(loc(a), loc(z)) for a, z in zip(path, path[1:]) if a[0] == z[0])) + math.dist(startpos, loc(start)) + math.dist(endpos, loc(goal)), 3), layer_transitions=sum((a[0] != z[0] for a, z in zip(path, path[1:]))))

def connect(a,z,width=.15):
 pa,pz=pad(a),pad(z);assert pa.GetNetname()==pz.GetNetname(),(a,z)
 b.BuildConnectivity()
 if pz.m_Uuid.AsString() in {i.m_Uuid.AsString() for i in b.GetConnectivity().GetConnectedItems(pa)}:return
 startpos,startlayer=xy(pa.GetPosition()),pa.GetParentFootprint().GetLayer()
 if a in ('R4.1','R1.1'):
  connected_ids={t.m_Uuid.AsString() for t in b.GetConnectivity().GetConnectedItems(pa)}
  candidates=[t for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.m_Uuid.AsString() in connected_ids and (a!='R1.1' or xy(t.GetPosition())[1]>61)]
  v=min(candidates,key=lambda t:math.dist(xy(t.GetPosition()),xy(pz.GetPosition())))
  startpos,startlayer=xy(v.GetPosition()),p.B_Cu
 if a=='U2.20':startpos,startlayer=(124.4,116.1),p.B_Cu
 if a=='U2.21':startpos,startlayer=(123.5,115.9),p.B_Cu
 if a=='U2.24':startpos,startlayer=(121.4,116.85),p.In1_Cu
 if a in ('U2.23','U2.22'):startpos,startlayer=({'U2.23':122.1,'U2.22':122.8}[a],116.18),p.B_Cu
 metrics=route_points(pa.GetNetname(),startpos,startlayer,xy(pz.GetPosition()),pz.GetParentFootprint().GetLayer(),width)
 route_evidence.append(dict(start=a,end=z,net=pa.GetNetname(),width_mm=width,**metrics));print('Connected',a,z,flush=True)
 p.SaveBoard(str(OUT/'checkpoint.kicad_pcb'),b)
# Connect all duplicate physical switch contacts explicitly.
for ref in ('SW17','SW18'):
 f=fps[ref]
 for number,waypoint_y in [('1',162.9),('2',169.2)]:
  ends=sorted([xy(q.GetPosition()) for q in f.Pads() if q.GetNumber()==number]);net=next(q.GetNetname() for q in f.Pads() if q.GetNumber()==number)
  tr(net,[ends[0],(ends[0][0],waypoint_y),(ends[1][0],waypoint_y),ends[1]],.2,p.F_Cu)
  if number=='2':
   for x,y in ends:via(net,x,waypoint_y,.5,.3)
# Short exposed-pad ground escape through pad 19; no drilled via in the EP.
tr('GND',[(123,119),(124.25,119),(124.25,117.0375),(126.2,116.9)],.2,p.F_Cu)
via('GND',126.2,116.9,.5,.3)
# Fill the lower board reference area, respecting all prior zone outlines.
for layer in [p.In1_Cu,p.In2_Cu]:
 z=p.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet('GND'));z.SetLocalClearance(p.FromMM(.2));z.SetMinThickness(p.FromMM(.2));z.SetZoneName('Core controls return');z.SetAssignedPriority(9);z.SetPadConnection(p.ZONE_CONNECTION_FULL)
 poly=z.Outline();poly.NewOutline()
 for x,y in [(70.5,105.2),(131.5,105.2),(131.5,170),(70.5,170)]:poly.Append(p.FromMM(x),p.FromMM(y))
 for existing in b.Zones():
  if existing.GetLayer()==layer:poly.BooleanSubtract(existing.Outline())
 b.Add(z)
tr('KEY_IRQ',[(121.75,117.0375),(121.4,116.85)],.15,p.F_Cu)
via('KEY_IRQ',121.4,116.85,.5,.3)
tr('MCU_EN',[(123.75,117.0375),(123.75,116.6),(124.25,116.1),(124.4,116.1)],.15,p.F_Cu)
via('MCU_EN',124.4,116.1,.5,.3)
tr('+3V3',[(123.25,117.0375),(123.25,116.45),(123.5,115.9)],.2,p.F_Cu)
via('+3V3',123.5,115.9,.5,.3)
# Explicit fine-pitch fanout within the native clearance rules.
for pin,x in [(23,122.1),(22,122.8)]:
 q=pad('U2.'+str(pin));net=q.GetNetname();px,py=xy(q.GetPosition())
 tr(net,[(px,py),(px,116.5),(x,116.35),(x,116.18)],.15,p.F_Cu)
 via(net,x,116.18,.5,.3)
for old in reworked:
 tr(old['net'],[(122.5,119),old['end']],old['width'],old['layer'])
 tr(old['net'],[old['start'],(122.5,114)],old['width'],old['layer'])
 route_points(old['net'],(122.5,114),old['layer'],(122.5,119),old['layer'],old['width'])
# Local bypass and controller bus connections precede long button trunks.
for a,z,w in [('U2.23','R3.2',.15),('U2.22','R4.2',.15),('U2.24','R5.2',.15),('U2.20','U33.6',.15),('U2.21','C4.1',.2),('C4.2','U2.19',.2),('R5.1','C4.1',.2),('R4.1','R5.1',.2),('R1.1','R2.1',.2),('U1.27','R2.2',.15),('U1.12','R5.2',.15),('U33.6','SW18.1',.15),('U1.27','SW17.1',.15)]:connect(a,z,w)
p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
shutil.copy2(SOURCE/'handset.kicad_pro',OUT/'handset.kicad_pro')
b.BuildConnectivity()
final_pads={q.m_Uuid.AsString():q for f in b.GetFootprints() for q in f.Pads()}
for group in source_groups:
 uid=next(iter(group));connected={q.m_Uuid.AsString() for q in b.GetConnectivity().GetConnectedItems(final_pads[uid])}|{uid}
 assert group<=connected,'Previously connected pads were disconnected'
final=geometry(b);assert all(final['copper'][k]==v for k,v in original['copper'].items() if k not in {r['uuid'] for r in reworked})
assert all(final['footprints'][k]==v for k,v in original['footprints'].items() if k not in ('C4','R2'))
spec=json.loads((SOURCE/'connectivity.json').read_text())
for c in spec:
 if c['ref']=='C4':c.update(x=123.5,y=117.6,side='B',angle=0)
 if c['ref']=='R2':c.update(x=98.8,y=63.3,angle=0)
(OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
with (OUT/'placement.csv').open('w') as stream:
 writer=csv.DictWriter(stream,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');writer.writeheader();writer.writerows(spec)
manifest=dict(preserved_pad_groups=len(source_groups),reworked_copper=reworked,source_board_sha256=hashlib.sha256((SOURCE/'handset.kicad_pcb').read_bytes()).hexdigest(),final_board_sha256=hashlib.sha256((OUT/'handset.kicad_pcb').read_bytes()).hexdigest(),preserved_copper_items=len(original['copper'])-len(reworked),added_copper_items=len(final['copper'])-len(original['copper'])+len(reworked),moved_refs={'R2':{'from_mm':[98,62],'to_mm':[98.8,63.3],'reason':'Unrouted boot pull-up moved into a clear escape corridor'},'C4':{'from_mm':[128,119],'to_mm':[123.5,117.6],'to_side':'B','reason':'Place the unrouted local bypass beside the TCA8418 supply pad'}},routes=route_evidence,reference_pours=['In1.Cu','In2.Cu'],fabrication_released=False)
(OUT/'core-routing.json').write_text(json.dumps(manifest,indent=2)+'\n');print('Staged',OUT,flush=True)
