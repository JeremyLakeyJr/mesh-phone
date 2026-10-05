#!/usr/bin/env python3
"""Stage reset-default-off accessory power, fault interlock and signal isolation."""
import copy,csv,hashlib,json,shutil,subprocess,uuid
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as p
from cad_sexpr import Q,parse,dump,child,children,prop
import rebuild_handset_schematics as drawing
from sync_handset_schematic_rebuild import geometry
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'hardware/handset-rev-a/generated';OUT=Path('/tmp/handset-expansion')
uid=lambda name:str(uuid.uuid5(uuid.NAMESPACE_URL,'handset-expansion/'+name))
p.SwigPyIterator.next=p.SwigPyIterator.__next__
assert not (SRC/'expansion-update.json').exists(),'Already installed; preserve subsequent work'
OUT.mkdir(exist_ok=True)
hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in SRC.iterdir() if f.is_file() and f.suffix not in ('.lck','.prl')}
for f in SRC.iterdir():
 if f.is_file() and f.suffix not in ('.lck','.prl'):shutil.copy2(f,OUT/f.name)
shutil.copytree(SRC/'Handset.pretty',OUT/'Handset.pretty',dirs_exist_ok=True)
drawing.OUT=OUT
spec={c['ref']:c for c in json.loads((SRC/'connectivity.json').read_text())};symbols={};instances={}
for path in SRC.glob('*.kicad_sch'):
 tree=parse(path.read_text())
 for s in children(child(tree,'lib_symbols'),'symbol'):symbols[str(s[1])]=s
 for s in children(tree,'symbol'):instances[str(prop(s,'Reference')[2])]=s
root=parse((SRC/'handset.kicad_sch').read_text());rootid=str(child(root,'uuid')[1]);sid=drawing.UID('expansion-control')
lib=parse((SRC/'Handset.kicad_sym').read_text())
def symbol(name,pins):
 s=parse(f'(symbol "Handset:{name}" (pin_names (offset 0.508)) (in_bom yes) (on_board yes) (property "Reference" "U" (at 0 0 0) (effects (font (size 1 1)))) (property "Value" "{name}" (at 0 0 0) (effects (font (size 1 1)))))')
 left=[v for v in pins if v[2] not in ('output','open_collector') and not v[1].startswith('B')];right=[v for v in pins if v not in left]
 h=(max(len(left),len(right))+1)*2.54
 s.append(parse(f'(symbol "{name}_0_1" (rectangle (start -15.24 5.08) (end 15.24 {-h}) (stroke (width 0.254) (type default)) (fill (type background))))'))
 unit=['symbol',Q(name+'_1_1')]
 for group,x,angle in [(left,-20.32,0),(right,20.32,180)]:
  for i,(num,label,typ) in enumerate(group):unit.append(parse(f'(pin {typ} line (at {x} {-i*2.54} {angle}) (length 5.08) (name "{label}" (effects (font (size 1 1)))) (number "{num}" (effects (font (size 1 1)))))'))
 s.append(unit);symbols['Handset:'+name]=s;local=copy.deepcopy(s);local[1]=Q(name);lib.append(local);return 'Handset:'+name
