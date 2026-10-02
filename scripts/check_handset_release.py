#!/usr/bin/env python3
"""Fail closed for manufacturing; run check_handset_pcb.sh immediately first."""
import json
from pathlib import Path
import sys
from check_handset_modem_power import build_report
from check_handset_system_power import build_report as system_power_report
from check_handset_display_expansion import build_report as display_expansion_report

root=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a'
out=root/'generated'
verification=json.loads((out/'verification-summary.json').read_text())
drc=json.loads((out/'drc.json').read_text())
erc=json.loads((out/'erc.json').read_text())
blockers=[x for x in json.loads((root/'release-blockers.json').read_text()) if x['status']!='closed']
issues={
 'display_expansion_findings':display_expansion_report(root)['blocking_findings'],
 'system_power_findings':system_power_report(root)['blocking_findings'],
 'modem_power_findings':build_report(root)['blocking_findings'],
 'open_engineering_blockers':[x['id'] for x in blockers],
 'integrity_failures':len(verification['integrity_failures']),
 'native_drc_findings':len(drc['violations']),
 'native_erc_findings':sum(len(s['violations']) for s in erc['sheets']),
 'unrouted_items':len(drc['unconnected_items']),
 'schematic_parity_findings':len(drc.get('schematic_parity',[])),
}
if (out/'display-routing.json').exists():
    import pcbnew as pcb
    from check_handset_display_routing import check_board
    display_copper=check_board(pcb.LoadBoard(str(out/'handset.kicad_pcb')))
    issues['display_routing_failures']=[g['net'] for g in display_copper['groups'] if not g['passed']]+display_copper['pin_contract_failures']
if (out/'backlight-update.json').exists():
    import pcbnew as pcb
    from check_handset_backlight_routing import check_board as check_backlight
    backlight=check_backlight(pcb.LoadBoard(str(out/'handset.kicad_pcb')))
    issues['backlight_routing_failures']=[g['net'] for g in backlight['groups'] if not g['passed']]+backlight['pin_contract_failures']
blocked=any(issues.values())
print(json.dumps({'status':'DO NOT FABRICATE' if blocked else 'Checks clear; independent release review required',**issues},indent=2))
sys.exit(1 if blocked else 0)
