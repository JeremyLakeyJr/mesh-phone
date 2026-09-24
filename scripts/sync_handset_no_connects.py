#!/usr/bin/env python3
"""Match KiCad's unique no-connect net names; never join unused pins together."""
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as p

OUT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
p.SwigPyIterator.next=p.SwigPyIterator.__next__
root=ET.parse(OUT/'netlist.xml').getroot()
nc={}
for net in root.findall('./nets/net'):
    name=net.get('name');nodes=net.findall('node')
    if name.startswith('unconnected-('):
        assert len(nodes)==1, 'A no-connect must never join separate pins'
        nc[(nodes[0].get('ref'),nodes[0].get('pin'))]=name
b=p.LoadBoard(str(OUT/'handset.kicad_pcb'))
count=0
for f in b.GetFootprints():
    ref=f.GetReference()
    if ref in ('H1','H2','H3','H4'):
        f.SetAttributes(f.GetAttributes() | p.FP_BOARD_ONLY)
    for pad in f.Pads():
        name=nc.get((ref,pad.GetNumber()))
        if name:
            assert not pad.GetNetname() or pad.GetNetname()==name, (ref,pad.GetNumber())
            n=b.FindNet(name)
            if not n:n=p.NETINFO_ITEM(b,name);b.Add(n)
            pad.SetNet(n);count+=1
p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
print(f'Synchronized {count} separate no-connect pad nets; mounting holes marked mechanical/board-only.')
