#!/usr/bin/env python3
"""Stage SX1262 switched RF copper; RF performance remains unqualified."""
import csv,hashlib,json,shutil
from pathlib import Path
import pcbnew as p
from sync_handset_schematic_rebuild import geometry
from cad_sexpr import parse,dump,child
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'hardware/handset-rev-a/generated';OUT=Path('/tmp/handset-sx1262-switch')
P=lambda a:p.VECTOR2I(*(p.FromMM(v) for v in a))
xy=lambda a:(round(p.ToMM(a.x),5),round(p.ToMM(a.y),5))
PLACEMENTS={'U37':(114.15,44.2,90),'C99':(111.9,43.7,0),'C100':(116.2,43.0,270),'C98':(115.0,39.5,90),
 'R91':(115.2,35.0,90),'C96':(109.9,42.8,180),'R93':(109.9,44.0,180),'R92':(117.6,45.8,0),'C97':(118.4,42.0,180)}
def main():
 assert not (SRC/'sx1262-switch-routing.json').exists(),'Already installed'
 shutil.copytree(SRC,OUT,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.history','.git','*.lck','*.prl'))
 b=p.LoadBoard(str(OUT/'handset.kicad_pcb'));before=geometry(b)
 removed={t.m_Uuid.AsString():before['copper'][t.m_Uuid.AsString()] for t in b.GetTracks() if t.GetClass()=='PCB_TRACK' and t.GetNetname()=='+3V3' and t.GetLayer()==p.F_Cu and (xy(t.GetStart()) in [(116.2,36.25),(116.2,44)] or xy(t.GetEnd()) in [(116.2,36.25),(116.2,44)])}
 assert len(removed)==3
 for t in b.GetTracks():
  if (115.6,34.1) in (xy(t.GetStart()),xy(t.GetEnd())):
   assert t.GetNetname()=='GND';removed[t.m_Uuid.AsString()]=before['copper'][t.m_Uuid.AsString()]
 assert len(removed)==5
 tree=parse((OUT/'handset.kicad_pcb').read_text());tree[:]=[v for v in tree if not(isinstance(v,list) and v[0] in ('segment','via') and str(child(v,'uuid')[1]) in removed)]
 (OUT/'handset.kicad_pcb').write_text(dump(tree)+'\n');b=p.LoadBoard(str(OUT/'handset.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()}
 for ref,(x,y,angle) in PLACEMENTS.items():
  f=fps[ref];assert f.GetLayer()==p.F_Cu;f.SetPosition(P((x,y)));f.SetOrientationDegrees(angle);f.Reference().SetLayer(p.F_Fab)
 def pad(key):
  ref,pin=key.split('.');return xy(next(q for q in fps[ref].Pads() if q.GetNumber()==pin).GetPosition())
 def tr(net,points,width=.15,layer=p.F_Cu):
  for a,z in zip(points,points[1:]):
   if a==z:continue
   t=p.PCB_TRACK(b);t.SetStart(P(a));t.SetEnd(P(z));t.SetWidth(p.FromMM(width));t.SetLayer(layer);t.SetNet(b.FindNet(net));b.Add(t)
 def via(net,pos):
  v=p.PCB_VIA(b);v.SetPosition(P(pos));v.SetWidth(p.FromMM(.5));v.SetDrill(p.FromMM(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet(net));v.SetFrontTentingMode(p.TENTING_MODE_TENTED);v.SetBackTentingMode(p.TENTING_MODE_TENTED);b.Add(v)
 tr('+3V3',[(114.5,36.25),(117.2,36.25),(117.2,43.5),(117.7,44),(114.9,46.8),(113.4,46.8)],.5)
 tr('GND',[(115.6,32.32),(115.6,33.6)],.25,p.B_Cu);via('GND',(115.6,33.6))
 # Matched outputs leave the rear IPD through one transition each.
 tr('SX_TX_MATCH',[pad('U36.8'),(113.65,42.7),(113.4,43.0)],.2,p.B_Cu);via('SX_TX_MATCH',(113.4,43.0))
 tr('SX_TX_MATCH',[(113.4,43.0),(112.12,43.0),pad('C99.1')],.34)
 tr('SX_RX_MATCH',[pad('U36.6'),(115.3,42.5),(115.3,42.6)],.2,p.B_Cu);via('SX_RX_MATCH',(115.3,42.6))
 tr('SX_RX_MATCH',[(115.3,42.6),(115.38,42.52),pad('C100.1')],.34)
 tr('SX_TX_AC',[pad('C99.2'),(112.38,44.5),(112.48,44.6),(113.35,44.6)],.34)
 tr('SX_TX_AC',[(113.35,44.6),pad('U37.1')])
 tr('SX_RX_AC',[pad('C100.2'),(116.2,44.4),(114.95,44.4)],.34)
 tr('SX_RX_AC',[(114.95,44.4),pad('U37.3')])
 tr('SX_ANT_AC',[pad('U37.5'),(114.15,42.6),(114.4,41.95)],.15)
 tr('SX_ANT_AC',[(114.4,41.95),(115.0,41.55),pad('C98.1')],.34)
 tr('LORA_RF_50R',[pad('C98.2'),(115.0,38.3)],.34);via('LORA_RF_50R',(115.0,38.3))
 tr('LORA_RF_50R',[(115.0,38.3),(115.7,37.6),(115.7,36.3),(116.55,35.45),(116.55,34.05),(116.975,33.625),pad('J20.1')],.34,p.B_Cu)
 # DIO2 filter and default-RX pull-down use inner-layer control copper.
 tr('SX_RF_SW',[pad('U4.12'),(114.25,34.3),(115.4,34.3),(115.8,34.7),(115.8,35.1)],.15,p.B_Cu);via('SX_RF_SW',(115.8,35.1))
 tr('SX_RF_SW',[(115.8,35.1),(115.8,35.51),pad('R91.1')])
 tr('SX_SWITCH_CTRL',[pad('R91.2'),(118.5,34.49),(118.5,35.8),(118.0,36.3)]);via('SX_SWITCH_CTRL',(118.0,36.3))
 via('SX_SWITCH_CTRL',(110.38,42.1));via('SX_SWITCH_CTRL',(113.25,43.75))
 tr('SX_SWITCH_CTRL',[(118.0,36.3),(118.0,35.7),(111.5,35.7),(111.5,40.98),(110.38,42.1)],.15,p.In1_Cu)
 tr('SX_SWITCH_CTRL',[(110.38,42.1),(110.38,44.8),(112.3,44.8),(113.25,43.75)],.15,p.In2_Cu)
 tr('SX_SWITCH_CTRL',[(110.38,42.1),pad('C96.1'),pad('R93.1')])
 tr('SX_SWITCH_CTRL',[(113.25,43.75),pad('U37.6')])
 # Dedicated filtered supply; retain the established main rail geometry.
 tr('+3V3',[(115.9,45.8),pad('R92.1')],.25)
 tr('SX_SWITCH_VDD',[pad('R92.2'),(118.9,45.01),(118.9,42.8),pad('C97.1')],.2)
 via('SX_SWITCH_VDD',(118.9,42.8));via('SX_SWITCH_VDD',(115.15,43.55))
 tr('SX_SWITCH_VDD',[(118.9,42.8),(118.9,43.4),(118.3,44),(115.05,44),(115.15,43.55)],.2,p.In2_Cu)
 tr('SX_SWITCH_VDD',[(115.15,43.55),pad('U37.4')])
 # Ground pins and close returns at each RF layer change.
 for key,pos in [('C96.2',(107.7,42.8)),('R93.2',(107.7,44.0)),('C97.2',(117.92,42.8)),('U37.2',(114.15,45.1))]:
  tr('GND',[pad(key),pos],.15 if key=='U37.2' else .25);via('GND',pos)
 for pos in [(111.6,42.0),(115.65,41.8),(115.7,38.7),(116.8,32.5)]:via('GND',pos)
 for q in fps['J20'].Pads():
  if q.GetNumber()=='2':
   pos=xy(q.GetPosition());end=(pos[0]+1.5,pos[1]);tr('GND',[pos,end],.4,p.B_Cu);via('GND',end)
 # Reference ground on both adjacent internal layers; subtract existing zones.
 for layer in (p.In1_Cu,p.In2_Cu):
  z=p.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet('GND'));z.SetZoneName('SX1262 switch return');z.SetLocalClearance(p.FromMM(.2));z.SetMinThickness(p.FromMM(.2));z.SetAssignedPriority(9);z.SetPadConnection(p.ZONE_CONNECTION_FULL)
  poly=z.Outline();poly.NewOutline()
  for a in [(107,32),(120.3,32),(120.3,47),(107,47)]:poly.Append(P(a).x,P(a).y)
  for other in b.Zones():
   if not other.GetIsRuleArea() and other.GetLayer()==layer:poly.BooleanSubtract(other.Outline())
  b.Add(z)
 p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
 shutil.copy2(SRC/'handset.kicad_pro',OUT/'handset.kicad_pro')
 after=geometry(b);assert all(after['copper'][k]==v for k,v in before['copper'].items() if k not in removed);assert all(after['footprints'][k]==v for k,v in before['footprints'].items() if k not in PLACEMENTS)
 spec=json.loads((OUT/'connectivity.json').read_text())
 for c in spec:
  if c['ref'] in PLACEMENTS:
   f=fps[c['ref']];c.update(x=xy(f.GetPosition())[0],y=xy(f.GetPosition())[1],side='F',angle=f.GetOrientationDegrees())
 (OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
 with (OUT/'placement.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec)
 report=dict(source_board_sha256=hashlib.sha256((SRC/'handset.kicad_pcb').read_bytes()).hexdigest(),final_board_sha256=hashlib.sha256((OUT/'handset.kicad_pcb').read_bytes()).hexdigest(),placements=PLACEMENTS,removed_copper=removed,preserved_copper_items=len(before['copper'])-len(removed),added_copper_items=len(after['copper'])-len(before['copper'])+len(removed),preserved_footprints=len(before['footprints'])-len(PLACEMENTS),fabrication_released=False)
 (OUT/'sx1262-switch-routing.json').write_text(json.dumps(report,indent=2)+'\n');print(OUT)
if __name__=='__main__':main()
