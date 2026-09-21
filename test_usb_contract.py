#!/usr/bin/env python3
import os
import sys
import uuid
os.environ['LD_LIBRARY_PATH'] = os.path.expanduser('~/.local/kicad-compat')
import pcbnew

pcb_path, sch_path = sys.argv[1:3]
board = pcbnew.LoadBoard(pcb_path)
usb = board.FindFootprintByReference('USB1')
if usb is None:
    raise SystemExit('USB1 not found')
pad_map = {
    'A1': '1', 'A4': '4', 'A5': '5', 'A6': '6', 'A7': '7', 'A9': '9', 'A12': '12',
    'B1': '13', 'B4': '14', 'B5': '15', 'B6': '16', 'B7': '17', 'B9': '19', 'B12': '22',
}
for pad in usb.Pads():
    old = pad.GetNumber()
    if old in pad_map:
        pad.SetNumber(pad_map[old])
board.Save(pcb_path)

text = open(sch_path, encoding='utf-8').read()
connected = {
    1651.000: 'GND', 1658.620: 'VBUS5V', 1661.160: 'USB_CC1',
    1663.700: 'USB_D+', 1666.240: 'USB_D-', 1671.320: 'VBUS5V',
    1678.940: 'GND', 1681.480: 'GND', 1684.020: 'VBUS5V',
    1686.560: 'USB_CC2', 1689.100: 'USB_D+', 1691.640: 'USB_D-',
    1696.720: 'VBUS5V', 1704.340: 'GND',
}
for y in connected:
    needle = f'\n\t(no_connect\n\t\t(at 198.120 {y:.3f})'
    while needle in text:
        start = text.index(needle) + 1
        depth = 0
        end = None
        for i in range(start, len(text)):
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        text = text[:start] + text[end:]

items = []
for y, label in connected.items():
    items.append(f'''\t(wire
\t\t(pts (xy 198.120 {y:.3f}) (xy 195.580 {y:.3f}))
\t\t(stroke (width 0) (type default)) (uuid "{uuid.uuid4()}"))
\t(label "{label}" (at 195.580 {y:.3f} 0)
\t\t(effects (font (size 1.0 1.0)) (justify left bottom)) (uuid "{uuid.uuid4()}"))''')
insert = '\n'.join(items) + '\n'
close = text.rfind('\n)')
if close < 0:
    raise SystemExit('schematic root close not found')
text = text[:close] + '\n' + insert + text[close:]
open(sch_path, 'w', encoding='utf-8').write(text)
print('USB1 pads mapped and schematic labels added')
