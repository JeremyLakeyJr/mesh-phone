#!/usr/bin/env python3
"""Stage the CAT4004A four-channel backlight current sink."""
import copy,csv,hashlib,json,shutil,subprocess,uuid
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as p
from cad_sexpr import Q,parse,dump,child,children,prop
import rebuild_handset_schematics as drawing
from sync_handset_schematic_rebuild import geometry
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'hardware/handset-rev-a/generated';OUT=Path('/tmp/handset-backlight')
uid=lambda x:str(uuid.uuid5(uuid.NAMESPACE_URL,'handset-backlight/'+x))
p.SwigPyIterator.next=p.SwigPyIterator.__next__
assert not (SRC/'backlight-update.json').exists(),'Already installed; preserve later work'
OUT.mkdir(exist_ok=True);hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in SRC.iterdir() if f.is_file()}
for f in SRC.iterdir():
 if f.is_file() and f.suffix not in ('.lck','.prl'):shutil.copy2(f,OUT/f.name)
shutil.copytree(SRC/'Handset.pretty',OUT/'Handset.pretty',dirs_exist_ok=True)
drawing.OUT=OUT;spec={c['ref']:c for c in json.loads((SRC/'connectivity.json').read_text())};symbols={};instances={}
for path in SRC.glob('*.kicad_sch'):
 tree=parse(path.read_text())
 for s in children(child(tree,'lib_symbols'),'symbol'):symbols[str(s[1])]=s
 for s in children(tree,'symbol'):instances[str(prop(s,'Reference')[2])]=s
root=parse((SRC/'handset.kicad_sch').read_text());rootid=str(child(root,'uuid')[1]);sid=drawing.UID('display')
lib=parse((SRC/'Handset.kicad_sym').read_text())
def symbol(name,pins):
 s=parse(f'(symbol "Handset:{name}" (pin_names (offset 0.508)) (in_bom yes) (on_board yes) (property "Reference" "U" (at 0 0 0) (effects (font (size 1 1)))) (property "Value" "{name}" (at 0 0 0) (effects (font (size 1 1)))))')
 left=[x for x in pins if x[2] not in ('output','tri_state','power_out')];right=[x for x in pins if x not in left];n=max(len(left),len(right));height=(n+1)*2.54
 s.append(parse(f'(symbol "{name}_0_1" (rectangle (start -15.24 5.08) (end 15.24 {-height}) (stroke (width 0.254) (type default)) (fill (type background))))'))
 unit=['symbol',Q(name+'_1_1')]
 for group,x,angle in [(left,-20.32,0),(right,20.32,180)]:
  for i,(num,label,typ) in enumerate(group):unit.append(parse(f'(pin {typ} line (at {x} {-i*2.54} {angle}) (length 5.08) (name "{label}" (effects (font (size 1 1)))) (number "{num}" (effects (font (size 1 1)))))'))
 s.append(unit);symbols['Handset:'+name]=s;local=copy.deepcopy(s);local[1]=Q(name);lib.append(local);return 'Handset:'+name
added=[]
def add(ref,value,libid,fp,nets,x,y):
 assert ref not in spec;added.append(ref)
 spec[ref]=dict(ref=ref,value=value,libid=libid,footprint=fp,nets={str(k):v for k,v in nets.items()},x=x,y=y,side='F',angle=0,sheet='display')
 instances[ref]=parse(f'(symbol (lib_id "{libid}") (at 0 0 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid(ref)}") (property "Reference" "{ref}" (at 0 0 0) (effects (font (size 1 1)))) (property "Value" "{value}" (at 0 0 0) (effects (font (size 1 1)))) (property "Footprint" "{fp}" (at 0 0 0) (effects (font (size 1 1)) (hide yes))) (instances (project "handset" (path "/{rootid}/{sid}" (reference "{ref}") (unit 1)))))')
