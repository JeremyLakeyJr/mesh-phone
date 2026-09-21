"""Import the local routing result without weakening any fabrication rules."""
from pathlib import Path
import shutil
import sys
import pcbnew

pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__
directory = Path(__file__).resolve().parent / 'revF-gps-expansion'
path = directory / 'owasso1.kicad_pcb'
backup = directory / 'owasso1-unrouted.kicad_pcb'
if not backup.exists():
    shutil.copy2(path, backup)
shutil.copy2(backup, path)
shutil.copy2(directory.parent / 'owasso1.kicad_pro', directory / 'owasso1.kicad_pro')
board = pcbnew.LoadBoard(str(path))
def placements():
    return {f.GetReference():(f.GetPosition().x,f.GetPosition().y,f.GetOrientationDegrees(),f.GetLayer()) for f in board.GetFootprints()}
before = placements()
if not pcbnew.ImportSpecctraSES(board, sys.argv[1] if len(sys.argv)>1 else '/tmp/owasso1-revf-routed.ses'):
    raise RuntimeError('SES import failed')
assert before == placements(), 'Routing import changed placements'
if not board.Save(str(path)):
    raise RuntimeError('Board save failed')
# Native SES import can reset the in-memory default net class; retain the exact
# authoritative project constraints after saving rather than accepting defaults.
shutil.copy2(directory.parent / 'owasso1.kicad_pro', directory / 'owasso1.kicad_pro')
print('Imported routes; all component positions, rotations and sides preserved.')
