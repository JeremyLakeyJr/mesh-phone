#!/usr/bin/env python3
"""Stage expansion routing; retain existing placement and copper."""
import csv,hashlib,heapq,json,math,shutil,sys
from pathlib import Path
import numpy as np
import pcbnew as p
from cad_sexpr import parse,dump,child
from sync_handset_schematic_rebuild import geometry
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('/tmp/handset-expansion')
OUT=Path('/tmp/handset-expansion-routing')
assert not (SOURCE/'expansion-routing.json').exists(),'Already installed; preserve subsequent edits'
OUT.mkdir(exist_ok=True)
source_hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in SOURCE.iterdir() if f.is_file() and f.suffix not in ('.lck','.prl')}
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
LAYERS=[p.F_Cu,p.B_Cu,p.In2_Cu,p.In1_Cu]
route_evidence=json.loads((OUT/'checkpoint-routes.json').read_text()) if '--resume' in sys.argv else []
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
            if pad.GetShape()==p.PAD_SHAPE_CUSTOM:
                box=pad.GetBoundingBox()
                x=p.ToMM(box.GetX()+box.GetWidth()/2);y=p.ToMM(box.GetY()+box.GetHeight()/2)
                w=p.ToMM(box.GetWidth());h=p.ToMM(box.GetHeight());a=0
            if pad.GetNetname() != net:
                for i, layer in enumerate(LAYERS):
                    if pad.IsOnLayer(layer):
                        paint(masks[i], x, y, w, h, a, clearance + width / 2)
            # Named lands need filled/capped via-in-pad escapes. Opposite-side
            # copper and all foreign nets remain clearance obstacles.
            vip=(f.GetReference(),pad.GetNumber()) in {('J16','8'),('U14','1'),('U14','6'),('U16','1')}
            if not (vip and pad.GetNetname()==net):
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
            capsule(vm, a, z, w / 2 + 0.41)
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA' and t.GetNetname() == net:
            _, yy, xx = idx(xy(t.GetPosition()), p.F_Cu)
            if 0 <= yy < NY and 0 <= xx < NX:
                vm[yy, xx] = False
    xx = X0 + np.arange(NX)[None, :] * STEP
    yy = Y0 + np.arange(NY)[:, None] * STEP
    opening = (xx < 114.6) & (xx > 85.4) & (yy > 78.9) & (yy < 105.1)
    # Native cut starts at y=80 here. Retain at least 0.45 mm centerline
    # setback in the connector escape bay; wider keepout stays elsewhere.
    opening &= ~((xx>=89.5)&(xx<=108.5)&(yy<=79.49-width/2))
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
    vm |= (xx>=85.4)&(xx<=114.6)&(yy>79.24)&(yy<105.1)
    # Some port lands are enclosed on the other three layers. In1 escapes
    # carry a heavy path cost and clear the GND fill. Continuity, slot lengths
    # and remaining return-path qualification are reported independently.
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
            nd = d + step*(8 if layer==3 else 1)
            if nd < cost.get(nxt, float('inf')):
                cost[nxt] = nd
                prev[nxt] = node
                heapq.heappush(heap, (nd + 4*heuristic(nxt), nd, nxt))
        if not vm[y, x]:
            for other in range(len(LAYERS)):
                if other == layer or masks[other, y, x]:
                    continue
                nxt = (other, y, x)
                nd = d + 25
                if nd < cost.get(nxt, float('inf')):
                    cost[nxt] = nd
                    prev[nxt] = node
                    heapq.heappush(heap, (nd + 4*heuristic(nxt), nd, nxt))
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
        endpoint=(tuple(escape['via_xy_mm']),p.B_Cu) if escape else (xy(q.GetPosition()),p.B_Cu if fps[key.split('.')[0]].IsFlipped() else p.F_Cu)
        # Branch from already connected copper, avoiding a second escape from
        # a host land that is now surrounded by completed routes.
        connected_vias=[i for i in b.GetConnectivity().GetConnectedItems(q) if i.GetClass()=='PCB_VIA']
        if connected_vias:
            target=xy((pz if key==a else pa).GetPosition())
            v=min(connected_vias,key=lambda i:math.dist(xy(i.GetPosition()),target))
            endpoint=(xy(v.GetPosition()),p.In2_Cu)
        endpoints.append(endpoint)
    metrics=route_points(pa.GetNetname(),*endpoints[0],*endpoints[1],width)
    route_evidence.append(dict(start=a,end=z,net=pa.GetNetname(),width_mm=width,**metrics))
    print('Connected',a,z,flush=True)
    p.SaveBoard(str(OUT/'checkpoint.kicad_pcb'),b)
    (OUT/'checkpoint-routes.json').write_text(json.dumps(route_evidence,indent=2)+'\n')

def pin_escape(key):
    q=pad(key);net=q.GetNetname()
    pos=xy(q.GetPosition());native_layer=p.B_Cu if fps[key.split('.')[0]].IsFlipped() else p.F_Cu;start=idx(pos,native_layer)
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
            if not (0<=yy<NY and 0<=xx<NX) or masks[nxt] or math.dist(loc(start),loc(nxt))>(15 if key.startswith('J16.') else 5):continue
            if dx and dy and (masks[layer,y,xx] or masks[layer,yy,x]):continue
            nd=dist+weight
            if nd<cost.get(nxt,float('inf')):cost[nxt]=nd;prev[nxt]=node;heapq.heappush(queue,(nd,nxt))
    if goal is None:
        p.SaveBoard(str(OUT/'escape-failure.kicad_pcb'),b)
        np.savez(OUT/'escape-failure.npz',masks=masks,vm=vm,start=start)
        raise RuntimeError('No escape via site: '+key)
    path=[goal]
    while path[-1]!=start:path.append(prev[path[-1]])
    path.reverse();tr(net,[pos,loc(start)],.15,native_layer);emit(net,path,.15);via(net,*loc(goal),.5,.3)
    route_evidence.append(dict(start=key,end='fanout via',net=net,width_mm=.15,trace_length_mm=round(cost[goal]*STEP+math.dist(pos,loc(start)),3),via_xy_mm=loc(goal)))
    print('Pin escape',key,flush=True)



