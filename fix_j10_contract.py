#!/usr/bin/env python3
"""Align the JAE SIM contact pad numbers with the schematic's six-pin contract."""
import os
import sys
os.environ['LD_LIBRARY_PATH'] = os.path.expanduser('~/.local/kicad-compat')
import pcbnew

path = sys.argv[1] if len(sys.argv) > 1 else 'owasso1.kicad_pcb'
board = pcbnew.LoadBoard(path)
fp = board.FindFootprintByReference('J10')
if fp is None:
    raise SystemExit('J10 not found')
mapping = {'C1': '1', 'C5': '2', 'C3': '3', 'C2': '4', 'C7': '5', 'CSW': '6'}
for pad in fp.Pads():
    old = pad.GetNumber()
    if old in mapping:
        pad.SetNumber(mapping[old])
board.Save(path)
print('J10 contact pads remapped to schematic pins 1..6')
