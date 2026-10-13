#!/usr/bin/env python3
"""Stage CC1101 digital interface; preserve existing routing and RF references."""
import csv,hashlib,heapq,json,math,shutil
from pathlib import Path
import numpy as np
import pcbnew as p
from sync_handset_schematic_rebuild import geometry
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'hardware/handset-rev-a/generated';OUT=Path('/tmp/handset-cc1101-digital')
assert not (SOURCE/'cc1101-digital-routing.json').exists(),'Already installed'
shutil.copytree(SOURCE,OUT,dirs_exist_ok=True,ignore=shutil.ignore_patterns(".history",".git","*.lck","*.prl"))
b=p.LoadBoard(str(SOURCE/'handset.kicad_pcb'));original=geometry(b)
b.BuildConnectivity()
source_pads={q.m_Uuid.AsString():q for f in b.GetFootprints() for q in f.Pads()}
source_groups=[];seen=set()
for uid,q in source_pads.items():
 if uid in seen:continue
 group={v.m_Uuid.AsString() for v in b.GetConnectivity().GetConnectedItems(q)}&source_pads.keys();group.add(uid)
 source_groups.append(group);seen|=group

from cad_sexpr import parse,dump,child
REMOVED=['35934c5e-5c86-40cd-8a19-2eceb7fc531d','70cbd9b9-eb9f-4147-9370-67ac0fcfb38d']
for t in b.GetTracks():
 if t.GetClass()=='PCB_TRACK' and any(tuple(round(p.ToMM(v),4) for v in pos) in [(118.28,39.4),(117.32,39.4)] for pos in (t.GetStart(),t.GetEnd())):REMOVED.append(t.m_Uuid.AsString())
for t in b.GetTracks():
 if t.GetClass()=='PCB_VIA' and tuple(round(p.ToMM(v),4) for v in t.GetPosition())==(117.85,38.7):REMOVED.append(t.m_Uuid.AsString())
 if t.GetClass()=='PCB_TRACK' and any(tuple(round(p.ToMM(v),4) for v in pos)==(117.85,38.7) for pos in (t.GetStart(),t.GetEnd())):REMOVED.append(t.m_Uuid.AsString())
 if t.GetClass()=='PCB_TRACK' and {tuple(round(p.ToMM(v),4) for v in pos) for pos in (t.GetStart(),t.GetEnd())}=={(118.8,38.5),(118.28,39.02)}:REMOVED.append(t.m_Uuid.AsString())
assert len(REMOVED)==8
tree=parse((SOURCE/'handset.kicad_pcb').read_text());tree[:]=[n for n in tree if not (isinstance(n,list) and n and n[0] in ('segment','via') and child(n,'uuid')[1] in REMOVED)]
(OUT/'routing-input.kicad_pcb').write_text(dump(tree)+'\n');b=p.LoadBoard(str(OUT/'routing-input.kicad_pcb'))
fps={f.GetReference():f for f in b.GetFootprints()}
P=lambda xy:p.VECTOR2I(*(p.FromMM(v) for v in xy))
xy=lambda pos:(p.ToMM(pos.x),p.ToMM(pos.y))
X0,Y0,STEP=68.,30.,.05
NX,NY=1281,2801
LAYERS=[p.F_Cu,p.B_Cu,p.In1_Cu,p.In2_Cu]
spi_trunks=False
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
    v.SetFrontTentingMode(p.TENTING_MODE_TENTED)
    v.SetBackTentingMode(p.TENTING_MODE_TENTED)
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
            protected = t.GetNetname() in {'USB_D_N','USB_D_P','USB_HOST_D_N','USB_HOST_D_P'} or t.GetNetname() in {'CC_X1','CC_X2','CC_RF_P','CC_RF_N','CC_BAL_P','CC_BAL_N','CC_SHUNT','CC_MATCH','CC_LPF','CC_DC_BLOCK','CC_RF_50R','SX_TX_MATCH','SX_TX_AC','SX_RX_MATCH','SX_RX_AC','SX_ANT_AC','LORA_RF_50R','SX_TCXO_OUT','SX_TCXO_COUPLED','SX_XTA'}
            capsule(vm, a, z, w / 2 + (0.7 if protected else 0.41))
            if protected and t.GetLayer() in (p.F_Cu,p.B_Cu):
                capsule(masks[2 if t.GetLayer()==p.F_Cu else 3],a,z,w/2+.1+width/2+.25)
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
    # Protect RF/clock reference corridors above, and restrict inner-layer
    # escapes beside the radio. SPI fanout opens below the EP at y=40.7;
    # control fanout opens at y=42. Final return-current review remains open.
    masks[2] |= (yy < (40.7 if spi_trunks and net.startswith('SPI_') else 42)) & (xx > 88) & ~((xx > 90) & (xx < 100) & (yy > 58)) & ~((xx > 117) & (xx < (120.1 if spi_trunks and net.startswith('SPI_') else 119.6)) & (yy > 36.5)) & ~((xx > 117) & (xx < 121) & (yy > 44.5))
    masks[3] |= (yy < (40.7 if spi_trunks and net.startswith('SPI_') else 42)) & (xx > 88) & ~((xx > 90) & (xx < 100) & (yy > 58)) & ~((xx > 117) & (xx < (120.1 if spi_trunks and net.startswith('SPI_') else 119.6)) & (yy > 36.5)) & ~((xx > 117) & (xx < 121) & (yy > 44.5))
    rf = ((xx > 121.25) & (yy < (40.7 if spi_trunks and net=='SPI_SCK' else 44))) | ((xx > 120.7) & (yy < 36.2)) | ((xx > 111.8) & (xx < 116) & (yy < 44))
    masks |= rf[None,:,:]
    vm |= rf
    masks[0] |= (xx > 119.5) & (xx < 123.5) & (yy > 37.2) & (yy < 41.2)
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
        if len(cost) > 500000:
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
            nd = d + step * (3 if layer == 2 else 1)
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