io=symbol('TCA9537DGS',[(1,'P0','bidirectional'),(2,'P1','bidirectional'),(3,'P2','bidirectional'),(4,'P3','bidirectional'),(5,'GND','power_in'),(6,'~{RESET}','input'),(7,'~{INT}','open_collector'),(8,'SCL','input'),(9,'SDA','bidirectional'),(10,'VCC','power_in')])
bus=symbol('SN74CB3Q3245PW',[(1,'NC','no_connect'),(10,'GND','power_in'),(19,'~{OE}','input'),(20,'VCC','power_in')]+[(i+1,'A'+str(i),'passive') for i in range(1,9)]+[(19-i,'B'+str(i),'passive') for i in range(1,9)])
gate=symbol('SN74HCS10PW',[(1,'1A','input'),(2,'1B','input'),(13,'1C','input'),(12,'1Y','output'),(3,'2A','input'),(4,'2B','input'),(5,'2C','input'),(6,'2Y','output'),(9,'3A','input'),(10,'3B','input'),(11,'3C','input'),(8,'3Y','output'),(7,'GND','power_in'),(14,'VCC','power_in')])
(OUT/'Handset.kicad_sym').write_text(dump(lib)+'\n')
added=[]
def add(ref,value,libid,fp,nets,x,y,mpn,side='F'):
 assert ref not in spec;added.append(ref)
 spec[ref]=dict(ref=ref,value=value,libid=libid,footprint=fp,nets={str(k):v for k,v in nets.items()},x=x,y=y,side=side,angle=0,sheet='expansion-control',mpn=mpn,manufacturer='Texas Instruments' if ref.startswith('U') else 'Murata' if ref.startswith('C') else 'Yageo')
 instances[ref]=parse(f'(symbol (lib_id "{libid}") (at 0 0 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid(ref)}") (property "Reference" "{ref}" (at 0 0 0) (effects (font (size 1 1)))) (property "Value" "{value}" (at 0 0 0) (effects (font (size 1 1)))) (property "Footprint" "{fp}" (at 0 0 0) (effects (font (size 1 1)) (hide yes))) (property "MPN" "{mpn}" (at 0 0 0) (effects (font (size 1 1)) (hide yes))) (instances (project "handset" (path "/{rootid}/{sid}" (reference "{ref}") (unit 1)))))')
add('U33','TCA9537DGSR',io,'Package_SO:VSSOP-10_3x3mm_P0.5mm',{1:'EXP_PWR_EN',2:'EXP_FAULT_N',3:'EXP_IO_ARM',4:'EXP_GPIO_SPARE',5:'GND',6:'MCU_EN',7:None,8:'I2C_SCL',9:'I2C_SDA',10:'+3V3'},80,88.8,'TCA9537DGSR')
# TI calls DGS VSSOP; KiCad's compatible DGS land pattern is named MSOP-10.
spec['U33']['footprint']='Package_SO:MSOP-10_3x3mm_P0.5mm';prop(instances['U33'],'Footprint')[2]=Q(spec['U33']['footprint'])
channels=[('SCL','I2C_SCL'),('SDA','I2C_SDA'),('SCK','SPI_SCK'),('MOSI','SPI_MOSI'),('MISO','SPI_MISO'),('CS','EXP_CS'),('IRQ','EXP_IRQ')]
nets={1:None,9:'GND',10:'GND',11:'GND',19:'EXP_IO_OE_N',20:'+3V3'}
changes={('U14','3'):'EXP_PWR_EN'}
for i,(name,host) in enumerate(channels,1):
 nets[i+1]=host;nets[19-i]='EXP_SW_'+name;changes[('R'+str(19+i),'1')]='EXP_SW_'+name
add('U34','SN74CB3Q3245PWR',bus,'Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm',nets,78,101,'SN74CB3Q3245PWR')
add('U35','SN74HCS10PWR',gate,'Package_SO:TSSOP-14_4.4x5mm_P0.65mm',{1:'EXP_PWR_EN',2:'EXP_IO_ARM',13:'EXP_FAULT_N',12:'EXP_IO_OE_N',3:'GND',4:'GND',5:'GND',6:None,9:'GND',10:'GND',11:'GND',8:None,7:'GND',14:'+3V3'},78,94,'SN74HCS10PWR')
for ref,x,y in [('C91',83.5,86.5),('C92',83.5,97),('C93',83.5,91)]:
 add(ref,'100nF 10% X7R 16V','Device:C','Capacitor_SMD:C_0402_1005Metric',{1:'+3V3',2:'GND'},x,y,'GRM155R71C104KA88D')
for ref,value,mpn,n1,n2,x,y in [
 ('R83','4.7k 1%','RC0402FR-074K7L','EXP_PWR_EN','GND',83.5,94.5),
 ('R84','4.7k 1%','RC0402FR-074K7L','EXP_IO_ARM','GND',83.5,92.5),
 ('R85','100k 1%','RC0402FR-07100KL','EXP_GPIO_SPARE','GND',73,90),
 ('R86','220k 1%','RC0402FR-07220KL','+3V3','EXP_IO_OE_N',83.5,102),
 ('R87','10k 1%','RC0402FR-0710KL','EXP_3V3','GND',82,104)]:
 add(ref,value,'Device:R','Resistor_SMD:R_0402_1005Metric',{1:n1,2:n2},x,y,mpn,'B' if ref=='R87' else 'F')
