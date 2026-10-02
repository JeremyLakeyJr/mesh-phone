#!/usr/bin/env python3
"""Stage backlight routing; retain existing placement and copper."""
import csv,hashlib,heapq,json,math,shutil,sys
from pathlib import Path
import numpy as np
import pcbnew as p
from cad_sexpr import parse,dump,child
from sync_handset_schematic_rebuild import geometry
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('/tmp/handset-backlight')
OUT=Path('/tmp/handset-backlight-routing')
assert not (SOURCE/'backlight-routing.json').exists(),'Already installed; preserve subsequent edits'
OUT.mkdir(exist_ok=True)
source_hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in SOURCE.iterdir() if f.is_file()}
for f in SOURCE.iterdir():
 if f.is_file() and f.suffix not in ('.lck','.prl'):shutil.copy2(f,OUT/f.name)
shutil.copytree(SOURCE/'Handset.pretty',OUT/'Handset.pretty',dirs_exist_ok=True)
p.SwigPyIterator.next=p.SwigPyIterator.__next__
b=p.LoadBoard(str(SOURCE/'handset.kicad_pcb'));original=geometry(b)
# Rework only this local +5V branch: it crosses the four unescaped cathodes.
reworked_ids={'6598405a-6b84-4bf0-a582-d60b44d75d27','7346835f-bd85-46b0-951d-db1e89638991','994d6f57-5319-4146-a295-bc1c900f9c50','c4f13e05-d131-429d-83bd-c531ec8389b3','f1458e3d-7a91-4d7d-a8b2-5b9b8e8ce994','beb23655-bab7-4cf5-b84f-d7da72deb2f0'}
for t in b.GetTracks():
 if t.GetClass()!='PCB_VIA' and t.GetLayer()==p.B_Cu and t.GetNetname()=='+5V_RF':
  ends=[(p.ToMM(pos.x),p.ToMM(pos.y)) for pos in (t.GetStart(),t.GetEnd())]
  if all(87.25<=x<=90.95 and 63.1<=y<=64.95 for x,y in ends):reworked_ids.add(t.m_Uuid.AsString())
 if t.GetClass()!='PCB_VIA' and t.GetLayer()==p.F_Cu and t.GetNetname()=='TOUCH_IRQ':
  pos=t.GetStart()
  if 119<p.ToMM(pos.x)<128 and 118<p.ToMM(pos.y)<123:reworked_ids.add(t.m_Uuid.AsString())
assert reworked_ids <= original['copper'].keys()
tree=parse((OUT/'handset.kicad_pcb').read_text())
tree[:]=[n for n in tree if not(isinstance(n,list) and n[0] in ('segment','via') and str(child(n,'uuid')[1]) in reworked_ids)]
(OUT/'handset.kicad_pcb').write_text(dump(tree)+'\n');b=p.LoadBoard(str(OUT/'handset.kicad_pcb'))
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
        if len(cost)>2000000:
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

def connect(a,z,width=.15):
    pa,pz=pad(a),pad(z)
    assert pa.GetNetname()==pz.GetNetname(),(a,z)
    b.BuildConnectivity()
    if pz.m_Uuid.AsString() in {q.m_Uuid.AsString() for q in b.GetConnectivity().GetConnectedItems(pa)}:return
    endpoints=[]
    for key,q in [(a,pa),(z,pz)]:
        escape=next((r for r in route_evidence if r['start']==key and r.get('end')=='fanout via'),None)
        endpoints.append((tuple(escape['via_xy_mm']),p.B_Cu) if escape else (xy(q.GetPosition()),p.F_Cu))
    metrics=route_points(pa.GetNetname(),*endpoints[0],*endpoints[1],width)
    route_evidence.append(dict(start=a,end=z,net=pa.GetNetname(),width_mm=width,**metrics))
    print('Connected',a,z,flush=True)
    p.SaveBoard(str(OUT/'checkpoint.kicad_pcb'),b)
    (OUT/'checkpoint-routes.json').write_text(json.dumps(route_evidence,indent=2)+'\n')

