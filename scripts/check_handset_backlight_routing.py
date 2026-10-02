#!/usr/bin/env python3
"""Check backlight physical continuity without trusting routing manifests."""
import json,sys
from pathlib import Path
import pcbnew as p
from handset_backlight_contract import PINS
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
GROUPS={'+5V_RF':'C26.1 J26.1 C49.1 C90.1 U32.8',
 'GND':'U7.8 U32.2 U32.9 C90.2 R82.2 R57.2',
 'LCD_K1':'J26.2 U32.3','LCD_K2':'J26.3 U32.4','LCD_K3':'J26.4 U32.5','LCD_K4':'J26.5 U32.6',
 'LCD_BL_RSET':'U32.7 R82.1','LCD_BL_GATE':'U32.1 R56.2 R57.1','LCD_BL_EN':'U2.14 R56.1'}

def check_board(board):
 board.BuildConnectivity();pads={f.GetReference()+'.'+q.GetNumber():q for f in board.GetFootprints() for q in f.Pads() if q.GetNumber()}
 checks=[];contract=[]
 for ref,pins in PINS.items():
  for pin,net in pins.items():
   key=ref+'.'+pin
   if key not in pads or pads[key].GetNetname()!=net:contract.append(key)
 for net,names in GROUPS.items():
  names=names.split();seed=pads.get(names[0]);connected=list(board.GetConnectivity().GetConnectedItems(seed)) if seed else []
  ids={q.m_Uuid.AsString() for q in connected}|({seed.m_Uuid.AsString()} if seed else set())
  missing=[n for n in names if n not in pads or pads[n].m_Uuid.AsString() not in ids]
  wrong=[n for n in names if n not in pads or pads[n].GetNetname()!=net]
  checks.append(dict(net=net,pads=names,disconnected=missing,wrong_net=wrong,passed=not(missing or wrong)))
 return dict(passed=not contract and all(c['passed'] for c in checks),groups=checks,pin_contract_failures=contract,fabrication_released=False,scope='Physical continuity only; current capacity, thermal performance and firmware timing remain unqualified')

if __name__=='__main__':
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
 report=check_board(p.LoadBoard(str(out/'handset.kicad_pcb')))
 (out/'backlight-routing-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));sys.exit(0 if report['passed'] else 1)
