#!/usr/bin/env python3
"""Check actual display supply/signal/ground copper, independently of routing evidence."""
import json,sys
from pathlib import Path
import pcbnew as p
from handset_display_contract import PINS
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
GROUPS={'LCD_3V0': 'U28.5 C85.1 U29.20 C86.1 U31.3 U31.6 C88.1 R81.1 C47.1 C48.1 J26.7 J26.8 J26.9 J26.35 J26.40 J26.41 J26.42', '+3V3': 'U1.2 C89.1 U31.7 C87.1 U30.8 R58.1', '+5V_RF': 'C26.1 U28.1 C84.1 J26.1 C49.1', 'SYS_EN': 'Q4.1 U28.3', 'SPI_SCK': 'U1.20 U29.2', 'SPI_MOSI': 'U1.21 U29.4', 'SPI_MISO': 'U1.22 U30.6', 'LCD_CS': 'U1.19 U29.6 U30.1 R58.2', 'LCD_DC': 'U2.1 U29.8', 'LCD_RESET': 'U2.2 U29.11', 'TOUCH_RESET': 'U2.3 U29.13', 'TOUCH_IRQ': 'U2.15 U30.3', 'I2C_SDA': 'U1.18 U31.1', 'I2C_SCL': 'U1.17 U31.8', 'PANEL_SPI_SCK': 'U29.18 J26.37', 'PANEL_SPI_MOSI': 'U29.16 J26.34', 'PANEL_SPI_MISO': 'U30.2 R80.1 J26.33', 'PANEL_LCD_CS': 'U29.14 J26.38', 'PANEL_LCD_DC': 'U29.12 J26.36', 'PANEL_LCD_RESET': 'U29.9 J26.10', 'PANEL_TOUCH_RESET': 'U29.7 J26.47', 'PANEL_TOUCH_IRQ': 'U30.5 R81.2 J26.46', 'PANEL_I2C_SDA': 'U31.4 J26.45', 'PANEL_I2C_SCL': 'U31.5 J26.44'}

GROUPS['GND']='U7.8 U28.2 U29.1 U29.10 U29.15 U29.17 U29.19 U30.4 U30.7 U31.2 C84.2 C85.2 C86.2 C87.2 C88.2 C89.2 R80.2 C47.2 C48.2 C49.2 J26.6 J26.43 J26.48 J26.49 J26.50'

GROUPS['GND']+=' '+ ' '.join('J26.'+str(pin) for pin in range(11,33))

def check_board(board):
 board.BuildConnectivity()
 pads={f.GetReference()+'.'+q.GetNumber():q for f in board.GetFootprints() for q in f.Pads() if q.GetNumber()}
 checks=[]
 for net,names in GROUPS.items():
  entries=[(name,pads[name]) for name in names.split()]
  seed=entries[0][1];connected=list(board.GetConnectivity().GetConnectedItems(seed))
  ids={q.m_Uuid.AsString() for q in connected}|{seed.m_Uuid.AsString()}
  wrong=[name for name,q in entries if q.GetNetname()!=net]
  missing=[name for name,q in entries if q.m_Uuid.AsString() not in ids]
  unexpected=sorted({q.GetNetname() for q in connected if q.GetNetname()!=net})
  checks.append(dict(net=net,pads=names.split(),disconnected=missing,wrong_net=wrong,unexpected_nets=unexpected,passed=not(missing or wrong or unexpected)))
 contract=[]
 for ref,pins in PINS.items():
  for pin,net in pins.items():
   actual=pads[ref+'.'+str(pin)].GetNetname()
   if (actual!=net if net else not actual.startswith('unconnected-(')):contract.append(ref+'.'+str(pin))
 return dict(passed=all(c['passed'] for c in checks) and not contract,groups=checks,pin_contract_failures=contract,
             fabrication_released=False,scope='Physical continuity only; does not establish current capacity, thermal margin, signal timing or full-board completeness')

if __name__=='__main__':
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
 report=check_board(p.LoadBoard(str(out/'handset.kicad_pcb')))
 (out/'display-routing-check.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2));sys.exit(0 if report['passed'] else 1)
