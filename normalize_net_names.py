#!/usr/bin/env python3
import os
import sys
os.environ['LD_LIBRARY_PATH'] = os.path.expanduser('~/.local/kicad-compat')
import pcbnew

path = sys.argv[1]
board = pcbnew.LoadBoard(path)
changed = 0
for net in board.GetNetsByNetcode().values():
    name = net.GetNetname()
    if name and not name.startswith('/'):
        net.SetNetname('/' + name)
        changed += 1
board.SetAreasNetCodesFromNetNames()
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
if not board.Save(path):
    raise SystemExit('save failed')
print(f'normalized {changed} net names')
