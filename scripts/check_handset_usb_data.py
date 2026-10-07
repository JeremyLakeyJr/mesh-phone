#!/usr/bin/env python3
"""Check actual USB pin polarity, copper, path balance and filled reference planes.

These checks do not certify impedance, ESD immunity or USB electrical compliance.
"""
import heapq,itertools,json,math,sys
from pathlib import Path
import pcbnew as p
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
GROUPS={
 'USB_D_N':'USB1.A7 USB1.B7 U17.1 U17.10 R88.2',
 'USB_D_P':'USB1.A6 USB1.B6 U17.2 U17.9 R89.2',
 'USB_HOST_D_N':'U1.13 R88.1', 'USB_HOST_D_P':'U1.14 R89.1',
 'GND':'U1.1 U17.3 U17.8',
}
RETURN_VIAS=[(106.5,49.1),(107.4,51.6),(128.2,54.75),(129.4,54.8),(124.2,51.5),(124.4,52.8)]
xy=lambda q:(round(p.ToMM(q.x),6),round(p.ToMM(q.y),6))

def distances(board,pads,net,start,ends):
 """Shortest planar copper path, with explicit external copper across ESD NC lands.

Pad interiors join track endpoints; barrel length is excluded and via count is
checked separately. Resistor bodies and the module's internal traces are excluded.
 """
 graph={}
 def edge(a,z,d):
  graph.setdefault(a,[]).append((z,d));graph.setdefault(z,[]).append((a,d))
 for t in board.GetTracks():
  if t.GetNetname()!=net:continue
  if isinstance(t,p.PCB_VIA):edge((*xy(t.GetPosition()),p.F_Cu),(*xy(t.GetPosition()),p.B_Cu),0)
  else:edge((*xy(t.GetStart()),t.GetLayer()),(*xy(t.GetEnd()),t.GetLayer()),p.ToMM(t.GetLength()))
 for name,q in pads.items():
  if q.GetNetname()!=net:continue
  for layer in (p.F_Cu,p.B_Cu):
   if not q.IsOnLayer(layer):continue
   poly=q.GetEffectivePolygon(layer,p.ERROR_OUTSIDE)
   for node in list(graph):
    if isinstance(node,tuple) and node[2]==layer and poly.Contains(p.VECTOR2I(p.FromMM(node[0]),p.FromMM(node[1]))):edge(name,node,math.dist(xy(q.GetPosition()),node[:2]))
 counter=itertools.count();costs={start:0};todo=[(0,next(counter),start)]
 while todo:
  d,_,node=heapq.heappop(todo)
  if d>costs[node]:continue
  for other,w in graph.get(node,[]):
   if d+w<costs.get(other,math.inf):costs[other]=d+w;heapq.heappush(todo,(d+w,next(counter),other))
 return {name:round(costs[name],6) if name in costs else None for name in ends}