from check_handset_expansion import GROUPS

def checkpoint():
 p.SaveBoard(str(OUT/'checkpoint.kicad_pcb'),b)
 (OUT/'checkpoint-routes.json').write_text(json.dumps(route_evidence,indent=2)+'\n')

# Escape ground pads to an internal plane; signal pads route on their native face.
zone=p.ZONE(b);zone.SetLayer(p.In1_Cu);zone.SetNet(b.FindNet('GND'));zone.SetLocalClearance(p.FromMM(.2));zone.SetThermalReliefGap(p.FromMM(.2));zone.SetThermalReliefSpokeWidth(p.FromMM(.25));zone.SetMinThickness(p.FromMM(.2));zone.SetZoneName('Expansion ground extension');zone.SetAssignedPriority(6)
poly=zone.Outline();poly.NewOutline()
for x,y in [(75.9,81.5),(85.3,81.5),(85.3,106.5),(72,106.5),(72,82.6),(75.9,82.6)]:poly.Append(int(p.FromMM(x)),int(p.FromMM(y)))
if not any(z.GetZoneName()=='Expansion ground extension' for z in b.Zones()):b.Add(zone)
for key in ['R1.2','C1.1','R1.1','U14.1','U14.6']:
 if any(r['start']==key and r['end']=='fanout via' for r in route_evidence):continue
 b.BuildConnectivity()
 if any(i.GetClass() in ('PCB_TRACK','PCB_VIA') for i in b.GetConnectivity().GetConnectedItems(pad(key))):continue
 pin_escape(key);checkpoint()
# Escape the narrow ESD lands before resistor/connector fanout occupies the bay.
for ref,numbers in [('U15',[2,4,1,5,3,8]),('U16',[4,2,1,3,8])]:
 for number in numbers:
  key=ref+'.'+str(number)
  if any(r['start']==key and r['end']=='fanout via' for r in route_evidence):continue
  pin_escape(key);checkpoint()
# Dense IC fanout comes first; later long routes must not enclose unescaped pads.
for ref,numbers in [('U34',[15,16,17,18,19,20,14,13,12,11,10,9,8,7,6,5,4,3,2]),('U33',[1,2,3,4,5,6,8,9,10]),('U35',[1,2,3,4,5,7,9,10,11,12,13,14])]:
 for number in numbers:
  key=ref+'.'+str(number)
  if any(r['start']==key and r['end']=='fanout via' for r in route_evidence):continue
  pin_escape(key);checkpoint()
for ref,numbers in [('R'+str(n),[1,2]) for n in range(20,27)]+[('J16',list(range(1,11)))]:
 for number in numbers:
  key=ref+'.'+str(number)
  if any(r['start']==key and r['end']=='fanout via' for r in route_evidence):continue
  b.BuildConnectivity()
  if any(i.GetClass() in ('PCB_TRACK','PCB_VIA') for i in b.GetConnectivity().GetConnectedItems(pad(key))):continue
  pin_escape(key);checkpoint()
for key in GROUPS['GND'].split()[1:]:
 if not any(r['start']==key and r['end']=='fanout via' for r in route_evidence):
  b.BuildConnectivity()
  if any(i.GetClass()=='PCB_VIA' for i in b.GetConnectivity().GetConnectedItems(pad(key))):continue
  pin_escape(key);checkpoint()
p.ZONE_FILLER(b).Fill(b.Zones())
# Establish module supply backbones before any narrow control branches.
connect('U7.6','U14.1',.3)
connect('U14.1','C40.1',.3)
connect('U14.6','J16.2',.3)
connect('U14.6','C41.1',.3)
# Complete host/connector signals and the remaining power branches.
for net,names in sorted(GROUPS.items(),key=lambda item:item[0] in ('+3V3','EXP_3V3','GND')):
 if net=='GND':continue
 keys=names.split();done=[keys.pop(0)]
 while keys:
  a,z=min(((a,z) for a in done for z in keys),key=lambda pair:math.dist(xy(pad(pair[0]).GetPosition()),xy(pad(pair[1]).GetPosition())))
  width=.3 if net=='EXP_3V3' else .15
  # Control/bleed branches; module supply already has a 0.3 mm backbone.
  if net in ('+3V3','EXP_3V3') and any(key.split('.')[0] in ('R1','R42','R86','R87') for key in (a,z)):width=.15
  connect(a,z,width)
  done.append(z);keys.remove(z)
p.ZONE_FILLER(b).Fill(b.Zones())
# Signal clearances can split small plane islands. Explicitly reconnect them.
for key in GROUPS['GND'].split()[1:]:connect('U7.8',key,.15)
p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'handset.kicad_pcb'),b);shutil.copy2(SOURCE/'handset.kicad_pro',OUT/'handset.kicad_pro')
final=geometry(b)
assert original['footprints']==final['footprints']
assert all(final['copper'].get(k)==v for k,v in original['copper'].items())
(OUT/'expansion-routing.json').write_text(json.dumps(dict(source_hashes=source_hashes,routes=route_evidence,source_copper_items=len(original['copper']),preserved_copper_items=len(original['copper']),added_copper_items=len(final['copper'].keys()-original['copper'].keys()),net_copper_change=len(final['copper'])-len(original['copper']),fabrication_released=False),indent=2)+'\n')
