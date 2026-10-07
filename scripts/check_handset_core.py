#!/usr/bin/env python3
"""Independently verify boot/reset and TCA8418 bring-up copper."""
import json, math, sys
from pathlib import Path
import pcbnew as p
p.SwigPyIterator.next = p.SwigPyIterator.__next__
ROOT = Path(__file__).resolve().parents[1] / 'hardware/handset-rev-a/generated'
GROUPS = {
 '+3V3': 'U1.2 R1.1 R2.1 R3.1 R4.1 R5.1 C4.1 U2.21 U33.10',
 'GND': 'U1.1 C1.2 C4.2 U2.19 U2.25 SW17.2 SW18.2',
 'MCU_EN': 'U1.3 R1.2 C1.1 U33.6 U2.20 SW18.1',
 'MCU_BOOT': 'U1.27 R2.2 SW17.1',
 'I2C_SCL': 'U1.17 R3.2 U2.23 U33.8',
 'I2C_SDA': 'U1.18 R4.2 U2.22 U33.9',
 'KEY_IRQ': 'U1.12 R5.2 U2.24',
}

def check_board(board):
 board.BuildConnectivity()
 fps = {f.GetReference(): f for f in board.GetFootprints()}
 pads = {}
 for ref, f in fps.items():
  for q in f.Pads(): pads.setdefault(ref + '.' + q.GetNumber(), []).append(q)
 checks = []
 for net, names in GROUPS.items():
  entries = [(name, q) for name in names.split() for q in pads[name]]
  seed = entries[0][1]
  connected = list(board.GetConnectivity().GetConnectedItems(seed))
  ids = {q.m_Uuid.AsString() for q in connected} | {seed.m_Uuid.AsString()}
  missing = [name + ':' + q.m_Uuid.AsString() for name, q in entries if q.m_Uuid.AsString() not in ids]
  wrong = [name for name, q in entries if q.GetNetname() != net]
  unexpected = sorted({q.GetNetname() for q in connected if q.GetNetname() != net})
  checks.append(dict(check=net, physical_pads=len(entries), disconnected=missing, wrong_net=wrong, unexpected_nets=unexpected, passed=not(missing or wrong or unexpected)))
 for ref, value in {'R1':'10k','R2':'10k','R5':'10k','R3':'4.7k','R4':'4.7k','C1':'1uF','C4':'100nF'}.items():
  checks.append(dict(check=ref+' value', actual=fps[ref].GetValue(), expected=value, passed=fps[ref].GetValue()==value))
 a,z = pads['U2.21'][0].GetPosition(),pads['C4.1'][0].GetPosition()
 distance=math.hypot(p.ToMM(a.x-z.x),p.ToMM(a.y-z.y))
 checks.append(dict(check='C4 local bypass placement',distance_mm=round(distance,3),passed=distance<=2.5))
 return dict(passed=all(c['passed'] for c in checks),checks=checks,fabrication_released=False,scope='Copper continuity and component intent; power-up timing, button noise immunity, firmware and full-board routing remain unqualified.')

if __name__ == '__main__':
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
 report=check_board(p.LoadBoard(str(out/'handset.kicad_pcb')))
 (out/'core-routing-check.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2));sys.exit(0 if report['passed'] else 1)
