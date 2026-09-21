#!/usr/bin/env python3
"""Normalize imported autorouter traces to the board fabrication rule."""
import os
import sys
os.environ["LD_LIBRARY_PATH"] = os.path.expanduser("~/.local/kicad-compat")
import pcbnew

src = sys.argv[1]
dst = sys.argv[2]
board = pcbnew.LoadBoard(src)
minimum = pcbnew.FromMM(0.20)
tracks = board.Tracks()
changed = 0
for i in range(tracks.size()):
    item = tracks[i]
    if item.GetWidth() < minimum:
        item.SetWidth(minimum)
        changed += 1
if not board.Save(dst):
    raise SystemExit("could not save normalized board")
print(f"normalized {changed} tracks -> {dst}")