layout={'C12':(117.3,39.4,180,'B')}
for ref,(x,y,a,side) in layout.items():
 f=fps[ref]
 layer=p.F_Cu if side=='F' else p.B_Cu
 if f.GetLayer()!=layer:f.Flip(f.GetPosition(),False)
 f.SetPosition(P((x,y)));f.SetOrientationDegrees(a);f.Reference().SetLayer(p.F_Fab if side=='F' else p.B_Fab)
tr('CC_VDD',[(118.8,38.5),(118.3,38.5),(117.78,39.02),(117.78,39.4)],.2,p.B_Cu)
tr('CC_VDD',[(118.28,40.3),(117.78,40.3),(117.78,39.4)],.25,p.B_Cu)
tr('GND',[(116.82,39.4),(116.5,40.15)],.25,p.B_Cu)
tr('GND',[(117.32,38),(116.5,38.3)],.25,p.B_Cu)
via('GND',116.5,38.3,.5,.3)
via('CC_GDO2',118.65,39.05,.5,.3)
tr('CC_GDO2',[xy(pad('U5.3').GetPosition()),(119.2,39),(118.65,39.05)],.15,p.B_Cu)
routes=[]
def connect(a,z,width=.15):
 pa,pz=pad(a),pad(z);assert pa.GetNetname()==pz.GetNetname()
 metrics=route_points(pa.GetNetname(),xy(pa.GetPosition()),pa.GetParentFootprint().GetLayer(),xy(pz.GetPosition()),pz.GetParentFootprint().GetLayer(),width)
 routes.append(dict(start=a,end=z,net=pa.GetNetname(),width_mm=width,**metrics));print('Connected',a,z,metrics,flush=True);p.SaveBoard(str(OUT/'checkpoint.kicad_pcb'),b)
via('CC_GDO0',119.2,36.8,.5,.3)
tr('CC_GDO0',[xy(pad('U5.6').GetPosition()),(119.4375,37.0375),(119.2,36.8)],.15,p.B_Cu)
via('CC_CS',120.4,36.2,.5,.3)
tr('CC_CS',[xy(pad('U5.7').GetPosition()),(121,36.7),(120.4,36.2)],.15,p.B_Cu)
via('CC_GDO0',95,65.9,.5,.3)
via('CC_CS',95.7,61.8,.5,.3)
metrics=route_points('I2C_SCL',(96.15,61.35),p.In2_Cu,(94.5,63),p.In2_Cu,.15)
routes.append(dict(net='I2C_SCL',start='96.15,61.35',end='94.5,63',**metrics))
metrics=route_points('PANEL_I2C_SCL',(91.85,65.7),p.F_Cu,(97,65.7),p.F_Cu,.15)
routes.append(dict(net='PANEL_I2C_SCL',start='91.85,65.7',end='97,65.7',**metrics));print('Reworked display I2C',metrics,flush=True)
for key,pos in [('U1.24',(95.7,61.8)),('U1.25',(95,65.9))]:
 metrics=route_points(pad(key).GetNetname(),xy(pad(key).GetPosition()),p.B_Cu,pos,p.B_Cu,.15)
 routes.append(dict(net=pad(key).GetNetname(),start=key,end=str(pos),**metrics));print('Host escape',key,metrics,flush=True)