def pin_escape(key):
    q=pad(key);net=q.GetNetname()
    pos=xy(q.GetPosition());start=idx(pos,p.F_Cu)
    masks,vm=obstacles(net,.15)
    assert not masks[start],('Ground pad blocked',key)
    queue=[(0,start)];cost={start:0};prev={};goal=None
    while queue:
        dist,node=heapq.heappop(queue)
        if dist!=cost[node]:continue
        layer,y,x=node
        if not vm[y,x]:goal=node;break
        for dy,dx,weight in [(1,0,1),(-1,0,1),(0,1,1),(0,-1,1),(1,1,1.414),(1,-1,1.414),(-1,1,1.414),(-1,-1,1.414)]:
            yy,xx=y+dy,x+dx;nxt=(layer,yy,xx)
            if not (0<=yy<NY and 0<=xx<NX) or masks[nxt] or math.dist(loc(start),loc(nxt))>(15 if key=='U2.14' else 5):continue
            if dx and dy and (masks[layer,y,xx] or masks[layer,yy,x]):continue
            nd=dist+weight
            if nd<cost.get(nxt,float('inf')):cost[nxt]=nd;prev[nxt]=node;heapq.heappush(queue,(nd,nxt))
    if goal is None:
        p.SaveBoard(str(OUT/'escape-failure.kicad_pcb'),b)
        np.savez(OUT/'escape-failure.npz',masks=masks,vm=vm,start=start)
        raise RuntimeError('No escape via site: '+key)
    path=[goal]
    while path[-1]!=start:path.append(prev[path[-1]])
    path.reverse();tr(net,[pos,loc(start)],.15,p.F_Cu);emit(net,path,.15);via(net,*loc(goal),.5,.3)
    route_evidence.append(dict(start=key,end='fanout via',net=net,width_mm=.15,trace_length_mm=round(cost[goal]*STEP+math.dist(pos,loc(start)),3),via_xy_mm=loc(goal)))
    print('Pin escape',key,flush=True)


if '--resume' not in sys.argv:
 for pin in [9,1,2,3,4,8,7,6,5]:pin_escape('U32.'+str(pin))
 # Stagger connector vias left of the existing In2 LCD_DC trace.
 for pin,points in [(2,[(88.25,63.15),(88.25,63.9),(88,64.25)]),(3,[(88.75,63.15),(88.75,64.4),(88.25,64.9)]),(4,[(89.25,63.15),(89.25,64.15)]),(5,[(89.75,63.15),(89.75,64.4),(89.75,64.6),(89.45,64.9),(89.25,64.9)])]:
  key='J26.'+str(pin);net=pad(key).GetNetname();vx,vy=points[-1]
  tr(net,points,.15,p.F_Cu);via(net,vx,vy,.5,.3)
  route_evidence.append(dict(start=key,end='fanout via',net=net,width_mm=.15,via_xy_mm=[vx,vy]))
 route_points('+5V_RF',(87.3,63.15),p.B_Cu,(90.9,64.9),p.B_Cu,.2)
 pin_escape('U2.14')
 route_points('TOUCH_IRQ',xy(pad('U2.15').GetPosition()),p.F_Cu,(121.95,121.8),p.B_Cu,.15)
 p.SaveBoard(str(OUT/'checkpoint.kicad_pcb'),b)
 (OUT/'checkpoint-routes.json').write_text(json.dumps(route_evidence,indent=2)+'\n')
zone=p.ZONE(b);zone.SetLayer(p.In1_Cu);zone.SetNet(b.FindNet('GND'));zone.SetLocalClearance(p.FromMM(.2));zone.SetThermalReliefGap(p.FromMM(.2));zone.SetThermalReliefSpokeWidth(p.FromMM(.25));zone.SetMinThickness(p.FromMM(.2));zone.SetZoneName('Backlight ground extension');zone.SetAssignedPriority(2)
poly=zone.Outline();poly.NewOutline()
for x,y in [(89,72),(102,72),(102,78.8),(89,78.8)]:poly.Append(int(p.FromMM(x)),int(p.FromMM(y)))
if not any(z.GetZoneName()=='Backlight ground extension' for z in b.Zones()):b.Add(zone)
# Route the host control first so later ground/gate traces do not enclose R56.1.
for a,z,w in [('U2.14','R56.1',.15),('U32.7','R82.1',.15),('U32.8','C90.1',.2),('U32.2','U32.9',.2),('R82.2','U32.9',.2),('C90.2','U32.9',.25),('U32.3','J26.2',.15),('U32.4','J26.3',.15),('U32.5','J26.4',.15),('U32.6','J26.5',.15),('U32.1','R56.2',.15),('R56.2','R57.1',.15),('R57.2','C49.2',.2),('C90.1','C49.1',.3)]:connect(a,z,w)
p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'handset.kicad_pcb'),b);shutil.copy2(SOURCE/'handset.kicad_pro',OUT/'handset.kicad_pro')
final=geometry(b)
assert original['footprints']==final['footprints']
assert all(final['copper'].get(k)==v for k,v in original['copper'].items() if k not in reworked_ids)
(OUT/'backlight-routing.json').write_text(json.dumps(dict(source_hashes=source_hashes,reworked_original_copper_ids=sorted(reworked_ids),routes=route_evidence,source_copper_items=len(original['copper']),preserved_copper_items=len(original['copper'])-len(reworked_ids),added_copper_items=len(final['copper'].keys()-original['copper'].keys()),net_copper_change=len(final['copper'])-len(original['copper']),fabrication_released=False),indent=2)+'\n')
