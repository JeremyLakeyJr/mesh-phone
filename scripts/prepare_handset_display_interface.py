#!/usr/bin/env python3
"""Stage a dedicated 3.0 V display domain and explicit signal buffers."""
import copy,csv,hashlib,json,shutil,subprocess,uuid
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as p
from cad_sexpr import Q,parse,dump,child,children,prop
import rebuild_handset_schematics as drawing
from sync_handset_schematic_rebuild import geometry
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'hardware/handset-rev-a/generated';OUT=Path('/tmp/handset-display-interface')
uid=lambda x:str(uuid.uuid5(uuid.NAMESPACE_URL,'handset-display-interface/'+x))
p.SwigPyIterator.next=p.SwigPyIterator.__next__
assert not (SRC/'display-interface-update.json').exists(),'Already installed; preserve later work'
OUT.mkdir(exist_ok=True);hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in SRC.iterdir() if f.is_file()}
for f in SRC.iterdir():
 if f.is_file() and f.suffix not in ('.lck','.prl'):shutil.copy2(f,OUT/f.name)
shutil.copytree(SRC/'Handset.pretty',OUT/'Handset.pretty',dirs_exist_ok=True)
drawing.OUT=OUT;spec={c['ref']:c for c in json.loads((SRC/'connectivity.json').read_text())};symbols={};instances={}
for path in SRC.glob('*.kicad_sch'):
 tree=parse(path.read_text())
 for s in children(child(tree,'lib_symbols'),'symbol'):symbols[str(s[1])]=s
 for s in children(tree,'symbol'):instances[str(prop(s,'Reference')[2])]=s
root=parse((SRC/'handset.kicad_sch').read_text());rootid=str(child(root,'uuid')[1]);sid=drawing.UID('display-interface')
lib=parse((SRC/'Handset.kicad_sym').read_text())
def symbol(name,pins):
 s=parse(f'(symbol "Handset:{name}" (pin_names (offset 0.508)) (in_bom yes) (on_board yes) (property "Reference" "U" (at 0 0 0) (effects (font (size 1 1)))) (property "Value" "{name}" (at 0 0 0) (effects (font (size 1 1)))))')
 left=[x for x in pins if x[2] not in ('output','tri_state','power_out')];right=[x for x in pins if x not in left];n=max(len(left),len(right));height=(n+1)*2.54
 s.append(parse(f'(symbol "{name}_0_1" (rectangle (start -15.24 5.08) (end 15.24 {-height}) (stroke (width 0.254) (type default)) (fill (type background))))'))
 unit=['symbol',Q(name+'_1_1')]
 for group,x,angle in [(left,-20.32,0),(right,20.32,180)]:
  for i,(num,label,typ) in enumerate(group):unit.append(parse(f'(pin {typ} line (at {x} {-i*2.54} {angle}) (length 5.08) (name "{label}" (effects (font (size 1 1)))) (number "{num}" (effects (font (size 1 1)))))'))
 s.append(unit);symbols['Handset:'+name]=s;local=copy.deepcopy(s);local[1]=Q(name);lib.append(local);return 'Handset:'+name
ldo=symbol('TPS7A2030PDBVR',[(1,'IN','power_in'),(2,'GND','power_in'),(3,'EN','input'),(4,'NC','no_connect'),(5,'OUT','power_out')])
forward=symbol('SN74LVC244APWR',[(1,'~{1OE}','input'),(2,'1A1','input'),(3,'2Y4','tri_state'),(4,'1A2','input'),(5,'2Y3','tri_state'),(6,'1A3','input'),(7,'2Y2','tri_state'),(8,'1A4','input'),(9,'2Y1','tri_state'),(10,'GND','power_in'),(11,'2A1','input'),(12,'1Y4','tri_state'),(13,'2A2','input'),(14,'1Y3','tri_state'),(15,'2A3','input'),(16,'1Y2','tri_state'),(17,'2A4','input'),(18,'1Y1','tri_state'),(19,'~{2OE}','input'),(20,'VCC','power_in')])
ret=symbol('SN74LVC2G125DCUR',[(1,'~{1OE}','input'),(2,'1A','input'),(3,'2Y','tri_state'),(4,'GND','power_in'),(5,'2A','input'),(6,'1Y','tri_state'),(7,'~{2OE}','input'),(8,'VCC','power_in')])
i2c=symbol('TCA9406DCUR',[(1,'SDA_B','bidirectional'),(2,'GND','power_in'),(3,'VCCA','power_in'),(4,'SDA_A','bidirectional'),(5,'SCL_A','bidirectional'),(6,'OE','input'),(7,'VCCB','power_in'),(8,'SCL_B','bidirectional')])
(OUT/'Handset.kicad_sym').write_text(dump(lib)+'\n')
added=[]
def add(ref,value,libid,fp,nets,x,y):
 assert ref not in spec;added.append(ref)
 spec[ref]=dict(ref=ref,value=value,libid=libid,footprint=fp,nets={str(k):v for k,v in nets.items()},x=x,y=y,side='F',angle=0,sheet='display-interface')
 instances[ref]=parse(f'(symbol (lib_id "{libid}") (at 0 0 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid(ref)}") (property "Reference" "{ref}" (at 0 0 0) (effects (font (size 1 1)))) (property "Value" "{value}" (at 0 0 0) (effects (font (size 1 1)))) (property "Footprint" "{fp}" (at 0 0 0) (effects (font (size 1 1)) (hide yes))) (instances (project "handset" (path "/{rootid}/{sid}" (reference "{ref}") (unit 1)))))')
