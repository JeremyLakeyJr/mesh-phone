#!/usr/bin/env python3
import os, sys
os.environ['LD_LIBRARY_PATH'] = os.path.expanduser('~/.local/kicad-compat')
import pcbnew

src, dst = sys.argv[1], sys.argv[2]
b = pcbnew.LoadBoard(src)
targets = {'R4': (162.5, 91.0), 'R5': (162.5, 95.0)}
found = set()
for fp in b.GetFootprints():
    ref = fp.GetReference()
    if ref in targets:
        x, y = targets[ref]
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        found.add(ref)
if found != set(targets):
    raise SystemExit(f'missing passives: {set(targets)-found}')
if not b.Save(dst):
    raise SystemExit('save failed')
print(dst)
