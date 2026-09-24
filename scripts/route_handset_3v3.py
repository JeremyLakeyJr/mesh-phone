#!/usr/bin/env python3
"""Prepare a local 3.3 V layout in /tmp; never overwrite the saved board.

One-shot candidate generator. Native checks and review precede installation.
The rest of the handset, including power distribution, remains unrouted.
"""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import pcbnew as p

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'hardware/handset-rev-a/generated'
OUT = Path('/tmp/handset-3v3-routing')
p.SwigPyIterator.next = p.SwigPyIterator.__next__
assert not (SOURCE / 'reg3-routing.json').exists(), 'Already installed; preserve manual changes.'
OUT.mkdir(exist_ok=True)
for f in SOURCE.iterdir():
    if f.is_file() and f.suffix in ('.kicad_pcb', '.kicad_sch', '.kicad_pro', '.kicad_sym', '.json', '.csv'):
        shutil.copy2(f, OUT / f.name)
for name in ('fp-lib-table', 'sym-lib-table'):
    shutil.copy2(SOURCE / name, OUT / name)
shutil.copytree(SOURCE / 'Handset.pretty', OUT / 'Handset.pretty', dirs_exist_ok=True)
b = p.LoadBoard(str(OUT / 'handset.kicad_pcb'))
fps = {f.GetReference(): f for f in b.GetFootprints()}
layout = {
    'U7': (124, 132, 90), 'L1': (124, 127.7, 180),
    'C20': (127.6, 131.2, 270), 'C21': (120.4, 131.2, 270),
    'C22': (117.4, 131.2, 270), 'R31': (121.6, 135.3, 0),
    'R32': (123.9, 135.3, 0), 'R33': (120.4, 134.1, 0),
    'R30': (126.7, 135.5, 0),
}
# Shift the whole cell below the existing SW8 through-via; retain its routing.
layout = {ref: (x, y+3, a) for ref, (x,y,a) in layout.items()}
def point(xy):
    return p.VECTOR2I(*(p.FromMM(v) for v in xy))
for ref, (x, y, angle) in layout.items():
    f = fps[ref]
    # Do not move any existing routed pad.
    for pad in f.Pads():
        assert not b.GetConnectivity().GetConnectedTracks(pad), ref + ' already routed'
    f.SetPosition(point((x, y)))
    f.SetOrientationDegrees(angle)
    f.Reference().SetLayer(p.B_Fab)
    f.Reference().SetPosition(point((x, y + 1.8)))
    f.Reference().SetTextAngle(p.EDA_ANGLE(0, p.DEGREES_T))

added = []
def track(net, points, width=.25, layer=p.B_Cu):
    points = [(x,y+3) for x,y in points]
    for a, z in zip(points, points[1:]):
        t = p.PCB_TRACK(b)
        t.SetStart(point(a)); t.SetEnd(point(z))
        t.SetWidth(p.FromMM(width)); t.SetLayer(layer)
        t.SetNet(b.FindNet(net)); b.Add(t); added.append(t)

def via(x, y, diameter=.6):
    y += 3
    v = p.PCB_VIA(b); v.SetPosition(point((x, y)))
    v.SetWidth(p.FromMM(diameter)); v.SetDrill(p.FromMM(.3))
    v.SetViaType(p.VIATYPE_THROUGH); v.SetLayerPair(p.F_Cu, p.B_Cu)
    v.SetNet(b.FindNet('GND')); b.Add(v); added.append(v)

# Short switch-node escapes widen away from the 0.5 mm pitch IC pads.
track('REG3_L1', [(124.5,131.25),(124.5,130.55)])
track('REG3_L1', [(124.5,130.55),(125.185,129.865),(125.185,127.7)], .6)
track('REG3_L2', [(123.5,131.25),(123.5,130.55)])
track('REG3_L2', [(123.5,130.55),(122.815,129.865),(122.815,127.7)], .6)
track('VSYS', [(125,131.25),(125.5,131.25)])
track('VSYS', [(125.5,131.25),(126.5,130.25),(127.6,130.25)], .6)
track('+3V3', [(123,131.25),(122.5,131.25)])
track('+3V3', [(122.5,131.25),(121.5,130.25),(120.4,130.25),(117.4,130.25)], .6)

# Two small through vias share the power return; no via sits in a solder pad.
track('GND', [(124,131.45),(124,132.15),(123.7,132.15)])
track('GND', [(124,132.15),(124.3,132.15)])
for x in (123.7,124.3): via(x,132.15,.5)
for x in (117.4,120.4,127.6):
    track('GND', [(x,132.15),(x,132.95)], .6)
    via(x,132.95); via(x+.8,132.95)
    track('GND', [(x,132.95),(x+.8,132.95)], .6)
# Local inner-layer power return only: whole-board ground planes are separate work.
track('GND', [(117.4,132.95),(128.4,132.95)], 1.2, p.In1_Cu)
for x in (123.7,124.3): track('GND', [(x,132.15),(x,132.95)], .6, p.In1_Cu)

# Quiet feedback, with a Kelvin sense connection at the output capacitor.
track('+3V3', [(120.4,130.25),(119.2,130.25),(119.2,135.3),(121.09,135.3)], .2)
track('REG3_FB', [(123.5,132.9),(123.5,134.5),(122.7,135.3),(122.11,135.3)], .2)
track('REG3_FB', [(122.7,135.3),(123.39,135.3)], .2)
track('GND', [(124,132.9),(124,133.5),(124.25,133.75)], .2)
track('GND', [(124.5,132.9),(124.5,133.5),(124.25,133.75)], .2)
track('GND', [(124.25,133.75),(124.41,133.91),(124.41,135.3)], .2)
track('GND', [(124.41,134.6),(125,134.6)], .2)
via(125,134.6)
# Separate analog return joins the power node next to the IC, not a load return.
track('GND', [(125,134.6),(125.3,134.6),(125.3,132.15),(124.3,132.15)], .25, p.In1_Cu)
track('SYS_EN', [(125,132.9),(125,133.5),(126.19,134.69),(126.19,135.5)], .2)
track('GND', [(127.21,135.5),(128,135.5)], .25); via(128,135.5)
track('GND', [(128,135.5),(128,132.95)], .3, p.In1_Cu)
track('+3V3', [(119.2,134.1),(119.89,134.1)], .2)
track('REG3_PG', [(123,132.9),(123,133.2),(122.1,134.1),(120.91,134.1)], .2)

p.SaveBoard(str(OUT / 'handset.kicad_pcb'), b)
spec = json.loads((OUT / 'connectivity.json').read_text())
for c in spec:
    if c['ref'] in layout:
        c['x'],c['y'],c['angle'] = layout[c['ref']]
(OUT / 'connectivity.json').write_text(json.dumps(spec, indent=2)+'\n')
with (OUT / 'placement.csv').open('w') as f:
    w = csv.DictWriter(f, fieldnames=['ref','value','footprint','x','y','side','angle','sheet'], extrasaction='ignore')
    w.writeheader(); w.writerows(spec)
(OUT / 'reg3-routing.json').write_text(json.dumps({
    'source_sha256': hashlib.sha256((SOURCE / 'handset.kicad_pcb').read_bytes()).hexdigest(),
    'moved_refs': list(layout), 'added_copper_items':len(added),
    'scope':'Local U7 3.3 V converter only; external VSYS/SYS_EN/3V3/GND distribution incomplete',
    'source':'https://www.ti.com/lit/ds/symlink/tps63802.pdf',
    'fabrication_released':False,
},indent=2)+'\n')
print(OUT)