driver=symbol('CAT4004AHU2',[(1,'EN/DIM','input'),(2,'GND','power_in'),(3,'LED1','passive'),(4,'LED2','passive'),(5,'LED3','passive'),(6,'LED4','passive'),(7,'RSET','passive'),(8,'VIN','power_in'),(9,'EP','power_in')])
(OUT/'Handset.kicad_sym').write_text(dump(lib)+'\n')
removed=['Q2','R52','R53','R54','R55']
b=p.LoadBoard(str(SRC/'handset.kicad_pcb'));b.BuildConnectivity();before=geometry(b)
for fp in b.GetFootprints():
 if fp.GetReference() in removed:
  for pad in fp.Pads():
   copper=[q for q in b.GetConnectivity().GetConnectedItems(pad) if isinstance(q,p.PCB_TRACK)]
   assert not copper,('Refuse to discard routed component',fp.GetReference(),pad.GetNumber())
for ref in removed:del spec[ref]
# Land pattern: onsemi CAT4002A/D rev3 p10 case517AW, rotated so pin1 is top-left.
fpname='CAT4004A_UDFN-8_2x2mm_P0.5mm_EP1x1.73mm'
fp=['footprint',Q('Handset:'+fpname),['version','20241229'],['generator',Q('pcbnew')],['layer',Q('F.Cu')],['attr','smd']]
fp+= [parse('(property "Reference" "U" (at 0 -2 0) (layer "F.Fab") (effects (font (size 0.7 0.7))))'),parse('(property "Value" "CAT4004AHU2-GT3" (at 0 2 0) (layer "F.Fab") (effects (font (size 0.7 0.7))))')]
for layer,width in [('F.Fab',.1),('F.CrtYd',.05)]:
 a=1 if layer=='F.Fab' else 1.4
 fp.append(parse(f'(fp_rect (start {-a} {-a}) (end {a} {a}) (stroke (width {width}) (type solid)) (layer "{layer}"))'))
fp.append(parse('(fp_line (start -1 -0.6) (end -0.6 -1) (stroke (width 0.1) (type solid)) (layer "F.Fab"))'))
fp.append(parse('(fp_line (start -1.3 -1.25) (end -0.65 -1.25) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))'))
for pin,x,y in [(1,-.9,-.75),(2,-.9,-.25),(3,-.9,.25),(4,-.9,.75),(5,.9,.75),(6,.9,.25),(7,.9,-.25),(8,.9,-.75)]:
 fp.append(parse(f'(pad "{pin}" smd rect (at {x} {y}) (size 0.5 0.3) (layers "F.Cu" "F.Paste" "F.Mask"))'))
fp.append(parse('(pad "9" smd rect (at 0 0) (size 1 1.73) (layers "F.Cu" "F.Mask"))'))
# Two paste windows, ~61% exposed-pad coverage; assembly review remains open.
for y in [-.43,.43]:fp.append(parse(f'(pad "" smd rect (at 0 {y}) (size 0.7 0.75) (layers "F.Paste"))'))
(OUT/'Handset.pretty'/ (fpname+'.kicad_mod')).write_text(dump(fp)+'\n')
add('U32','CAT4004AHU2-GT3',driver,'Handset:'+fpname,{1:'LCD_BL_GATE',2:'GND',3:'LCD_K1',4:'LCD_K2',5:'LCD_K3',6:'LCD_K4',7:'LCD_BL_RSET',8:'+5V_RF',9:'GND'},94,77)
add('R82','4.99k 1%','Device:R','Resistor_SMD:R_0402_1005Metric',{1:'LCD_BL_RSET',2:'GND'},97,74)
add('C90','1uF 10% X7R 25V','Device:C','Capacitor_SMD:C_0603_1608Metric',{1:'+5V_RF',2:'GND'},98,77)
for ref,mpn,mfr in [('U32','CAT4004AHU2-GT3','onsemi'),('R82','RC0402FR-074K99L','Yageo'),('C90','GRM188R71E105KA12D','Murata')]:
 spec[ref].update(mpn=mpn,manufacturer=mfr)
 instances[ref].append(parse(f'(property "MPN" "{mpn}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))'))
page=drawing.Sheet('display','External display, touch and backlight',22,'CAT4004A: four current sinks, 4.99k sets approx. 15mA/channel. On/off only until dimming timing is qualified. Do not fabricate.',rootid,spec,instances,symbols)
page.place('J26',86.36,121.92);page.place('U32',274.32,60.96)
pairs=defaultdict(list)
for ref,c in spec.items():
 if c['sheet']=='display' and ref not in ['J26','U32']:pairs[tuple(c['nets'][k] for k in ['1','2'])].append(ref)
