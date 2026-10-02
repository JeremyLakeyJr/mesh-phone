#!/usr/bin/env python3
"""Independent netlist contracts for always-on charger ownership and isolation."""
import copy,json,sys
from pathlib import Path
import xml.etree.ElementTree as ET
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
x=ET.parse(OUT/'netlist.xml').getroot()
nets={(n.get('ref'),n.get('pin')):net.get('name') for net in x.findall('./nets/net') for n in net.findall('node')}
contracts={
'U25':{'3':'PWR_AON_3V0','4':'GND','5':'PWR_NRST','18':'PWR_HOST_SCL','19':'PWR_HOST_SDA','20':'PWR_SWDIO','21':'PWR_SWCLK','27':'CHG_I2C_SDA','28':'CHG_I2C_SCL'},
'U26':{'1':'VSYS','2':'GND','3':'VSYS','5':'PWR_AON_3V0'},
'U27':{'1':'+3V3','2':'I2C_SCL','3':'I2C_SDA','4':'GND','5':'+3V3','6':'PWR_HOST_SDA','7':'PWR_HOST_SCL','8':'PWR_AON_3V0'},
'U3':{'7':'CHG_I2C_SDA','8':'CHG_I2C_SCL'},
'U24':{'6':'CHG_I2C_SCL','7':'CHG_I2C_SDA','8':'PWR_AON_3V0'},
'R76':{'1':'PWR_AON_3V0','2':'CHG_I2C_SCL'},'R77':{'1':'PWR_AON_3V0','2':'CHG_I2C_SDA'},
'R78':{'1':'PWR_AON_3V0','2':'PWR_NRST'},
'C60':{'1':'PWR_AON_3V0'},'R66':{'1':'PWR_AON_3V0'},'R69':{'1':'PWR_AON_3V0'},
'U8':{'7':'I2C_SCL','8':'I2C_SDA'},'U7':{'1':'SYS_EN'}}
def errors(n):
    err=[f'{r}.{pin} != {net}' for r,pins in contracts.items() for pin,net in pins.items() if n.get((r,pin))!=net]
    for net,expected in [('PWR_HOST_SCL',{('U25','18'),('U27','7')}),('PWR_HOST_SDA',{('U25','19'),('U27','6')})]:
        if {k for k,v in n.items() if v==net}!=expected:err.append(net+': unexpected endpoint / B-side pull-up')
    for net in ('CHG_I2C_SDA','CHG_I2C_SCL'):
        if any(r not in ('U3','U24','U25','R76','R77') for (r,pin),v in n.items() if v==net):err.append(net+': bus ownership violation')
    return err
assert not errors(nets),errors(nets)
mutations=[(('U24','8'),'+3V3'),(('U3','7'),'I2C_SDA'),(('U27','5'),'PWR_AON_3V0'),(('R99','1'),'PWR_HOST_SDA'),(('U1','99'),'CHG_I2C_SDA')]
for key,val in mutations:
    bad=copy.deepcopy(nets);bad[key]=val;assert errors(bad),(key,val)
report=dict(contract_pins=sum(map(len,contracts.values())),negative_tests=len(mutations),passed=True,scope='Logical net ownership and power domains; not routed continuity or hardware qualification',fabrication_released=False)
(OUT/'power-supervisor-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