for (ref,pin),net in changes.items():spec[ref]['nets'][pin]=net
spec['U15'].update(x=84,y=76,angle=0)  # Move unrouted ESD array to a clear escape area.
spec['R42'].update(value='10k 1%',mpn='RC0402FR-0710KL',manufacturer='Yageo')
inst=instances['R42'];field=next((x for x in children(inst,'property') if x[1]=='MPN'),None)
if field:field[2]=Q(spec['R42']['mpn'])
else:inst.append(parse('(property "MPN" "RC0402FR-0710KL" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))'))
# Redraw only the existing expansion sheet; part identities and all other sheets remain.
page=drawing.Sheet('protection','Protected external module port',20,'Port signals pass through U34 on expansion-control. U14 EN defaults low; fault drives U33 and the hardware signal interlock. No hot-plug approval.',rootid,spec,instances,symbols)
for ref,x,y in [('J16',76.2,81.28),('U14',187.96,71.12),('U15',289.56,71.12),('U16',375.92,71.12)]:page.place(ref,x,y)
passives=['R20','R21','R22','R23','R24','R25','R26','R41','R42','C40','C41']
for i,ref in enumerate(passives):page.bank([ref],35.56+(i%4)*99.06,157.48+(i//4)*38.1)
page.finish()
page=drawing.Sheet('expansion-control','Expansion power control and signal isolation',25,'TCA9537 0x49: P0 power, P1 fault, P2 IO arm, P3 unused input. MCU_EN low resets all ports to inputs. External pull-downs retain OFF.',rootid,spec,instances,symbols)
for ref,x,y in [('U33',66.04,63.5),('U34',203.2,63.5),('U35',335.28,63.5)]:page.place(ref,x,y)
for i,ref in enumerate(added[3:]):page.bank([ref],35.56+(i%4)*99.06,162.56+(i//4)*43.18)
# Share dense unused-gate grounds on a drawn bus instead of overlapping symbols.
ground_pins=[(key,pos) for key,(pos,angle,net) in page.pins.items() if key.startswith('U35.') and net=='GND']
bx=ground_pins[0][1][0]-3.81;ys=sorted(pos[1] for _,pos in ground_pins)
for key,pos in ground_pins:
 page.wire(pos,(bx,pos[1]));page.dot((bx,pos[1]));page.wired.add(key)
page.wire((bx,ys[0]),(bx,ys[-1]));gy=ys[len(ys)//2]
page.wire((bx,gy),(bx-12.7,gy));page.ground((bx-12.7,gy))
page.text('U35: /OE = NOT (EXP_PWR_EN AND EXP_IO_ARM AND EXP_FAULT_N).\nInitialize output latch to 0xF0 before direction 0xFA. Power-only 0xF1; armed 0xF5.\nFault is polled; no MCU GPIO/strap changes. A stuck host I2C bus requires hardware reset.\nNo rail-good sensor: qualify load/startup and share buses only after settling with fault clear.\nAccessory address 0x49 is reserved. Swap modules only with handset power off.',25.4,254,1)
page.finish()
root.append(parse(f'(sheet (at 401.32 365.76) (size 172.72 25.4) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0)) (uuid "{sid}") (property "Sheetname" "Expansion control and isolation" (at 401.32 363.22 0) (effects (font (size 1.2 1.2)) (justify left bottom))) (property "Sheetfile" "expansion-control.kicad_sch" (at 401.32 393.7 0) (effects (font (size 1 1)) (justify left top))) (instances (project "handset" (path "/{rootid}" (page "25")))))'))
(OUT/'handset.kicad_sch').write_text(dump(root)+'\n')
subprocess.run(['kicad-cli','sch','export','netlist',str(OUT/'handset.kicad_sch'),'--format','kicadxml','-o',str(OUT/'netlist.xml')],check=True)
xml=ET.parse(OUT/'netlist.xml').getroot();native={(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in xml.findall('./nets/net') for n in net.findall('node')}
b=p.LoadBoard(str(SRC/'handset.kicad_pcb'));before=geometry(b);b.BuildConnectivity();fps={f.GetReference():f for f in b.GetFootprints()}
def netobj(name):
 n=b.FindNet(name)
 if not n:n=p.NETINFO_ITEM(b,name);b.Add(n)
 return n
for pad in fps['U15'].Pads():
 assert all(isinstance(i,p.PAD) and i.m_Uuid==pad.m_Uuid for i in b.GetConnectivity().GetConnectedItems(pad)), 'ESD array must remain unrouted before relocation'
fps['U15'].SetOrientationDegrees(0)
fps['U15'].SetPosition(p.VECTOR2I(p.FromMM(84),p.FromMM(76)))
fps['U15'].Reference().SetLayer(p.B_Fab)
fps['J16'].Reference().SetLayer(p.B_Fab)  # Keep crowded connector silk clear of the ESD lands.
for (ref,pin),net in changes.items():
 pad=next(q for q in fps[ref].Pads() if q.GetNumber()==pin)
 assert all(isinstance(i,p.PAD) and i.m_Uuid==pad.m_Uuid for i in b.GetConnectivity().GetConnectedItems(pad)),('Refuse to rename routed pad',ref,pin)
 pad.SetNet(netobj(net))
fps['R42'].SetValue(spec['R42']['value']);fps['R42'].SetField('MPN',spec['R42']['mpn']);fps['R42'].GetField('MPN').SetVisible(False)
for ref in added:
 c=spec[ref];library,name=c['footprint'].split(':');fp=p.FootprintLoad('/usr/share/kicad/footprints/'+library+'.pretty',name);assert fp
 b.Add(fp);fp.SetReference(ref);fp.SetValue(c['value']);fp.SetFPID(p.LIB_ID(library,name))
 if c['side']=='B':fp.Flip(fp.GetPosition(),False)
 fp.SetPosition(p.VECTOR2I(p.FromMM(c['x']),p.FromMM(c['y'])));fp.Reference().SetLayer(p.B_Fab if c['side']=='B' else p.F_Fab);fp.Value().SetVisible(False)
 path=p.KIID_PATH()
 for ident in [rootid,sid,uid(ref)]:path.push_back(p.KIID(ident))
 fp.SetPath(path);fp.SetSheetname('Expansion control and isolation');fp.SetSheetfile('expansion-control.kicad_sch')
 fp.SetField('MPN',c['mpn']);fp.GetField('MPN').SetVisible(False)
 for pad in fp.Pads():
  if pad.GetNumber():pad.SetNet(netobj(native[ref,pad.GetNumber()]))
p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
after=geometry(b);assert before['copper']==after['copper']
for ref,g in before['footprints'].items():
 expected=list(g)
 if ref=='R42':expected[5]=spec[ref]['value']
 if ref=='U15':
  expected[1:4]=[p.FromMM(84),p.FromMM(76),0.0]
  expected[8]=[(v[0],v[1],v[2]-p.FromMM(5),v[3]+p.FromMM(1),v[4],v[5],v[6]) for v in expected[8]]
 assert expected==after['footprints'][ref],ref
for c in spec.values():
 for pin,net in c['nets'].items():
  actual=native.get((c['ref'],pin));assert actual==net if net else actual and actual.startswith('unconnected-('),(c['ref'],pin,net,actual)
(OUT/'connectivity.json').write_text(json.dumps(list(spec.values()),indent=2)+'\n')
with (OUT/'placement.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec.values())
with (OUT/'expansion-bom.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['Reference','Manufacturer','MPN','Value','Footprint','Qualification'])
 for ref in added+['R42']:
  c=spec[ref];w.writerow([ref,c['manufacturer'],c['mpn'],c['value'],c['footprint'],'Captured; hardware qualification pending'])
(OUT/'expansion-update.json').write_text(json.dumps(dict(source_hashes=hashes,added_refs=added,changed_pads={ref+'.'+pin:net for (ref,pin),net in changes.items()},changed_values={'R42':spec['R42']['value']},moved_existing_refs={'U15':{'from_mm':[89,75],'to_mm':[84,76],'from_angle':0,'to_angle':0,'reason':'Escape array signals clear of retained power and display copper; ESD path qualification pending'}},preserved_copper_items=len(before['copper']),fabrication_released=False),indent=2)+'\n')
print('Staged',OUT)
