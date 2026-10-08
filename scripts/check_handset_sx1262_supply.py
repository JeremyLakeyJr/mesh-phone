#!/usr/bin/env python3
"""Check SX1262 input supply and ground copper against established rail anchors."""
import json
import sys
from pathlib import Path
import pcbnew as p

p.SwigPyIterator.next = p.SwigPyIterator.__next__
ROOT = Path(__file__).resolve().parents[1] / 'hardware/handset-rev-a/generated'
GROUPS = {
    '+3V3': 'U1.2 U4.1 U4.10 U4.11 C8.1 C75.1 C76.1',
    'GND': 'U1.1 U4.2 U4.5 U4.8 U4.20 U4.25 C8.2 C75.2 C76.2',
}


def check_board(board):
    board.BuildConnectivity()
    pads = {}
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            pads.setdefault(footprint.GetReference() + '.' + pad.GetNumber(), []).append(pad)
    checks = []
    for net, names in GROUPS.items():
        entries = [(name, pad) for name in names.split() for pad in pads[name]]
        seed = entries[0][1]
        connected = list(board.GetConnectivity().GetConnectedItems(seed))
        ids = {pad.m_Uuid.AsString() for pad in connected} | {seed.m_Uuid.AsString()}
        missing = [name for name, pad in entries if pad.m_Uuid.AsString() not in ids]
        wrong = [name for name, pad in entries if pad.GetNetname() != net]
        unexpected = sorted({item.GetNetname() for item in connected if item.GetNetname() != net})
        checks.append(dict(net=net, physical_pads=len(entries), missing=missing,
                           wrong_net=wrong, unexpected_nets=unexpected,
                           passed=not (missing or wrong or unexpected)))
    return dict(passed=all(check['passed'] for check in checks), groups=checks,
                fabrication_released=False,
                scope='SX1262 input supplies and ground continuity; RF frontend, thermal layout and electrical qualification remain open.')


if __name__ == '__main__':
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    report = check_board(p.LoadBoard(str(out / 'handset.kicad_pcb')))
    (out / 'sx1262-supply-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    sys.exit(not report['passed'])