banks=[rs[j:j+3] for rs in pairs.values() for j in range(0,len(rs),3)]
for i,refs in enumerate(banks):page.bank(refs,180.34+(i%2)*101.6,127+(i//2)*30.48)
page.text('EN/DIM: external R57 pull-down retains default off.\nInitialize U2 GPIO low for >=10ms before enabling.\nKeep high for full-scale current; do not apply ordinary PWM.\nRSET gain, current drift, heat and purchased panel remain unqualified.',170.18,271.78,1)
page.finish()
subprocess.run(['kicad-cli','sch','export','netlist',str(OUT/'handset.kicad_sch'),'--format','kicadxml','-o',str(OUT/'netlist.xml')],check=True)
xml=ET.parse(OUT/'netlist.xml').getroot();native={(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in xml.findall('./nets/net') for n in net.findall('node')}
# Delete only specifically superseded, unrouted footprints; never remove existing copper.
tree=parse((SRC/'handset.kicad_pcb').read_text())
tree[:]=[v for v in tree if not(isinstance(v,list) and v and v[0]=='footprint' and str(prop(v,'Reference')[2]) in removed)]
(OUT/'handset.kicad_pcb').write_text(dump(tree)+'\n');b=p.LoadBoard(str(OUT/'handset.kicad_pcb'))
def netobj(name):
 n=b.FindNet(name)
 if not n:n=p.NETINFO_ITEM(b,name);b.Add(n)
 return n
for ref in added:
 c=spec[ref];library,name=c['footprint'].split(':');path=str(OUT/'Handset.pretty') if library=='Handset' else '/usr/share/kicad/footprints/'+library+'.pretty'
 fp=p.FootprintLoad(path,name);b.Add(fp);fp.SetReference(ref);fp.SetValue(c['value']);fp.SetFPID(p.LIB_ID(library,name));fp.SetPosition(p.VECTOR2I(p.FromMM(c['x']),p.FromMM(c['y'])));fp.Reference().SetLayer(p.F_Fab);fp.Value().SetVisible(False)
 path=p.KIID_PATH()
 for ident in [rootid,sid,uid(ref)]:path.push_back(p.KIID(ident))
 fp.SetPath(path);fp.SetSheetname('External display, touch and backlight');fp.SetSheetfile('display.kicad_sch')
 for pad in fp.Pads():
  if pad.GetNumber():pad.SetNet(netobj(native[(ref,pad.GetNumber())]))
p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'handset.kicad_pcb'),b);shutil.copy2(SRC/'handset.kicad_pro',OUT/'handset.kicad_pro')
tree=parse((OUT/'handset.kicad_pcb').read_text())
for fp in children(tree,'footprint'):
 ref=str(prop(fp,'Reference')[2])
 if ref in added:
  field=copy.deepcopy(prop(fp,'Value'));field[1]=Q('MPN');field[2]=Q(spec[ref]['mpn']);child(field,'uuid')[1]=Q(uid(ref+'/mpn'));fp.append(field)
(OUT/'handset.kicad_pcb').write_text(dump(tree)+'\n')
after=geometry(p.LoadBoard(str(OUT/'handset.kicad_pcb')))
assert before['copper']==after['copper']
assert all(g==after['footprints'][r] for r,g in before['footprints'].items() if r not in removed)
(OUT/'connectivity.json').write_text(json.dumps(list(spec.values()),indent=2)+'\n')
with (OUT/'placement.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec.values())
with (OUT/'backlight-bom.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['Reference','Manufacturer','MPN','Value','Footprint','Qualification'])
 for ref in added:
  c=spec[ref];w.writerow([ref,c['manufacturer'],c['mpn'],c['value'],c['footprint'],'Captured; routing and hardware qualification pending'])
(OUT/'backlight-update.json').write_text(json.dumps(dict(source_hashes=hashes,added_refs=added,removed_refs=removed,preserved_copper_items=len(before['copper']),fabrication_released=False),indent=2)+'\n')
print('Staged',OUT)
