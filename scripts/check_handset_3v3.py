#!/usr/bin/env python3
"""Verify local converter copper continuity, not merely matching net names.

External power distribution and electrical/thermal qualification are excluded.
"""
import json
from pathlib import Path
import sys
import pcbnew as p

p.SwigPyIterator.next = p.SwigPyIterator.__next__
REFS = {'U7', 'L1', 'C20', 'C21', 'C22', 'R30', 'R31', 'R32', 'R33'}
EXPECTED = {
    'SYS_EN': {'U7.1','R30.1'},
    'GND': {'U7.2','U7.3','U7.8','C20.2','C21.2','C22.2','R30.2','R32.2'},
    'REG3_FB': {'U7.4','R31.2','R32.1'},
    'REG3_PG': {'U7.5','R33.2'},
    '+3V3': {'U7.6','C21.1','C22.1','R31.1','R33.1'},
    'REG3_L2': {'U7.7','L1.2'},
    'REG3_L1': {'U7.9','L1.1'},
    'VSYS': {'U7.10','C20.1'},
}

def inspect(board):
    board.BuildConnectivity()
    copper = board.GetConnectivity()
    pads = {f.GetReference()+'.'+pad.GetNumber(): pad
            for f in board.GetFootprints() if f.GetReference() in REFS
            for pad in f.Pads() if pad.GetNumber()}
    results = []
    for net, names in EXPECTED.items():
        start = pads[sorted(names)[0]]
        connected = list(copper.GetConnectedItems(start))
        ids = {item.m_Uuid.AsString() for item in connected}
        ids.add(start.m_Uuid.AsString())
        missing = sorted(name for name in names if pads[name].m_Uuid.AsString() not in ids)
        wrong = sorted(name for name in names if pads[name].GetNetname() != net)
        unexpected = sorted({item.GetNetname() for item in connected if item.GetNetname() != net})
        results.append({'net':net, 'pads':sorted(names), 'disconnected':missing,
                        'wrong_net':wrong, 'unexpected_connected_nets':unexpected,
                        'passed':not (missing or wrong or unexpected)})
    return {'scope':'Local U7 converter copper; does not validate external distribution or operation',
            'groups':results, 'passed':all(r['passed'] for r in results),
            'local_pads':len(pads), 'fabrication_released':False}

if __name__ == '__main__':
    path = Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated/handset.kicad_pcb'
    result = inspect(p.LoadBoard(str(path)))
    (path.parent/'reg3-continuity.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['passed'] else 1)
