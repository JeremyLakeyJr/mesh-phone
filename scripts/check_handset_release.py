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
if (out/'expansion-update.json').exists():
    import pcbnew as pcb
    from check_handset_expansion import check_board as check_expansion,check_circuit
    check_circuit(out)
    expansion=check_expansion(pcb.LoadBoard(str(out/'handset.kicad_pcb')))
    issues['expansion_routing_failures']=[g['net'] for g in expansion['groups'] if not g['passed']]+expansion['pin_contract_failures']
if (out/'usb-connector-update.json').exists():
    import pcbnew as pcb
    from check_handset_usb_connector import inspect as check_usb
    usb=check_usb(pcb.LoadBoard(str(out/'handset.kicad_pcb')))
    issues['usb_footprint_failures']=[c['check'] for c in usb['checks'] if not c['passed']]
if (out/'keypad-routing.json').exists():
    import pcbnew as pcb
    from check_handset_keypad import check_board as check_keypad
    keypad=check_keypad(pcb.LoadBoard(str(out/'handset.kicad_pcb')))
    issues['keypad_routing_failures']=[g['net'] for g in keypad['groups'] if not g['passed']]
if (out/'core-routing.json').exists():
    import pcbnew as pcb
    from check_handset_core import check_board as check_core
    core=check_core(pcb.LoadBoard(str(out/'handset.kicad_pcb')))
    issues['core_routing_failures']=[c['check'] for c in core['checks'] if not c['passed']]
if (out/'usb-data-update.json').exists():
    import pcbnew as pcb
    from check_handset_usb_data import inspect as check_usb_data
    usb_data=check_usb_data(pcb.LoadBoard(str(out/'handset.kicad_pcb')))
    issues['usb_data_failures']=[c['check'] for c in usb_data['checks'] if not c['passed']]
if (out/'audio-routing.json').exists():
    import pcbnew as pcb
    from check_handset_audio import check_board as check_audio
    audio=check_audio(pcb.LoadBoard(str(out/'handset.kicad_pcb')))
    issues['audio_routing_failures']=[g['net'] for g in audio['groups'] if not g['passed']]
if (out/'sx1262-clock-update.json').exists():
    from check_handset_sx1262_clock import inspect as check_sx_clock
    clock=check_sx_clock(out)
    issues['sx1262_clock_failures']=clock['circuit_failures']+[c['check'] for c in clock['copper']['checks'] if not c['passed']]
    issues['sx1262_clock_qualification']=clock['qualification_open']
blocked=any(issues.values())
print(json.dumps({'status':'DO NOT FABRICATE' if blocked else 'Checks clear; independent release review required',**issues},indent=2))
sys.exit(1 if blocked else 0)
