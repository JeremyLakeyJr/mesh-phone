#!/usr/bin/env python3
"""Fail closed for manufacturing; run check_handset_pcb.sh immediately first."""
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a'
out=root/'generated'
verification=json.loads((out/'verification-summary.json').read_text())
drc=json.loads((out/'drc.json').read_text())
erc=json.loads((out/'erc.json').read_text())
blockers=[x for x in json.loads((root/'release-blockers.json').read_text()) if x['status']!='closed']
issues={
 'open_engineering_blockers':[x['id'] for x in blockers],
 'integrity_failures':len(verification['integrity_failures']),
 'native_drc_findings':len(drc['violations']),
 'native_erc_findings':sum(len(s['violations']) for s in erc['sheets']),
 'unrouted_items':len(drc['unconnected_items']),
 'schematic_parity_findings':len(drc.get('schematic_parity',[])),
}
blocked=any(issues.values())
print(json.dumps({'status':'DO NOT FABRICATE' if blocked else 'Checks clear; independent release review required',**issues},indent=2))
sys.exit(1 if blocked else 0)