rail='LCD_3V0'
add('U28','TPS7A2030PDBVR',ldo,'Package_TO_SOT_SMD:SOT-23-5',{1:'+5V_RF',2:'GND',3:'SYS_EN',4:None,5:rail},80,55)
fn={1:'GND',19:'GND',10:'GND',20:rail,15:'GND',17:'GND',5:None,3:None}
for a,z,net in [(2,18,'SPI_SCK'),(4,16,'SPI_MOSI'),(6,14,'LCD_CS'),(8,12,'LCD_DC'),(11,9,'LCD_RESET'),(13,7,'TOUCH_RESET')]:fn[a]=net;fn[z]='PANEL_'+net
add('U29','SN74LVC244APWR',forward,'Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm',fn,91,55)
add('U30','SN74LVC2G125DCUR',ret,'Package_SO:VSSOP-8_2.3x2mm_P0.5mm',{1:'LCD_CS',2:'PANEL_SPI_MISO',3:'TOUCH_IRQ',4:'GND',5:'PANEL_TOUCH_IRQ',6:'SPI_MISO',7:'GND',8:'+3V3'},79,73)
add('U31','TCA9406DCUR',i2c,'Package_SO:VSSOP-8_2.3x2mm_P0.5mm',{1:'I2C_SDA',2:'GND',3:rail,4:'PANEL_I2C_SDA',5:'PANEL_I2C_SCL',6:rail,7:'+3V3',8:'I2C_SCL'},79.8,66)
for ref,net,x,y,big in [('C84','+5V_RF',77.8,59,True),('C85',rail,81,59,True),('C86',rail,91,50,False),('C87','+3V3',79,77,False),('C88',rail,77.5,63,False),('C89','+3V3',81,63,False)]:
 add(ref,'4.7uF 10% X5R 25V' if big else '100nF 10% X7R 16V','Device:C','Capacitor_SMD:C_0603_1608Metric' if big else 'Capacitor_SMD:C_0402_1005Metric',{1:net,2:'GND'},x,y)
add('R80','100k 1%','Device:R','Resistor_SMD:R_0402_1005Metric',{1:'PANEL_SPI_MISO',2:'GND'},79,80)
add('R81','100k 1%','Device:R','Resistor_SMD:R_0402_1005Metric',{1:rail,2:'PANEL_TOUCH_IRQ'},82,77)
for ref in added:
 c=spec[ref]
 mpn=c['value'] if ref.startswith('U') else ('GRM188R61E475KE11D' if ref in ['C84','C85'] else 'GRM155R71C104KA88D' if ref.startswith('C') else 'RC0402FR-07100KL')
 c.update(mpn=mpn,manufacturer='Texas Instruments' if ref.startswith('U') else 'Murata' if ref.startswith('C') else 'Yageo')
 instances[ref].append(parse(f'(property "MPN" "{mpn}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))'))