def inspect(board):
 board.BuildConnectivity();checks=[]
 pads={f.GetReference()+'.'+q.GetNumber():q for f in board.GetFootprints() for q in f.Pads() if q.GetNumber()}
 def check(name,ok):checks.append(dict(check=name,passed=bool(ok)))
 for net,names in GROUPS.items():
  names=names.split();present=all(n in pads for n in names);check(net+' required pads present',present)
  if not present:continue
  seed=pads[names[0]];items=list(board.GetConnectivity().GetConnectedItems(seed));ids={q.m_Uuid.AsString() for q in items}|{seed.m_Uuid.AsString()}
  check(net+' pin assignment',all(pads[n].GetNetname()==net for n in names))
  check(net+' physical continuity',all(pads[n].m_Uuid.AsString() in ids for n in names))
  check(net+' no foreign copper net',all(q.GetNetname()==net for q in items))
 for ref in ('R88','R89'):
  f=next((f for f in board.GetFootprints() if f.GetReference()==ref),None)
  check(ref+' populated 22 ohm termination',f and f.GetValue()=='22 1%' and not f.IsDNP())
 results={}
 for net,start,ends in [('USB_D_N','R88.2',['USB1.A7','USB1.B7','U17.1']),('USB_D_P','R89.2',['USB1.A6','USB1.B6','U17.2']),('USB_HOST_D_N','R88.1',['U1.13']),('USB_HOST_D_P','R89.1',['U1.14'])]:results[net]=distances(board,pads,net,start,ends)
 check('all copper graph paths exist',all(v is not None for r in results.values() for v in r.values()))
 totals={};skews={}
 if checks[-1]['passed']:
  for orientation,n,pin in [('A','A7','A6'),('B','B7','B6')]:
   minus=results['USB_D_N']['USB1.'+n]+results['USB_HOST_D_N']['U1.13'];plus=results['USB_D_P']['USB1.'+pin]+results['USB_HOST_D_P']['U1.14']
   totals[orientation]={'N':round(minus,6),'P':round(plus,6)};skews[orientation]=round(abs(minus-plus),6)
   check('orientation '+orientation+' planar skew <= 0.25 mm',abs(minus-plus)<=.25)
  for net,pins in [('USB_D_N',['USB1.A7','USB1.B7']),('USB_D_P',['USB1.A6','USB1.B6'])]:check(net+' orientation branches balanced',abs(results[net][pins[0]]-results[net][pins[1]])<=.05)
 signal_vias=[t for t in board.GetTracks() if isinstance(t,p.PCB_VIA) and t.GetNetname() in ('USB_D_N','USB_D_P')]
 via_counts={net:sum(t.GetNetname()==net for t in signal_vias) for net in ('USB_D_N','USB_D_P')}
 check('three through vias per data leg',all(count==3 for count in via_counts.values()) and all(t.TopLayer()==p.F_Cu and t.BottomLayer()==p.B_Cu for t in signal_vias))
 seed=pads['U1.1'];ground_ids={q.m_Uuid.AsString() for q in board.GetConnectivity().GetConnectedItems(seed)}|{seed.m_Uuid.AsString()}
 ground_vias=[t for t in board.GetTracks() if isinstance(t,p.PCB_VIA) and t.GetNetname()=='GND' and t.m_Uuid.AsString() in ground_ids]
 for point in RETURN_VIAS:check('ground return via '+str(point),any(math.dist(xy(v.GetPosition()),point)<1e-5 for v in ground_vias))
 for t in signal_vias:
  nearest=sorted(math.dist(xy(t.GetPosition()),xy(g.GetPosition())) for g in ground_vias)
  check(t.GetNetname()+' two ground vias within 2.5 mm at '+str(xy(t.GetPosition())),len(nearest)>=2 and nearest[1]<=2.5)
 # Sample the centerline and both trace edges with 0.10 mm extra reference margin.
 # Only local antipads within 0.65 mm of a signal via are exempted; record them.
 planes={layer:[z.GetFilledPolysList(layer) for z in board.Zones() if z.GetNetname()=='GND' and z.IsOnLayer(layer)] for layer in (p.In1_Cu,p.In2_Cu)}
 misses=[];exempt=0;samples=0
 for t in board.GetTracks():
  if t.GetNetname() not in ('USB_D_N','USB_D_P','USB_HOST_D_N','USB_HOST_D_P') or isinstance(t,p.PCB_VIA):continue
  check('outer layer trace '+t.m_Uuid.AsString(),t.GetLayer() in (p.F_Cu,p.B_Cu))
  ref=p.In1_Cu if t.GetLayer()==p.F_Cu else p.In2_Cu;a,z=xy(t.GetStart()),xy(t.GetEnd());length=math.dist(a,z)
  if length==0:continue
  steps=max(1,math.ceil(length/.1));nx=-(z[1]-a[1])/length;ny=(z[0]-a[0])/length;radius=p.ToMM(t.GetWidth())/2+.1
  for i in range(steps+1):
   for offset in (-radius,0,radius):
    point=(a[0]+(z[0]-a[0])*i/steps+nx*offset,a[1]+(z[1]-a[1])*i/steps+ny*offset);samples+=1
    if any(poly.Contains(p.VECTOR2I(p.FromMM(point[0]),p.FromMM(point[1]))) for poly in planes[ref]):continue
    if any(math.dist(point,xy(v.GetPosition()))<=.65 for v in signal_vias):exempt+=1
    else:misses.append(dict(net=t.GetNetname(),layer=board.GetLayerName(t.GetLayer()),position_mm=[round(v,4) for v in point]))
 check('filled reference corridor outside via antipads',not misses)
 return dict(passed=all(c['passed'] for c in checks),checks=checks,planar_path_lengths_mm=results,connector_to_module_planar_mm=totals,skew_mm=skews,signal_via_counts=via_counts,reference_samples=samples,via_antipad_exempt_samples=exempt,reference_gaps=misses,fabrication_released=False,scope='CAD connectivity, planar path balance and sampled filled ground corridor; excludes barrel delay, module internals, component parasitics, fabrication tolerances and electrical compliance')

if __name__=='__main__':
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT;report=inspect(p.LoadBoard(str(out/'handset.kicad_pcb')));(out/'usb-data-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));sys.exit(not report['passed'])
