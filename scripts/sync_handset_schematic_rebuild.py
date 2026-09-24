#!/usr/bin/env python3
"""Synchronize the staged all-sheet rebuild, never reset saved placement."""
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as p
from cad_sexpr import parse, child

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'hardware/handset-rev-a/generated'
OUT = Path('/tmp/handset-schematic-rebuild')
p.SwigPyIterator.next = p.SwigPyIterator.__next__


def geometry(board):
    copper = {}
    for t in board.GetTracks():
        entry = [t.GetClass(), t.GetStart().x, t.GetStart().y,
                 t.GetEnd().x, t.GetEnd().y, t.GetWidth(t.GetLayer()) if isinstance(t, p.PCB_VIA) else t.GetWidth(), t.GetLayer(), t.GetNetname()]
        if isinstance(t, p.PCB_VIA):
            entry += [t.GetDrillValue(), t.TopLayer(), t.BottomLayer(), t.GetViaType()]
        copper[t.m_Uuid.AsString()] = entry
    footprints = {}
    for f in board.GetFootprints():
        footprints[f.GetReference()] = [f.m_Uuid.AsString(), f.GetPosition().x,
            f.GetPosition().y, f.GetOrientationDegrees(), f.GetLayer(), f.GetValue(),
            f.GetFPID().GetLibNickname(), f.GetFPID().GetLibItemName(),
            sorted((pad.m_Uuid.AsString(), pad.GetNumber(), pad.GetPosition().x,
                    pad.GetPosition().y, pad.GetSize().x, pad.GetSize().y,
                    pad.GetOrientationDegrees()) for pad in f.Pads())]
    return {'copper': copper, 'footprints': footprints}


def main():
    manifest = json.loads((OUT/'schematic-rebuild.json').read_text())
    for name, digest in manifest['source_hashes'].items():
        assert hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() == digest, name
    spec = json.loads((OUT/'connectivity.json').read_text())
    xml = ET.parse(OUT/'netlist.xml').getroot()
    components = {c.get('ref'): c for c in xml.findall('./components/comp')}
    assert set(components) == {c['ref'] for c in spec}
    nets = {(node.get('ref'), node.get('pin')): net.get('name')
            for net in xml.findall('./nets/net') for node in net.findall('node')}
    for c in spec:
        for pin, expected in c['nets'].items():
            actual = nets.get((c['ref'], pin))
            assert actual == expected if expected else actual and actual.startswith('unconnected-('), (c['ref'], pin, expected, actual)
    b = p.LoadBoard(str(SOURCE/'handset.kicad_pcb'))
    before = geometry(b)
    rootid = str(child(parse((OUT/'handset.kicad_sch').read_text()), 'uuid')[1])
    changed = []
    for f in b.GetFootprints():
        ref = f.GetReference()
        if ref not in components:
            assert ref in ('H1', 'H2', 'H3', 'H4')
            continue
        comp = components[ref]
        path = p.KIID_PATH()
        ids = [rootid] + comp.find('sheetpath').get('tstamps').strip('/').split('/') + [comp.findtext('tstamps')]
        for ident in ids:
            path.push_back(p.KIID(ident))
        f.SetPath(path)
        for key in ('Sheetname', 'Sheetfile'):
            getattr(f, 'Set'+key)(comp.find(f'property[@name="{key}"]').get('value'))
        for pad in f.Pads():
            if not pad.GetNumber():
                continue
            if (ref, pad.GetNumber()) not in nets:
                assert not pad.GetNetname(), (ref, pad.GetNumber(), 'Unexpected omitted electrical pad')
                continue
            net = nets[(ref, pad.GetNumber())]
            previous = pad.GetNetname()
            if previous != net:
                assert (ref, pad.GetNumber(), net) in [('U4', '1', '+3V3'), ('U9', '5', 'GND')] or (previous.startswith('unconnected-(') and net.startswith('unconnected-(')), (ref, pad.GetNumber(), previous, net)
                changed.append([ref, pad.GetNumber(), previous, net])
                n = b.FindNet(net)
                if not n:
                    n = p.NETINFO_ITEM(b, net); b.Add(n)
                pad.SetNet(n)
    p.SaveBoard(str(OUT/'handset.kicad_pcb'), b)
    # SaveBoard must not replace the saved design rules with default rules.
    (OUT/'handset.kicad_pro').write_bytes((SOURCE/'handset.kicad_pro').read_bytes())
    after = geometry(p.LoadBoard(str(OUT/'handset.kicad_pcb')))
    assert before == after, 'Placement, footprint geometry or routed copper changed'
    with (OUT/'placement.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=['ref','value','footprint','x','y','side','angle','sheet'], extrasaction='ignore')
        writer.writeheader(); writer.writerows(spec)
    manifest.update(pad_net_changes=changed, preserved_copper_items=len(before['copper']),
                    preserved_footprints=len(before['footprints']), netlist_verified=True)
    (OUT/'schematic-rebuild.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Verified all pin nets; preserved', len(before['copper']), 'copper items and', len(before['footprints']), 'footprints. Changed pad nets:', changed)


if __name__ == '__main__':
    main()
