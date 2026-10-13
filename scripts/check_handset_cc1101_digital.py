#!/usr/bin/env python3
"""Check CC1101 host-interface copper; firmware and timing remain unqualified."""
import json,sys
from pathlib import Path
import pcbnew as p
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
GROUPS={'SPI_SCK':'U1.20 U5.1 U29.2 U34.4','SPI_MOSI':'U1.21 U5.20 U29.4 U34.5','SPI_MISO':'U1.22 U5.2 U30.6 U34.6','CC_CS':'U1.24 U5.7 R12.2','CC_GDO0':'U1.25 U5.6','CC_GDO2':'U5.3 TP1.1','+3V3':'U1.2 R12.1 L11.1'}
def check_board(b,manifest):
 b.BuildConnectivity();fps={f.GetReference():f for f in b.GetFootprints()};pads={f.GetReference()+'.'+q.GetNumber():q for f in b.GetFootprints() for q in f.Pads() if q.GetNumber()};checks=[];lengths={};inner=[]
 def check(name,ok):checks.append(dict(check=name,passed=bool(ok)))
 for net,keys in GROUPS.items():
  qs=[pads[k] for k in keys.split()];connected=list(b.GetConnectivity().GetConnectedItems(qs[0]));ids={q.m_Uuid.AsString() for q in connected}|{qs[0].m_Uuid.AsString()};check(net+' full pad continuity',all(q.GetNetname()==net and q.m_Uuid.AsString() in ids for q in qs) and all(q.GetNetname()==net for q in connected))
 check('CS pull-up value',fps['R12'].GetValue()=='10k')
 ts={t.m_Uuid.AsString():t for t in b.GetTracks()};added=manifest['added_copper_uuids'];check('all recorded new copper retained',all(uid in ts for uid in added))
 new=[ts[uid] for uid in added if uid in ts];vias=[t for t in new if t.GetClass()=='PCB_VIA'];tracks=[t for t in new if t.GetClass()=='PCB_TRACK']
 check('digital trace widths',all(round(p.ToMM(t.GetWidth()),3) in ({.2,.25} if t.GetNetname()=='CC_VDD' else {.25} if t.GetNetname()=='GND' else {.15}) for t in tracks))
 check('through vias geometry and tenting',all(v.GetViaType()==p.VIATYPE_THROUGH and v.GetWidth(p.F_Cu)==p.FromMM(.5) and v.GetDrillValue()==p.FromMM(.3) and v.GetFrontTentingMode()==p.TENTING_MODE_TENTED and v.GetBackTentingMode()==p.TENTING_MODE_TENTED for v in vias))
 for t in tracks:
  lengths[t.GetNetname()]=lengths.get(t.GetNetname(),0)+p.ToMM(t.GetLength())
  if t.GetLayer() in (p.In1_Cu,p.In2_Cu):inner.append(dict(net=t.GetNetname(),layer=b.GetLayerName(t.GetLayer()),start=[p.ToMM(v) for v in t.GetStart()],end=[p.ToMM(v) for v in t.GetEnd()],length_mm=p.ToMM(t.GetLength())))
 check('inner digital routing outside radio reference area',all(all(pt[1]>=(40.7 if r['net'].startswith('SPI_') else 42) or pt[0]<=88 or (90<pt[0]<100 and pt[1]>58) or (117<pt[0]<(120.1 if r['net'].startswith('SPI_') else 119.6) and pt[1]>36.5) or (117<pt[0]<121 and pt[1]>44.5) for pt in (r['start'],r['end'])) for r in inner))
 check('test-point branch bounded',lengths.get('CC_GDO2',0)<20)
 return dict(passed=all(c['passed'] for c in checks),checks=checks,added_route_lengths_mm={k:round(v,4) for k,v in lengths.items()},inner_escape_segments=inner,new_vias=len(vias),qualification_open=['Qualify shared SPI loading, edge rates, bus clock, MISO release, chip-select timing and power/reset sequencing on assembled hardware. Other SPI-device branches remain unfinished.','Review inner-layer fanout and return-current paths, including the still-unrouted GNSS region; configure GDO0 and the GDO2 test output, then verify CC1101 register access and RF operation.'],fabrication_released=False)
if __name__=='__main__':
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT;r=check_board(p.LoadBoard(str(out/'handset.kicad_pcb')),json.loads((out/'cc1101-digital-routing.json').read_text()));(out/'cc1101-digital-checks.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));sys.exit(not r['passed'])
