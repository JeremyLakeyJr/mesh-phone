#!/usr/bin/env python3
import json
import uuid
from pathlib import Path

root = Path(__file__).resolve().parent
draft = json.loads((root / "netlist_draft.json").read_text())
def uid(): return str(uuid.uuid4())
def skey(p):
    s = str(p)
    return (0, int(s)) if s.isdigit() else (1, s)

parts = {p["ref"]: p for p in draft["parts"]}
pins = {r: [] for r in parts}
for n in draft["nets"]:
    for r, p in n["nodes"]:
        if r in pins and str(p) not in pins[r]: pins[r].append(str(p))
for r in pins: pins[r].sort(key=skey)

pos = {}
for i, r in enumerate(sorted(parts)):
    c, row = divmod(i, 8)
    pos[r] = (45 + c*43, 35 + row*28)

defs = []
coords = {}
for r in sorted(parts):
    ps = pins[r] or ["1"]
    side = (len(ps)+1)//2
    h = max(12.7, side*2.54+5.08)
    name = "OWASSO_" + r
    lines = [f'  (symbol "{name}"',
             '    (pin_names (offset 0.254)) (exclude_from_sim no) (in_bom yes) (on_board yes)',
             f'    (property "Reference" "{r}" (at 0 {-h/2-2.5} 0) (effects (font (size 1.27 1.27))))',
             f'    (property "Value" "{parts[r]["value"]}" (at 0 {h/2+2.5} 0) (effects (font (size 1 1))))',
             f'    (symbol "{name}_0_1" (rectangle (start -10.16 {-h/2}) (end 10.16 {h/2}) (stroke (width 0.254) (type default)) (fill (type background))))',
             f'    (symbol "{name}_1_1"']
    x0, y0 = pos[r]
    for i, p in enumerate(ps):
        if i < side:
            x, y, a = -12.7, -h/2+2.54+i*2.54, 0
            coords[(r,p)] = (x0+x, y0+y)
        else:
            x, y, a = 12.7, -h/2+2.54+(i-side)*2.54, 180
            coords[(r,p)] = (x0+x, y0+y)
        lines.append(f'''      (pin passive line
        (at {x} {y} {a}) (length 2.54) (uuid "{uid()}")
        (name "P{p}" (effects (font (size 0.9 0.9))))
        (number "{p}" (effects (font (size 0.9 0.9))))
      )''')
    lines += ['    )', '  )']
    defs.append("\n".join(lines))

symbols = []
for r in sorted(parts):
    x, y = pos[r]
    symbols.append(f'''  (symbol
    (lib_id "OWASSO:OWASSO_{r}") (at {x} {y} 0) (unit 1)
    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
    (uuid "{uid()}")
    (property "Reference" "{r}" (at {x} {y-8} 0) (effects (font (size 1.27 1.27))))
    (property "Value" "{parts[r]["value"]}" (at {x} {y+8} 0) (effects (font (size 1 1))))
    (property "Footprint" "{parts[r].get("fp") or ""}" (at {x} {y} 0) (hide yes) (effects (font (size 1 1))))
    (instances (project "owasso1" (path "/{uid()}" (reference "{r}") (unit 1))))
  )''')

labels = []
for n in draft["nets"]:
    for r, p in n["nodes"]:
        if (r, str(p)) not in coords: continue
        x, y = coords[(r, str(p))]
        labels.append(f'''  (label "{n["name"]}" (at {x:.3f} {y:.3f} 0)
    (effects (font (size 1 1)) (justify left bottom)) (uuid "{uid()}"))''')

text = f'''(kicad_sch
  (version 20250114) (generator "owasso-revD") (generator_version "10.0")
  (uuid "{uid()}") (paper "A2")
  (title_block (title "OWASSO-1 DIY Phone") (date "2026-09-13") (rev "D"))
  (lib_symbols
{chr(10).join(defs)}
  )
{chr(10).join(symbols)}
{chr(10).join(labels)}
  (sheet_instances (path "/" (page "1")))
)\n'''
(root / "owasso1.kicad_sch").write_text(text)
print(f"Wrote rev-D schematic: {len(parts)} parts, {len(draft['nets'])} nets")
