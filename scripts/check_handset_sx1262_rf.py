#!/usr/bin/env python3
"""Independent SX1262 matching/switch contract; deliberately not RF sign-off."""
import copy,json,sys
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as p
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
NETS={
 'SX_RFO':'U4.23 U36.1 L13.2','SX_RFI_N':'U4.22 U36.3','SX_RFI_P':'U4.21 U36.4',
 'SX_TX_MATCH':'U36.8 C99.1','SX_TX_AC':'C99.2 U37.1',
 'SX_RX_MATCH':'U36.6 C100.1','SX_RX_AC':'C100.2 U37.3',
 'SX_ANT_AC':'U37.5 C98.1','LORA_RF_50R':'C98.2 J20.1',
 'SX_RF_SW':'U4.12 R91.1','SX_SWITCH_CTRL':'R91.2 U37.6 C96.1 R93.1',
 'SX_SWITCH_VDD':'R92.2 U37.4 C97.1',
}
PARTS={'U36':('0900FM15K0039001E','0900FM15K0039001E'),
 'U37':('BGS12WN6E6327','BGS12WN6E6327XTSA1'),
 'R91':('100R 1%','RC0402FR-07100RL'),'R92':('100R 1%','RC0402FR-07100RL'),
 'R93':('100k 1%','RC0402FR-07100KL')}
PARTS.update({r:('1nF 10% X7R 50V','GRM155R71H102KA01D') for r in ['C96','C97']})
PARTS.update({r:('100pF 5% C0G 50V','GRM1555C1H101JA01D') for r in ['C98','C99','C100']})
def checks(nets,parts):
 errors=[]
 for net,names in NETS.items():
  if {name for name,value in nets.items() if value==net}!=set(names.split()):errors.append(net+' exact membership')
 for name in 'U36.2 U36.5 U36.7 U36.9 U36.10 U37.2 C96.2 C97.2 R93.2'.split():
  if nets.get(name)!='GND':errors.append(name+' ground')
 if nets.get('R92.1')!='+3V3':errors.append('switch main supply')
 for ref,wanted in PARTS.items():
  if parts.get(ref)!=wanted:errors.append(ref+' value/MPN')
 return errors

def inspect(out):
 xml=ET.parse(out/'netlist.xml').getroot()
 nets={node.get('ref')+'.'+node.get('pin'):net.get('name') for net in xml.findall('./nets/net') for node in net.findall('node') if not node.get('ref').startswith('#')}
 parts={c.get('ref'):(c.findtext('value'),c.findtext('fields/field[@name="MPN"]')) for c in xml.findall('./components/comp')}
 failures=checks(nets,parts);negative=[]
 for name,value in [('U37.1','SX_RX_AC'),('U37.3','SX_TX_AC'),('U37.1','SX_TX_MATCH'),('U37.5','LORA_RF_50R'),('U36.4','SX_RFI_N'),('U37.4','SX_TCXO_PWR'),('U36.10','SX_RFO')]:
  bad=copy.deepcopy(nets);bad[name]=value;negative.append(dict(mutation=name+' -> '+value,rejected=bool(checks(bad,parts))))
 bad=copy.deepcopy(parts);bad['C99']=('0R',PARTS['C99'][1]);negative.append(dict(mutation='DC block replaced by short',rejected=bool(checks(nets,bad))))
 b=p.LoadBoard(str(out/'handset.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()}
 expected={'U36':{'1':(-.7,-.75),'2':(-.7,-.25),'3':(-.7,.25),'4':(-.7,.75),'5':(0,1.0625),'6':(.7,.75),'7':(.7,.25),'8':(.7,-.25),'9':(.7,-.75),'10':(0,-1.0625)},
 'U37':{'1':(-.2,-.4),'2':(-.2,0),'3':(-.2,.4),'4':(.2,.4),'5':(.2,0),'6':(.2,-.4)}}
 for ref,positions in expected.items():
  f=fps[ref];pads={q.GetNumber():q for q in f.Pads() if q.GetNumber()}
  if set(pads)!=set(positions):failures.append(ref+' pad count')
  for pin,pos in positions.items():
   q=pads[pin];rel=q.GetFPRelativePosition();actual=(round(p.ToMM(rel.x),4),round(p.ToMM(rel.y),4))
   if f.GetLayer()==p.B_Cu:actual=(actual[0],-actual[1])
   size=(round(p.ToMM(q.GetSize().x),4),round(p.ToMM(q.GetSize().y),4))
   wanted=(.25,.25) if ref=='U37' else ((.3,.625) if pin in ['5','10'] else (.6,.3))
   if actual!=pos or size!=wanted:failures.append(ref+'.'+pin+' land pattern')
   if q.GetNetname()!=nets.get(ref+'.'+pin):failures.append(ref+'.'+pin+' board net')
 return dict(passed=not failures and all(t['rejected'] for t in negative),failures=failures,negative_tests=negative,
  truth_table={'CTRL_low':'RFIN pin5 -> RF1 pin3 (RX)','CTRL_high':'RFIN pin5 -> RF2 pin1 (TX)'},
  qualification_open=[('Local PA and RF input copper is captured; qualify line geometry and PA load behavior.' if (out/'sx1262-local-rf-routing.json').exists() else 'PA choke/bypass schematic is captured; complete local placement/copper and qualify PA load behavior.'),
   ('Switched RF copper is captured; qualify all transitions and manufacturer ground-via geometry against the selected stackup.' if (out/'sx1262-switch-routing.json').exists() else 'RF component placement is provisional; complete RF routing and manufacturer ground-via geometry against the selected stackup.'),
   'Verify zero DC at all switch RF ports; qualify 100pF blocks, insertion loss, RF switch timing, conducted power/harmonics and sensitivity.',
   'Complete thermal layout, supply integrity, clock and antenna/coexistence qualification.'],fabrication_released=False)
if __name__=='__main__':
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
 result=inspect(out);(out/'sx1262-rf-checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));sys.exit(not result['passed'])
