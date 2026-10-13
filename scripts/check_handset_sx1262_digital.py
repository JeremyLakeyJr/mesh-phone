#!/usr/bin/env python3
"""Check SX1262 host-interface copper; timing and RF operation remain unqualified."""
import json,sys
from pathlib import Path
import pcbnew as p
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
GROUPS={'SPI_SCK':'U1.20 U4.18 U5.1','SPI_MOSI':'U1.21 U4.17 U5.20','SPI_MISO':'U1.22 U4.16 U5.2','SX_CS':'U1.23 U4.19 R10.2','SX_RESET':'U1.9 U4.15','SX_BUSY':'U1.10 U4.14','SX_DIO1':'U1.11 U4.13','+3V3':'U1.2 U4.1 U4.10 U4.11 R10.1 L11.1'}
def check_board(b,manifest):
 b.BuildConnectivity();fps={f.GetReference():f for f in b.GetFootprints()};pads={f.GetReference()+'.'+q.GetNumber():q for f in b.GetFootprints() for q in f.Pads() if q.GetNumber()};checks=[];lengths={}
 def check(name,ok):checks.append(dict(check=name,passed=bool(ok)))
 for net,keys in GROUPS.items():
  qs=[pads[k] for k in keys.split()];connected=list(b.GetConnectivity().GetConnectedItems(qs[0]));ids={q.m_Uuid.AsString() for q in connected}|{qs[0].m_Uuid.AsString()};check(net+' full pad continuity',all(q.GetNetname()==net and q.m_Uuid.AsString() in ids for q in qs) and all(q.GetNetname()==net for q in connected))
 check('CS pull-up value',fps['R10'].GetValue()=='10k')
 ts={t.m_Uuid.AsString():t for t in b.GetTracks()};added=manifest['added_copper_uuids'];check('all recorded new copper retained',bool(added) and all(uid in ts for uid in added))
 new=[ts[uid] for uid in added if uid in ts];vias=[t for t in new if t.GetClass()=='PCB_VIA'];tracks=[t for t in new if t.GetClass()=='PCB_TRACK']
 widths={'+3V3':{.15,.5},'LORA_RF_50R':{.34},'GND':{.25}}
 check('reviewed trace widths',all(round(p.ToMM(t.GetWidth()),3) in widths.get(t.GetNetname(),{.15}) for t in tracks))
 check('through vias geometry and tenting',all(v.GetViaType()==p.VIATYPE_THROUGH and v.GetWidth(p.F_Cu)==p.FromMM(.5) and v.GetDrillValue()==p.FromMM(.3) and v.GetFrontTentingMode()==p.TENTING_MODE_TENTED and v.GetBackTentingMode()==p.TENTING_MODE_TENTED for v in vias))
 for t in tracks:lengths[t.GetNetname()]=lengths.get(t.GetNetname(),0)+p.ToMM(t.GetLength())
 return dict(passed=all(c['passed'] for c in checks),checks=checks,added_route_lengths_mm={k:round(v,4) for k,v in lengths.items()},new_vias=len(vias),qualification_open=['Qualify shared-SPI loading, edge rates, bus clock, MISO release, NSS timing, reset/BUSY/DIO1 behavior and power sequencing on assembled hardware. Other SPI-device branches remain unfinished.','Review final inner-layer power and digital return paths, revised antenna/switch-control geometry and the relocated pull-up/filter; verify firmware register access, TCXO/switch timing and conducted RF operation.'],fabrication_released=False)
if __name__=='__main__':
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT;r=check_board(p.LoadBoard(str(out/'handset.kicad_pcb')),json.loads((out/'sx1262-digital-routing.json').read_text()));(out/'sx1262-digital-checks.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));sys.exit(not r['passed'])
