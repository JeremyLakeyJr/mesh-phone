#!/usr/bin/env python3
"""Remove PCB-only net assignments that have no schematic contract."""
import os
os.environ['LD_LIBRARY_PATH'] = os.path.expanduser('~/.local/kicad-compat')
import pcbnew

path = 'owasso1.kicad_pcb'
board = pcbnew.LoadBoard(path)

# The Ra-01SH control pins are intentionally reserved at the module edge.
# They are labelled in the schematic but not assigned to MCU GPIOs yet.
net_names = ['/SX1262_TXEN', '/SX1262_DIO2', '/SX1262_DIO3', '/SX1262_RXEN']
nets = dict(board.GetNetsByName())
for name in net_names:
    if name not in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni
j3 = board.FindFootprintByReference('J3')
if j3 is None:
    raise SystemExit('J3 not found')
for pad_num, net_name in zip(['5', '7', '8', '11'], net_names):
    pad = next((p for p in j3.Pads() if p.GetNumber() == pad_num), None)
    if pad is None:
        raise SystemExit(f'J3 pad {pad_num} not found')
    pad.SetNet(nets[net_name])

sw = board.FindFootprintByReference('SW1')
if sw is None:
    raise SystemExit('SW1 not found')
pad = next((p for p in sw.Pads() if p.GetNumber() == '3'), None)
if pad is None:
    raise SystemExit('SW1 pad 3 not found')
old = pad.GetNetname()
pad.SetNet(None)
board.Save(path)
print(f'SW1.3: {old!r} -> no net')
print('J3 pads 5/7/8/11 assigned to reserved schematic nets')
