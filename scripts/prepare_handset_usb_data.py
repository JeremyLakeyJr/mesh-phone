#!/usr/bin/env python3
"""Stage USB pass-through ESD pads and host series termination without moving existing parts."""
import copy,csv,hashlib,json,shutil,subprocess,uuid
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as p
from cad_sexpr import Q,parse,dump,child,children,prop
import rebuild_handset_schematics as drawing
from sync_handset_schematic_rebuild import geometry
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'hardware/handset-rev-a/generated';OUT=Path('/tmp/handset-usb-data')
assert not (SRC/'usb-data-update.json').exists(),'Already installed'
shutil.copytree(SRC,OUT,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.history','.git','*.lck','*.prl'))
drawing.OUT=OUT
spec={c['ref']:c for c in json.loads((SRC/'connectivity.json').read_text())};symbols={};instances={}
for path in SRC.glob('*.kicad_sch'):
 tree=parse(path.read_text())
 for s in children(child(tree,'lib_symbols'),'symbol'):symbols[str(s[1])]=s
 for s in children(tree,'symbol'):instances[str(prop(s,'Reference')[2])]=s
rootid=str(child(parse((SRC/'handset.kicad_sch').read_text()),'uuid')[1]);sid=drawing.UID('usb')
uid=lambda ref:str(uuid.uuid5(uuid.NAMESPACE_URL,'handset-usb-data/'+ref))
# TI permits NC pads as external pass-through lands. They are not internally connected.
# Mark those two symbol pins passive to describe the intentional copper connection.
sym=symbols['Handset:TPD4E05U06DQA']
for unit in children(sym,'symbol'):
 for pin in children(unit,'pin'):
  if child(pin,'number')[1] in ('9','10'):pin[1]='passive'
lib=parse((SRC/'Handset.kicad_sym').read_text())
for i,s in enumerate(lib):
 if isinstance(s,list) and s[:2]==['symbol','TPD4E05U06DQA']:
  replacement=copy.deepcopy(sym);replacement[1]=Q('TPD4E05U06DQA');lib[i]=replacement
(OUT/'Handset.kicad_sym').write_text(dump(lib)+'\n')
spec['U17']['nets'].update({'1':'USB_D_N','2':'USB_D_P','9':'USB_D_P','10':'USB_D_N'})
for ref,pin,pol,x in [('R88','13','N',91.98),('R89','14','P',93.25)]:
 spec['U1']['nets'][pin]='USB_HOST_D_'+pol
 spec[ref]=dict(ref=ref,value='22 1%',libid='Device:R',footprint='Resistor_SMD:R_0402_1005Metric',nets={'1':'USB_HOST_D_'+pol,'2':'USB_D_'+pol},x=97.25,y=47.98 if pol=='N' else 49.25,side='B',angle=0,sheet='usb',mpn='RC0402FR-0722RL',manufacturer='Yageo')
 instances[ref]=parse(f'(symbol (lib_id "Device:R") (at 0 0 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid(ref)}") (property "Reference" "{ref}" (at 0 0 0) (effects (font (size 1 1)))) (property "Value" "22 1%" (at 0 0 0) (effects (font (size 1 1)))) (property "Footprint" "Resistor_SMD:R_0402_1005Metric" (at 0 0 0) (effects (font (size 1 1)) (hide yes))) (property "MPN" "RC0402FR-0722RL" (at 0 0 0) (effects (font (size 1 1)) (hide yes))) (instances (project "handset" (path "/{rootid}/{sid}" (reference "{ref}") (unit 1)))))')
core=(OUT/'core.kicad_sch').read_text().replace('"USB_D_N"','"USB_HOST_D_N"').replace('"USB_D_P"','"USB_HOST_D_P"');(OUT/'core.kicad_sch').write_text(core)
page=drawing.Sheet('usb','USB-C data and ESD',3,'U17 NC lands 10/9 externally bridge to 1/2 for pass-through routing; no internal connection. R88/R89 host series termination, initial 22 ohms; qualify on hardware.',rootid,spec,instances,symbols)
page.place('USB1',76.2,81.28);page.place('U17',203.2,71.12)
page.bank(['R88'],279.4,66.04);page.bank(['R89'],355.6,66.04);page.finish()
subprocess.run(['kicad-cli','sch','export','netlist',str(OUT/'handset.kicad_sch'),'--format','kicadxml','-o',str(OUT/'netlist.xml')],check=True)
xml=ET.parse(OUT/'netlist.xml').getroot();native={(n.get('ref'),n.get('pin')):net.get('name') for net in xml.findall('./nets/net') for n in net.findall('node')}
b=p.LoadBoard(str(SRC/'handset.kicad_pcb'));before=geometry(b)
def netobj(name):
 n=b.FindNet(name)
 if not n:n=p.NETINFO_ITEM(b,name);b.Add(n)
 return n
for f in b.GetFootprints():
 if f.GetReference() in ('U1','U17'):
  for q in f.Pads():
   if q.GetNumber():q.SetNet(netobj(native[f.GetReference(),q.GetNumber()]))
for ref in ['R88','R89']:
 c=spec[ref];f=p.FootprintLoad('/usr/share/kicad/footprints/Resistor_SMD.pretty','R_0402_1005Metric');b.Add(f);f.SetReference(ref);f.SetValue(c['value']);f.SetFPID(p.LIB_ID('Resistor_SMD','R_0402_1005Metric'));f.Flip(f.GetPosition(),False);f.SetOrientationDegrees(c['angle']);f.SetPosition(p.VECTOR2I(p.FromMM(c['x']),p.FromMM(c['y'])));f.Reference().SetLayer(p.B_Fab);f.Value().SetVisible(False);f.SetField('MPN',c['mpn']);f.GetField('MPN').SetVisible(False)
 path=p.KIID_PATH()
 for ident in [rootid,sid,uid(ref)]:path.push_back(p.KIID(ident))
 f.SetPath(path);f.SetSheetname('USB-C data and ESD');f.SetSheetfile('usb.kicad_sch')
 for q in f.Pads():q.SetNet(netobj(native[ref,q.GetNumber()]))
p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
after=geometry(b)
assert before['copper']==after['copper']
assert all(after['footprints'][k]==v for k,v in before['footprints'].items())
(OUT/'connectivity.json').write_text(json.dumps(list(spec.values()),indent=2)+'\n')
with (OUT/'placement.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec.values())
(OUT/'usb-data-update.json').write_text(json.dumps(dict(source_board_sha256=hashlib.sha256((SRC/'handset.kicad_pcb').read_bytes()).hexdigest(),added_refs=['R88','R89'],preserved_copper_items=len(before['copper']),fabrication_released=False),indent=2)+'\n')
print('Staged',OUT)