# Reserve the narrow SPI pad escapes before routing any long trunks.
from collections import deque
for key in ['U5.2','U5.1','U5.20']:
 qpad=pad(key);net=qpad.GetNetname();masks,vm=obstacles(net,.15);start=idx(xy(qpad.GetPosition()),p.B_Cu);seen={start};todo=deque([start]);candidates=[]
 while todo:
  node=todo.popleft();layer,y,x=node
  if not vm[y,x] and not masks[0,y,x] and (not masks[2,y,x] or not masks[3,y,x]):candidates.append(node)
  for dy,dx in [(1,0),(-1,0),(0,1),(0,-1)]:
   nxt=(layer,y+dy,x+dx)
   if math.dist(nxt[1:],start[1:])>100:continue
   if 0<=nxt[1]<NY and 0<=nxt[2]<NX and not masks[nxt] and nxt not in seen:seen.add(nxt);todo.append(nxt)
 assert candidates,'No local escape '+key
 target=min(candidates,key=lambda n:math.dist(n[1:],start[1:]));pos=loc(target)
 metrics=route_points(net,xy(qpad.GetPosition()),p.B_Cu,pos,p.B_Cu,.15);via(net,*pos,.5,.3);routes.append(dict(net=net,start=key,end=str(pos),**metrics));print('SPI escape',key,pos,flush=True)
spi_trunks=True
for a,z in [('U5.7','U1.24'),('U5.6','U1.25'),('U5.3','TP1.1'),('U5.7','R12.2'),('R12.1','L11.1'),('U5.20','U1.21'),('U5.2','U1.22'),('U5.1','U1.20')]:connect(a,z)
from route_handset_cc1101_digital_finish import finish_board
b=finish_board(b,OUT,original['copper'])
p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'handset.kicad_pcb'),b);shutil.copy2(SOURCE/'handset.kicad_pro',OUT/'handset.kicad_pro')
b.BuildConnectivity();final_pads={q.m_Uuid.AsString():q for f in b.GetFootprints() for q in f.Pads()}
for group in source_groups:
 uid=next(iter(group));connected={q.m_Uuid.AsString() for q in b.GetConnectivity().GetConnectedItems(final_pads[uid])}|{uid};assert group<=connected
final=geometry(b);assert all(final['copper'][k]==v for k,v in original['copper'].items() if k not in REMOVED);assert all(final['footprints'][k]==v for k,v in original['footprints'].items() if k not in layout)
spec=json.loads((OUT/'connectivity.json').read_text())
for c in spec:
 if c['ref'] in layout:c['x'],c['y'],c['angle'],c['side']=layout[c['ref']]
(OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
with (OUT/'placement.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec)
m=dict(added_copper_uuids=sorted(final["copper"].keys()-original["copper"].keys()),placements=layout,removed_copper=REMOVED,source_board_sha256=hashlib.sha256((SOURCE/'handset.kicad_pcb').read_bytes()).hexdigest(),final_board_sha256=hashlib.sha256((OUT/'handset.kicad_pcb').read_bytes()).hexdigest(),preserved_copper_items=len(original['copper'])-len(REMOVED),added_copper_items=len(final['copper'])-len(original['copper'])+len(REMOVED),routing_searches=routes,route_metrics_note='Search metrics precede local clearance/keepout finishing and removal of redundant escape copper. Measure final added copper using cc1101-digital-checks.json.',fabrication_released=False)
(OUT/'cc1101-digital-routing.json').write_text(json.dumps(m,indent=2)+'\n')
