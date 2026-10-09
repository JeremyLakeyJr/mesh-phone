#!/usr/bin/env python3
"""Stage TCXO relocation and local PA/RF input copper; preserve other circuits."""
import csv,hashlib,json,shutil
from pathlib import Path
import pcbnew as p
from cad_sexpr import parse,dump,child
from sync_handset_schematic_rebuild import geometry
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'hardware/handset-rev-a/generated'
OUT=Path('/tmp/handset-sx1262-local-rf')
P=lambda a:p.VECTOR2I(*(p.FromMM(v) for v in a))
xy=lambda a:(round(p.ToMM(a.x),5),round(p.ToMM(a.y),5))

def main():
 assert not (SRC/'sx1262-local-rf-routing.json').exists(),'Already installed'
 shutil.copytree(SRC,OUT,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.history','.git','*.lck','*.prl'))
 original=p.LoadBoard(str(SRC/'handset.kicad_pcb'));before=geometry(original)
 # Remove only explicitly identified clock copper and the local VDD_IN escape.
 # S-expression removal avoids pcbnew SWIG ownership issues.
 clocknets={'SX_TCXO_OUT','SX_TCXO_COUPLED','SX_XTA','SX_TCXO_PWR'}
 ground_pairs={frozenset(pair) for pair in [((112.2,41.4),(114.4,41.4)),((114.4,41.4),(114.4,42.5)),
                  ((116.98,39),(117.1,38.88)),((117.1,38.88),(117.1,38.0))]}
 supply_pairs={frozenset(pair) for pair in [((111.0625,37.25),(111.0625,38.5625)),((111.0625,38.5625),(111.15,38.65))]}
 removed={}
 for t in original.GetTracks():
  net=t.GetNetname();via=t.GetClass()=='PCB_VIA';a,z=xy(t.GetStart()),xy(t.GetEnd())
  remove=net in clocknets
  remove|=net=='GND' and ((not via and frozenset((a,z)) in ground_pairs) or (via and a in [(114.4,42.5),(117.1,38.0)]))
  remove|=net=='+3V3' and ((not via and (frozenset((a,z)) in supply_pairs or (t.GetLayer()==p.F_Cu and (111.15,38.65) in (a,z)))) or (via and a==(111.15,38.65)))
  if remove:removed[t.m_Uuid.AsString()]=before['copper'][t.m_Uuid.AsString()]
 tree=parse((SRC/'handset.kicad_pcb').read_text())
 tree[:]=[v for v in tree if not(isinstance(v,list) and v[0] in ['segment','via'] and str(child(v,'uuid')[1]) in removed)]
 (OUT/'handset.kicad_pcb').write_text(dump(tree)+'\n');b=p.LoadBoard(str(OUT/'handset.kicad_pcb'))
 fps={f.GetReference():f for f in b.GetFootprints()}
 placements={
  'Y3':(105.3,38.8,0),'R90':(108.45,41.0,0),'C94':(102.2,39.5,180), 'J25':(103,33.7,0),
  'R49':(101,38.4,0),'C44':(98.8,38.6,0),'R10':(116.8,37.0,0),
  'L13':(111.65,39.55,270),'C10':(110.5,41.1,180),'C101':(110.2,39.85,180),
  'U36':(113.9,41.15,270),
 }
 for ref,(x,y,angle) in placements.items():
  f=fps[ref]
  if f.GetLayer()!=p.B_Cu:f.Flip(f.GetPosition(),False)
  f.SetPosition(P((x,y)));f.SetOrientationDegrees(angle)
  f.Reference().SetLayer(p.B_Fab)
 def tr(net,points,width=.2,layer=p.B_Cu):
  for a,z in zip(points,points[1:]):
   if a==z:continue
   t=p.PCB_TRACK(b);t.SetStart(P(a));t.SetEnd(P(z));t.SetWidth(p.FromMM(width));t.SetLayer(layer);t.SetNet(b.FindNet(net));b.Add(t)
 def via(net,point):
  v=p.PCB_VIA(b);v.SetPosition(P(point));v.SetWidth(p.FromMM(.5));v.SetDrill(p.FromMM(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet(net));b.Add(v)
 def pad(key):
  ref,pin=key.split('.');return xy(next(q for q in fps[ref].Pads() if q.GetNumber()==pin).GetPosition())
 # TCXO output stays on B.Cu and contains no signal vias.
 tr('SX_TCXO_OUT',[pad('Y3.3'),(107.0,39.6),(107.0,40.06),pad('R90.1')],.15)
 tr('SX_TCXO_COUPLED',[pad('R90.2'),(108.96,38.64),pad('C95.1')],.15)
 tr('SX_XTA',[pad('C95.2'),(110.3,38.18),(110.3,36.25),pad('U4.3')],.15)
 tr('SX_TCXO_PWR',[pad('U4.6'),(109.9,34.75)],.2);via('SX_TCXO_PWR',(109.9,34.75))
 tr('SX_TCXO_PWR',[(109.9,34.75),(109.3,34.75),(108.65,35.4),(105.8,35.4),(105.8,38.8),(103.3,40.1)],.2,p.In1_Cu)
 via('SX_TCXO_PWR',(103.3,40.1))
 tr('SX_TCXO_PWR',[(103.3,40.1),(103.3,39.6),pad('Y3.4')],.2)
 tr('SX_TCXO_PWR',[pad('C94.1'),(103.3,39.6)],.2)
 tr('GND',[pad('Y3.1'),pad('Y3.2'),(106.4,36.95)],.3);via('GND',(106.4,36.95))
 tr('GND',[pad('C94.2'),(101.2,39.5)],.25);via('GND',(101.2,39.5))
 # Pull the VDD_IN via out of the PA area; the established front feed remains.
 tr('+3V3',[pad('U4.1'),(110.95,37.3625),(110.95,37.95)],.2);via('+3V3',(110.95,37.95))
 # Recover the preserved endpoint of the removed front-layer feed segment.
 feed=[v for v in removed.values() if v[0]=='PCB_TRACK' and v[6]==p.F_Cu and v[7]=='+3V3']
 assert len(feed)==1,feed
 item=feed[0];ends=[(p.ToMM(item[1]),p.ToMM(item[2])),(p.ToMM(item[3]),p.ToMM(item[4]))]
 anchor=next(a for a in ends if a!=(111.15,38.65))
 tr('+3V3',[anchor,(110.95,37.95)],.3,p.F_Cu)
 # Local PA feed and bypass. Matching-device outputs remain intentionally open.
 tr('SX_VR_PA',[pad('U4.24'),(111.75,38.45),(111.65,38.55),pad('L13.1')],.2)
 tr('SX_VR_PA',[pad('L13.1'),(110.68,39.065),pad('C101.1'),pad('C10.1')],.2)
 tr('SX_RFO',[pad('U4.23'),(112.25,38.8),(113.15,39.7),pad('U36.1')],.2)
 tr('SX_RFO',[pad('L13.2'),(112.69,40.06),pad('U36.1')],.2)
 tr('SX_RFI_N',[pad('U4.22'),(112.75,38.45),(114.15,39.85),pad('U36.3')],.2)
 tr('SX_RFI_P',[pad('U4.21'),(113.25,38.45),(114.65,39.85),pad('U36.4')],.2)
 tr('GND',[pad('C101.2'),(109.9,39.85),(109.9,40.4),pad('C10.2')],.25)
 via('GND',(109.9,40.4))
 # Extend the clock ground reference over its relocated corridor, retaining
 # existing zones and their exclusions. RF ground geometry is still unfinished.
 for layer in (p.In1_Cu,p.In2_Cu):
  zone=p.ZONE(b);zone.SetLayer(layer);zone.SetNet(b.FindNet('GND'));zone.SetZoneName('SX1262 clock return')
  zone.SetLocalClearance(p.FromMM(.2));zone.SetMinThickness(p.FromMM(.2));zone.SetAssignedPriority(11);zone.SetPadConnection(p.ZONE_CONNECTION_FULL)
  poly=zone.Outline();poly.NewOutline()
  for a in [(101,36.5),(109.5,36.5),(109.5,42),(101,42)]:poly.Append(P(a).x,P(a).y)
  for existing in b.Zones():
   if not existing.GetIsRuleArea() and existing.GetLayer()==layer:poly.BooleanSubtract(existing.Outline())
  b.Add(zone)
 p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
 after=geometry(b)
 assert all(after['copper'][k]==v for k,v in before['copper'].items() if k not in removed)
 assert all(after['footprints'][k]==v for k,v in before['footprints'].items() if k not in placements)
 spec=json.loads((OUT/'connectivity.json').read_text())
 for c in spec:
  if c['ref'] in placements:
   f=fps[c['ref']];c.update(x=xy(f.GetPosition())[0],y=xy(f.GetPosition())[1],side='B',angle=f.GetOrientationDegrees())
 (OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
 with (OUT/'placement.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec)
 report=dict(source_board_sha256=hashlib.sha256((SRC/'handset.kicad_pcb').read_bytes()).hexdigest(),
  final_board_sha256=hashlib.sha256((OUT/'handset.kicad_pcb').read_bytes()).hexdigest(),moved_refs=list(placements),
  removed_copper=removed,preserved_copper_items=len(before['copper'])-len(removed),added_copper_items=len(after['copper'])-len(before['copper'])+len(removed),
  fabrication_released=False,scope='TCXO relocation and local PA/RF input copper; switch/antenna and RF grounding qualification remain open')
 (OUT/'sx1262-local-rf-routing.json').write_text(json.dumps(report,indent=2)+'\n');print(OUT)
if __name__=='__main__':main()
