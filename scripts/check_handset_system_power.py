#!/usr/bin/env python3
"""Separate handset power-path and shared-pack screening; unknown loads stay open."""
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
from check_handset_modem_power import ROOT, build_report as modem_report


def scenario(vbat, main_a, aux_a, modem_a, modem_v, efficiency):
    values=(vbat,main_a,aux_a,modem_a,modem_v,efficiency)
    if not all(math.isfinite(v) for v in values) or vbat<=0 or modem_v<=0 or not 0<efficiency<=1 or min(main_a,aux_a,modem_a)<0:
        raise ValueError('Invalid power scenario')
    # Ideal battery-only SYS tracking; FET/wiring drop and Iq excluded explicitly.
    handset=(3.3*main_a+5*aux_a)/(vbat*efficiency)
    modem=modem_v*modem_a/(vbat*efficiency)
    return dict(battery_v=vbat,main_3v3_a=main_a,aux_5v_a=aux_a,
        handset_branch_a=handset,modem_branch_a=modem,total_battery_a=handset+modem)


def build_report(root=ROOT):
    inputs=json.loads((root/'system-power-inputs.json').read_text())
    spec={c['ref']:c for c in json.loads((root/'generated/connectivity.json').read_text())}
    tree=ET.parse(root/'generated/netlist.xml').getroot()
    nets={(node.attrib['ref'],node.attrib['pin']):net.attrib['name'] for net in tree.findall('./nets/net') for node in net.findall('node')}
    values={c.attrib['ref']:c.findtext('value') for c in tree.findall('./components/comp')}
    for ref,pins in inputs['cad_contract'].items():
        if values[ref]!=spec[ref]['value']:
            raise ValueError('CAD value mismatch: '+ref)
        for pin,net in pins.items():
            if spec[ref]['nets'][pin]!=net or nets.get((ref,pin))!=net:
                raise ValueError('Power topology changed: '+ref+'.'+pin)
    if values['U3']!='BQ25186DLHR' or values['U7']!='TPS63802DLAR' or values['U1']!='ESP32-S3-WROOM-1-N16R8':
        raise ValueError('Re-audit device current models')
    policy=json.loads((root/'charger-policy.json').read_text())
    # BQ25186 register 0x06 bits 7:6: battery discharge OCP, typical threshold.
    ocp_code=(int(policy['common_registers']['0x06'],16)>>6)&3
    ocp_typ=[.5,1.05,1.65,3.125][ocp_code]
    modem=modem_report(root)
    vm=modem['output_reference_resistor_corner_v'][1]
    a=inputs['screening_assumptions'];rows=[]
    for v in a['battery_voltages_v']:
        for main in a['main_rail_sweep_a']:
            for aux in a['aux_rail_sweep_a']:
                row=scenario(v,main,aux,a['modem_output_a'],vm,a['conversion_efficiency'])
                row['exceeds_configured_handset_ocp_typical']=row['handset_branch_a']>ocp_typ
                row['exceeds_provisional_pack_target']=row['total_battery_a']>modem['battery_upgrade']['target_continuous_a']
                rows.append(row)
    unresolved=[x['function'] for x in inputs['load_inventory'] if x['qualified_peak_a'] is None]
    findings=[]
    if unresolved:findings.append('Unqualified load profiles: '+', '.join(unresolved))
    if any(r['exceeds_configured_handset_ocp_typical'] for r in rows):
        findings.append('Handset load sweep crosses the configured BQ25186 discharge OCP typical threshold; raising it requires path and thermal qualification.')
    if any(r['exceeds_provisional_pack_target'] for r in rows):
        findings.append('Simultaneous rail-load sweep exceeds the provisional pack target; converter ratings are not a permitted simultaneous-use budget.')
    findings.append('Battery-only sensitivity model excludes FET/wiring drop, converter Iq, startup/inrush and USB load sharing; hardware operating modes remain unqualified.')
    host=scenario(3,inputs['host_tx_reference']['current_a'],0,0,vm,a['conversion_efficiency'])
    return dict(scope='Battery-only rail envelope and incomplete load inventory; no operating mode authorized',
        configured_handset_ocp_code=ocp_code,configured_handset_ocp_typical_a=ocp_typ,
        ocp_is_not_guaranteed_continuous_rating=True,esp32_reference_case=host,
        legacy_other_load_allowance_a=modem['assumptions']['other_battery_load_a'],
        unresolved_load_profiles=unresolved,scenarios=rows,blocking_findings=findings,
        fabrication_released=False,input_sha256={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
        ['system-power-inputs.json','generated/netlist.xml','generated/connectivity.json','charger-policy.json','battery-upgrade-requirements.json','battery-qualification.json']})


if __name__=='__main__':
    result=build_report()
    (ROOT/'system-power-report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