with (OUT/'display-interface-bom.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['Reference','Manufacturer','MPN','Value','Footprint','Qualification'])
 for ref in added:
  c=spec[ref];w.writerow([ref,c['manufacturer'],c['mpn'],c['value'],c['footprint'],'Captured and placed; routing and assembly qualification pending'])
changes={} 
for pin,net in spec['J26']['nets'].items():
 if net=='+3V3':changes[('J26',pin)]=rail
 elif net in ['SPI_SCK','SPI_MOSI','SPI_MISO','LCD_CS','LCD_DC','LCD_RESET','TOUCH_RESET','TOUCH_IRQ','I2C_SDA','I2C_SCL']:changes[('J26',pin)]='PANEL_'+net
for ref in ['C47','C48']:changes[(ref,'1')]=rail
for (ref,pin),net in changes.items():spec[ref]['nets'][pin]=net
# Redraw the existing display page with the same part identities and explicit domain names.
page=drawing.Sheet('display','External display, touch and backlight',22,'Dedicated LCD_3V0 supply and translated signals on display-interface. Backlight remains on +5V_RF. Purchased CTP and timing qualification pending.',rootid,spec,instances,symbols)
page.place('J26',86.36,121.92);page.place('Q2',330.2,60.96)
pairs=defaultdict(list)
for ref,c in spec.items():
 if c['sheet']=='display' and ref not in ['J26','Q2']:pairs[tuple(c['nets'][k] for k in ['1','2'])].append(ref)
banks=[rs[j:j+3] for rs in pairs.values() for j in range(0,len(rs),3)]
for i,refs in enumerate(banks):page.bank(refs,180.34+(i%2)*101.6,101.6+(i//2)*33.02)
page.finish()
page=drawing.Sheet('display-interface','Display supply and signal translation',24,'Circuit capture and placement only. Route and qualify supplies, timing, startup and case cable. Do not fabricate.',rootid,spec,instances,symbols)
for ref,x,y in [('U28',55.88,63.5),('U29',157.48,63.5),('U30',254,63.5),('U31',350.52,63.5)]:page.place(ref,x,y)
for i,ref in enumerate(added[4:]):page.bank([ref],35.56+(i%4)*96.52,157.48+(i//4)*55.88)
# Compact ground labels prevent ground-symbol text overlapping adjacent IC pins.
for key,(pos,angle,net) in page.pins.items():
 if key.startswith(('U28.','U29.','U30.','U31.')) and net=='GND':
  end=(round(pos[0]-7.62,4),pos[1]);page.wire(pos,end);page.wired.add(key)
  page.tree.append(['global_label',Q('GND'),['shape','bidirectional'],['at',str(end[0]),str(end[1]),'0'],['effects',['font',['size','1','1']],['justify','right']],['uuid',Q(page.ident())]])
page.text('U29: 3.3 V tolerant inputs; outputs use LCD_3V0.\nU30: MISO OE follows host LCD_CS; IRQ buffer always enabled.\nU31: internal pull-ups; verify bus capacitance and touch option.\nU28: 5 V input provides headroom; qualify load and heat.',25.4,256.54,1)
page.finish()
root.append(parse(f'(sheet (at 213.36 365.76) (size 172.72 25.4) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0)) (uuid "{sid}") (property "Sheetname" "Display supply and translation" (at 213.36 363.22 0) (effects (font (size 1.2 1.2)) (justify left bottom))) (property "Sheetfile" "display-interface.kicad_sch" (at 213.36 393.7 0) (effects (font (size 1 1)) (justify left top))) (instances (project "handset" (path "/{rootid}" (page "24")))))'))
(OUT/'handset.kicad_sch').write_text(dump(root)+'\n')
subprocess.run(['kicad-cli','sch','export','netlist',str(OUT/'handset.kicad_sch'),'--format','kicadxml','-o',str(OUT/'netlist.xml')],check=True)
xml=ET.parse(OUT/'netlist.xml').getroot();native={(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in xml.findall('./nets/net') for n in net.findall('node')}
b=p.LoadBoard(str(SRC/'handset.kicad_pcb'));before=geometry(b);b.BuildConnectivity();fps={f.GetReference():f for f in b.GetFootprints()};renamed={}
def netobj(name):
 n=b.FindNet(name)
 if not n:n=p.NETINFO_ITEM(b,name);b.Add(n)
 return n
# Changed pad copper must be isolated from all unchanged pads; preserve shape while renaming its local group.
for (ref,pin),net in changes.items():
 pad=next(x for x in fps[ref].Pads() if x.GetNumber()==pin)
 items=list(b.GetConnectivity().GetConnectedItems(pad))
 for item in items:
  if isinstance(item,p.PAD):
   key=(item.GetParentFootprint().GetReference(),item.GetNumber());assert changes.get(key)==net,(ref,pin,'shared copper',key)
 for item in items+[pad]:item.SetNet(netobj(net));renamed[item.m_Uuid.AsString()]=net
for ref in added:
 c=spec[ref];library,name=c['footprint'].split(':');fp=p.FootprintLoad('/usr/share/kicad/footprints/'+library+'.pretty',name);b.Add(fp);fp.SetReference(ref);fp.SetValue(c['value']);fp.SetFPID(p.LIB_ID(library,name));fp.SetPosition(p.VECTOR2I(p.FromMM(c['x']),p.FromMM(c['y'])));fp.Reference().SetLayer(p.F_Fab);fp.Value().SetVisible(False)
 path=p.KIID_PATH()
 for ident in [rootid,sid,uid(ref)]:path.push_back(p.KIID(ident))
 fp.SetPath(path);fp.SetSheetname('Display supply and signal translation');fp.SetSheetfile('display-interface.kicad_sch')
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
assert before['footprints'].items()<=after['footprints'].items()
for ident,g in before['copper'].items():
 expected=list(g)
 if ident in renamed:expected[7]=renamed[ident]
 assert expected==after['copper'][ident],ident
(OUT/'connectivity.json').write_text(json.dumps(list(spec.values()),indent=2)+'\n')
with (OUT/'placement.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec.values())
(OUT/'display-interface-update.json').write_text(json.dumps(dict(source_hashes=hashes,added_refs=added,changed_pads={ref+'.'+pin:net for (ref,pin),net in changes.items()},preserved_copper_items=len(before['copper']),fabrication_released=False),indent=2)+'\n')
