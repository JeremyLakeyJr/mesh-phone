#!/usr/bin/env python3
"""Stage grounded SX1262 IPD with a bounded 0.2mm drilled-via rule."""
import hashlib,json,math,shutil
from pathlib import Path
import pcbnew as p
from cad_sexpr import parse,dump,child
from sync_handset_schematic_rebuild import geometry
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'hardware/handset-rev-a/generated';OUT=Path('/tmp/handset-sx1262-rf-ground')
AREA='SX1262 RF grounding'
VIA_POS={'2':(113.65,41.0),'5':(115.55,41.15),'7':(114.15,41.25),'9':(113.15,42.4),'10':(112.25,41.15)}
RULES='''(version 1)
# Retain the previous general limits while allowing only the RF GND exception.
(rule "General drilled holes"
  (constraint hole_size (min 0.3mm)))
(rule "General vias"
  (condition "A.Type == 'Via'")
  (constraint via_diameter (min 0.5mm)))
(rule "SX1262 RF ground vias"
  (condition "A.Type == 'Via' && A.NetName == 'GND' && A.enclosedByArea('SX1262 RF grounding')")
  (constraint hole_size (min 0.2mm) (max 0.2mm))
  (constraint via_diameter (min 0.45mm) (max 0.45mm)))
'''
P=lambda a:p.VECTOR2I(*(p.FromMM(v) for v in a))
xy=lambda a:(round(p.ToMM(a.x),5),round(p.ToMM(a.y),5))

def main():
 assert not (SRC/'sx1262-rf-ground-routing.json').exists(),'Already installed'
 assert not (SRC/'handset.kicad_dru').exists(),'Merge existing rules explicitly'
 shutil.copytree(SRC,OUT,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.history','.git','*.lck','*.prl'))
 old=p.LoadBoard(str(SRC/'handset.kicad_pcb'));before=geometry(old)
 selected=[t for t in old.GetTracks() if t.GetClass()=='PCB_TRACK' and t.GetNetname()=='+3V3' and t.GetLayer()==p.F_Cu and {xy(t.GetStart()),xy(t.GetEnd())}=={(113.4,35.15),(113.4,49.25)}]
 assert len(selected)==1;replaced=selected[0];assert round(p.ToMM(replaced.GetWidth()),4)==.5
 ident=replaced.m_Uuid.AsString()
 tree=parse((SRC/'handset.kicad_pcb').read_text());tree[:]=[v for v in tree if not(isinstance(v,list) and v[0]=='segment' and str(child(v,'uuid')[1])==ident)]
 (OUT/'handset.kicad_pcb').write_text(dump(tree)+'\n')
 project=json.loads((SRC/'handset.kicad_pro').read_text());rules=project['board']['design_settings']['rules']
 assert rules['min_through_hole_diameter']==.3 and rules['min_via_diameter']==.5
 rules['min_through_hole_diameter']=.2;rules['min_via_diameter']=.45
 netsettings=project['net_settings']
 netsettings['classes'].append(dict(name='RF 50 ohm target',priority=1,clearance=.15,track_width=.34,via_diameter=.5,via_drill=.3))
 for net in ['SX_TX_MATCH','SX_TX_AC','SX_RX_MATCH','SX_RX_AC','SX_ANT_AC','LORA_RF_50R']:
  netsettings['netclass_patterns'].append(dict(netclass='RF 50 ohm target',pattern=net))
 (OUT/'handset.kicad_pro').write_text(json.dumps(project,indent=2)+'\n');(OUT/'handset.kicad_dru').write_text(RULES)
 b=p.LoadBoard(str(OUT/'handset.kicad_pcb'))
 def tr(net,points,width,layer=p.B_Cu):
  for a,z in zip(points,points[1:]):
   if a==z:continue
   t=p.PCB_TRACK(b);t.SetStart(P(a));t.SetEnd(P(z));t.SetWidth(p.FromMM(width));t.SetLayer(layer);t.SetNet(b.FindNet(net));b.Add(t)
 feed=[(113.4,35.15),(114.5,36.25),(116.2,36.25),(116.2,44),(113.4,46.8),(113.4,49.25)]
 tr('+3V3',feed,.5,p.F_Cu)
 f=next(f for f in b.GetFootprints() if f.GetReference()=='U36');pads={q.GetNumber():q for q in f.Pads()}
 vias=[]
 for pin,pos in VIA_POS.items():
  tr('GND',[xy(pads[pin].GetPosition()),pos],.25)
  v=p.PCB_VIA(b);v.SetPosition(P(pos));v.SetWidth(p.FromMM(.45));v.SetDrill(p.FromMM(.2));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet('GND'))
  v.SetFrontTentingMode(p.TENTING_MODE_TENTED);v.SetBackTentingMode(p.TENTING_MODE_TENTED);b.Add(v)
  vias.append(dict(pin=pin,position_mm=pos,uuid=v.m_Uuid.AsString()))
 def rectangle(zone,points):
  poly=zone.Outline();poly.NewOutline()
  for point in points:poly.Append(P(point).x,P(point).y)
 area=p.ZONE(b);area.SetLayer(p.B_Cu);area.SetIsRuleArea(True);area.SetZoneName(AREA)
 for method in ['SetDoNotAllowTracks','SetDoNotAllowVias','SetDoNotAllowPads','SetDoNotAllowFootprints','SetDoNotAllowZoneFills']:getattr(area,method)(False)
 rectangle(area,[(112.0,40.7),(115.8,40.7),(115.8,42.7),(112.0,42.7)]);b.Add(area)
 zone=p.ZONE(b);zone.SetLayer(p.B_Cu);zone.SetNet(b.FindNet('GND'));zone.SetZoneName('SX1262 IPD ground')
 zone.SetLocalClearance(p.FromMM(.15));zone.SetMinThickness(p.FromMM(.15));zone.SetAssignedPriority(12);zone.SetPadConnection(p.ZONE_CONNECTION_FULL)
 rectangle(zone,[(112.1,40.9),(115.7,40.9),(115.7,42.5),(112.1,42.5)]);b.Add(zone)
 p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
 (OUT/'handset.kicad_pro').write_text(json.dumps(project,indent=2)+'\n')
 after=geometry(b);assert before['footprints']==after['footprints']
 assert all(after['copper'][k]==v for k,v in before['copper'].items() if k!=ident)
 report=dict(source_board_sha256=hashlib.sha256((SRC/'handset.kicad_pcb').read_bytes()).hexdigest(),final_board_sha256=hashlib.sha256((OUT/'handset.kicad_pcb').read_bytes()).hexdigest(),
  source_project_sha256=hashlib.sha256((SRC/'handset.kicad_pro').read_bytes()).hexdigest(),final_project_sha256=hashlib.sha256((OUT/'handset.kicad_pro').read_bytes()).hexdigest(),
  custom_rules_sha256=hashlib.sha256(RULES.encode()).hexdigest(),removed_copper={ident:before['copper'][ident]},
  preserved_copper_items=len(before['copper'])-1,added_copper_items=len(after['copper'])-len(before['copper'])+1,
  preserved_footprints=len(before['footprints']),ground_vias=vias,
  feed_width_mm=.5,old_feed_length_mm=14.1,new_feed_length_mm=round(sum(math.dist(a,z) for a,z in zip(feed,feed[1:])),4),
  fabrication_released=False,scope='IPD ground/via layout and constrained drill rule; RF matching/impedance and remaining switch/antenna qualification open')
 (OUT/'sx1262-rf-ground-routing.json').write_text(json.dumps(report,indent=2)+'\n');print(OUT)
if __name__=='__main__':main()
