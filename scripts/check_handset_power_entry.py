#!/usr/bin/env python3
"""Check physical continuity of the local power-entry cell, not net labels alone."""
from collections import defaultdict
import json
from pathlib import Path
import sys
import pcbnew as p

p.SwigPyIterator.next = p.SwigPyIterator.__next__


def inspect(path):
    board = p.LoadBoard(str(path))
    board.BuildConnectivity()
    meta = json.loads((path.parent/'power-entry-update.json').read_text())
    refs = set(meta['added_refs'] + meta['changed_refs'] + ['J2','USB1','U17'])
    groups = defaultdict(list)
    for fp in board.GetFootprints():
        if fp.GetReference() not in refs:
            continue
        for pad in fp.Pads():
            net = pad.GetNetname()
            if not pad.GetNumber() or not net or net.startswith('unconnected-(') or net in ('USB_D_P','USB_D_N'):
                continue
            groups[net].append((fp.GetReference()+'.'+pad.GetNumber(), pad))
    results = []
    for net, entries in sorted(groups.items()):
        start = entries[0][1]
        connected = list(board.GetConnectivity().GetConnectedItems(start))
        ids = {item.m_Uuid.AsString() for item in connected} | {start.m_Uuid.AsString()}
        missing = sorted(name for name, pad in entries if pad.m_Uuid.AsString() not in ids)
        unexpected = sorted({item.GetNetname() for item in connected if item.GetNetname() != net})
        results.append(dict(net=net, pads=sorted(name for name, _ in entries),
                            disconnected=missing, unexpected_connected_nets=unexpected,
                            passed=not (missing or unexpected)))
    return dict(scope='Local power entry only; external rail/I2C distribution and USB data excluded',
                groups=results, passed=all(r['passed'] for r in results),
                local_pads=sum(len(v) for v in groups.values()), fabrication_released=False)


if __name__ == '__main__':
    path = Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated/handset.kicad_pcb'
    result = inspect(path)
    (path.parent/'power-entry-continuity.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['passed'] else 1)
