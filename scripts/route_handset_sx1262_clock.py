#!/usr/bin/env python3
"""Route the staged TCXO with a back-layer clock path and local inner returns."""
import hashlib,json,shutil
from pathlib import Path
import pcbnew as p
from sync_handset_schematic_rebuild import geometry
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'hardware/handset-rev-a/generated'
OUT=Path('/tmp/handset-sx1262-clock')
b=p.LoadBoard(str(OUT/'handset.kicad_pcb'));before=geometry(b)
assert not any(t.GetNetname()=='SX_TCXO_OUT' for t in b.GetTracks()),'Clock already routed'
P=lambda xy:p.VECTOR2I(*(p.FromMM(v) for v in xy))
def track(net,points,width=.15,layer=p.B_Cu):
 for a,z in zip(points,points[1:]):
  t=p.PCB_TRACK(b);t.SetStart(P(a));t.SetEnd(P(z));t.SetWidth(p.FromMM(width));t.SetLayer(layer);t.SetNet(b.FindNet(net));b.Add(t)
def via(net,pos):
 v=p.PCB_VIA(b);v.SetPosition(P(pos));v.SetWidth(p.FromMM(.5));v.SetDrill(p.FromMM(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet(net));b.Add(v)
# No vias or branches in the oscillator output / series R / series C / XTA path.
track('SX_TCXO_OUT',[(112.2,39.8),(109.91,39.8)])
track('SX_TCXO_COUPLED',[(108.89,39.8),(108.89,38.63),(108.92,38.6)])
track('SX_XTA',[(109.88,38.6),(110.3,38.18),(110.3,36.25),(111.0625,36.25)])
# DIO3 supplies only the TCXO and its local bypass. Keep supply off clock layer near U4.
track('SX_TCXO_PWR',[(111.0625,34.75),(109.9,34.75)])
via('SX_TCXO_PWR',(109.9,34.75))
track('SX_TCXO_PWR',[(109.9,34.75),(110.2,34.45),(110.2,33.2),(115.6,33.2),(116.2,33.8),(116.2,38.0)],.2,p.F_Cu)
via('SX_TCXO_PWR',(116.2,38.0))
track('SX_TCXO_PWR',[(116.2,38.0),(116.2,38.82),(116.02,39),(115.2,39.8),(114.4,39.8)],.2)
track('GND',[(112.2,41.4),(114.4,41.4),(114.4,42.5)],.3)
via('GND',(114.4,42.5))
track('GND',[(116.98,39),(117.1,38.88),(117.1,38.0)],.25)
via('GND',(117.1,38.0))
track('GND',[(111.0625,35.25),(110.5,35.25),(109.9,35.55)],.2)
via('GND',(109.9,35.55))
for layer in (p.In1_Cu,p.In2_Cu):
 zone=p.ZONE(b);zone.SetLayer(layer);zone.SetNet(b.FindNet('GND'));zone.SetZoneName('SX1262 clock return')
 zone.SetLocalClearance(p.FromMM(.2));zone.SetMinThickness(p.FromMM(.2));zone.SetAssignedPriority(10);zone.SetPadConnection(p.ZONE_CONNECTION_FULL)
 poly=zone.Outline();poly.NewOutline()
 for point in [(107.5,33.2),(117.4,33.2),(117.4,44),(107.5,44)]:poly.Append(int(p.FromMM(point[0])),int(p.FromMM(point[1])))
 for existing in b.Zones():
  if not existing.GetIsRuleArea() and existing.GetLayer()==layer:poly.BooleanSubtract(existing.Outline())
 b.Add(zone)
p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
shutil.copy2(SRC/'handset.kicad_pro',OUT/'handset.kicad_pro')
after=geometry(b);assert before['footprints']==after['footprints']
for ident,item in before['copper'].items():assert after['copper'][ident]==item
m=json.loads((OUT/'sx1262-clock-update.json').read_text())
m.update(added_copper_items=len(after['copper'])-len(before['copper']),added_ground_zones=2,
 final_board_sha256=hashlib.sha256((OUT/'handset.kicad_pcb').read_bytes()).hexdigest(),
 scope='TCXO schematic, placement and local copper; RF frontend, remaining radio supply/ground and qualification remain open')
(OUT/'sx1262-clock-update.json').write_text(json.dumps(m,indent=2)+'\n')
print('Staged clock routing')
