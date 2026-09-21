#!/usr/bin/env python3
"""Build an isolated, explicitly unreleased GPS/expansion engineering revision.

Never replaces the user's main board. KiCad remains responsible for net export,
zone fill, DRC and ERC. Pin changes remove obsolete copper on affected nets.
"""
import copy
import json
import math
from pathlib import Path
import shutil
import subprocess
import uuid
import xml.etree.ElementTree as ET
from cad_sexpr import Q, child, children, dump, parse, prop
import pcbnew

pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__
BASE = Path(__file__).resolve().parent
OUT = BASE / 'revF-gps-expansion'
OUT.mkdir(exist_ok=True)
uid = lambda: str(uuid.uuid4())
root = parse((BASE / 'owasso1.kicad_sch').read_text())
root_id = child(root, 'uuid')[1]
symbols = {str(prop(s, 'Reference')[2]): s for s in children(root, 'symbol')}
libs = {str(s[1]): s for s in children(child(root, 'lib_symbols'), 'symbol')}
board = pcbnew.LoadBoard(str(BASE / 'owasso1.kicad_pcb'))
fps = {f.GetReference(): f for f in board.GetFootprints()}
changes = []

def point(node):
    return tuple(round(float(x), 4) for x in node[1:3])

def pin_positions(symbol, lib):
    sx, sy = point(child(symbol, 'at'))
    angle = math.radians(float(child(symbol, 'at')[3]))
    pins = []
    for unit in children(lib, 'symbol'):
        for p in children(unit, 'pin'):
            x, y = point(child(p, 'at'))
            pos = (round(sx + x*math.cos(angle) + y*math.sin(angle), 4),
                   round(sy + x*math.sin(angle) - y*math.cos(angle), 4))
            pins.append((str(child(p, 'number')[1]), pos, p))
    return pins

def label(net, x, y, justify='right'):
    return parse(f'(label {json.dumps(net)} (at {x} {y} 0) (effects (font (size 1 1)) (justify {justify} bottom)) (uuid "{uid()}"))')

def wire(x, y, x2, y2):
    return parse(f'(wire (pts (xy {x} {y}) (xy {x2} {y2})) (stroke (width 0) (type default)) (uuid "{uid()}"))')

def set_pin(ref, number, net):
    s = symbols[ref]
    p = next(pos for n, pos, _ in pin_positions(s, libs[str(child(s, 'lib_id')[1])]) if n == str(number))
    connected = {p}
    removed = []
    for w in children(root, 'wire'):
        pts = [point(t) for t in children(child(w, 'pts'), 'xy')]
        if p in pts:
            connected.update(pts)
            removed.append(w)
    for n in root:
        if isinstance(n, list) and n and n[0] in ('label', 'no_connect') and point(child(n, 'at')) in connected:
            removed.append(n)
    for n in removed:
        root.remove(n)
    x, y = p
    if net is None:
        root.append(parse(f'(no_connect (at {x} {y}) (uuid "{uid()}"))'))
    else:
        root.extend([wire(x, y, x-5.08, y), label(net, x-5.08, y)])
    changes.append({'ref':ref, 'pin':str(number), 'net':net})

# Free general-purpose GPIOs. GPIO35/36/37 are occupied by octal PSRAM.
for pin, net in {3:'MCU_EN',4:'GPS_HOST_TX',5:'GPS_HOST_RX',6:'GPS_PPS',
                 7:'EXP_CS',8:'EXP_IRQ',9:'LCD_RESET',10:'TP_RESET',12:'TOUCH_INT',
                 16:None,20:'SPI_SCK',21:'SPI_MOSI',22:'SPI_MISO',
                 23:'SX1262_CS',24:'CC1101_CS',25:'CC1101_GDO0',26:None,
                 27:'MCU_BOOT',28:None,29:None,30:None}.items():
    set_pin('U1', pin, net)
# Correct SO16 address pins and P0-P7. Pin 13 remains optional polling IRQ.
for pin, net in {1:'GND',2:'GND',3:'GND',4:'KEY_R1',5:'KEY_R2',6:'KEY_R3',
                 7:'KEY_R4',9:'KEY_C1',10:'KEY_C2',11:'KEY_C3',12:'KEY_C4'}.items():
    set_pin('U2', pin, net)
# Separate protected pack/charger rail from switched system rail. In particular,
# never connect USB VBUS directly to a cell through the slide switch.
for ref, pin in [('J13',1),('U3',5),('C2',1),('U4',5),('U6',3),('SW1',1)]:
    set_pin(ref, pin, 'BAT_CHARGE')

# Correct the three legacy connector-shaped symbols to their actual pad sets.
# Keep existing pin coordinates so this does not disturb other schematic wiring.
contract_libs = []
for ref in ('J10','USB1','U3'):
    s = symbols[ref]
    old = libs[str(child(s,'lib_id')[1])]
    lib = copy.deepcopy(old)
    name = ref+'_contract'
    libid = 'owasso1-review:'+name
    actual = {p.GetNumber() for p in fps[ref].Pads() if p.GetNumber()}
    lib[1] = Q(libid)
    for sub in children(lib,'symbol'):
        sub[1] = Q(name+'_'+str(sub[1]).rsplit('_',2)[-2]+'_'+str(sub[1]).rsplit('_',1)[-1])
        sub[:] = [p for p in sub if not (isinstance(p,list) and p and p[0]=='pin' and str(child(p,'number')[1]) not in actual)]
    if ref=='U3':
        sub = next(su for su in children(lib,'symbol') if children(su,'pin'))
        template = copy.deepcopy(children(sub,'pin')[-1])
        child(template,'number')[1] = Q('9')
        child(template,'name')[1] = Q('EP_GND')
        child(template,'at')[2] = str(min(float(child(p,'at')[2]) for p in children(sub,'pin'))-2.54)
        sub.append(template)
    child(s,'lib_id')[1] = Q(libid)
    child(root,'lib_symbols').append(lib)
    libs[libid] = lib
    export = copy.deepcopy(lib)
    export[1] = Q(name)
    contract_libs.append(export)
    if ref=='U3':
        set_pin(ref,9,'GND')

# Remove only genuinely orphaned legacy annotations, not connected NC flags.
pinpoints = {pos for s in symbols.values() for _,pos,_ in pin_positions(s,libs[str(child(s,'lib_id')[1])])}
wirepoints = {point(p) for w in children(root,'wire') for p in children(child(w,'pts'),'xy')}
root[:] = [n for n in root if not (isinstance(n,list) and n and
    ((n[0]=='no_connect' and (point(child(n,'at')) not in pinpoints or point(child(n,'at')) in wirepoints)) or
     (n[0]=='label' and point(child(n,'at')) not in pinpoints|wirepoints)))]

# Restore library-qualified metadata using actual placed footprints, not stale
# schematic choices. This does NOT assert that the legacy part selection is valid.
for ref, fp in fps.items():
    if ref not in symbols:
        continue
    s = symbols[ref]
    name = str(fp.GetFPID().GetLibItemName())
    oldlib = str(prop(s, 'Footprint')[2]).split(':')[0]
    if (BASE / 'owasso1.pretty' / (name+'.kicad_mod')).exists():
        libname = 'owasso1'
    else:
        matches = list(Path('/usr/share/kicad/footprints').glob('*.pretty/'+name+'.kicad_mod'))
        preferred = [p for p in matches if p.parent.stem == oldlib]
        if not matches:
            raise RuntimeError(f'No library footprint for {ref}: {name}')
        libname = (preferred or matches)[0].parent.stem
    fpid = libname + ':' + name
    prop(s, 'Footprint')[2] = Q(fpid)
    fp.SetFPID(pcbnew.LIB_ID(libname, name))
    symbol_id = str(child(s, 'uuid')[1])
    s[:] = [n for n in s if not (isinstance(n,list) and n and n[0]=='instances')]
    s.append(parse(f'(instances (project "owasso1" (path "/{root_id}" (reference "{ref}") (unit 1))))'))
    fp.SetPath(pcbnew.KIID_PATH('/'+str(root_id)+'/'+symbol_id))

# Readable new sheet with true GPS pin types. Legacy root remains preserved.
sheet_id, child_id = uid(), uid()
sheet = parse(f'(kicad_sch (version 20250610) (generator "eeschema") (generator_version "10.0") (uuid "{child_id}") (paper "A3") (title_block (title "Owasso1 GPS, rear expansion and MCU support") (date "2026-09-20") (rev "F - ENGINEERING ONLY")) (lib_symbols))')
new_parts = []
libcache = {}

def library_symbol(libid):
    libname, name = libid.split(':')
    if libname not in libcache:
        libcache[libname] = parse((Path('/usr/share/kicad/symbols')/(libname+'.kicad_sym')).read_text())
    syms = {str(s[1]):s for s in children(libcache[libname], 'symbol')}
    result = copy.deepcopy(syms[name])
    if child(result, 'extends'):
        parent = copy.deepcopy(syms[str(child(result,'extends')[1])])
        for block in children(parent, 'symbol'):
            block[1] = Q(str(block[1]).replace(str(parent[1]),name,1))
            result.append(block)
        result.remove(child(result,'extends'))
    result[1] = Q(libid)
    return result

def add(ref, libid, value, footprint, connections, schpos, pcbpos, angle=0, side='B', mpn=None):
    lib = library_symbol(libid)
    if not any(s[1]==libid for s in children(child(sheet,'lib_symbols'),'symbol')):
        child(sheet,'lib_symbols').append(lib)
    x,y = schpos
    sid = uid()
    s = parse(f'(symbol (lib_id "{libid}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{sid}") (property "Reference" "{ref}" (at {x} {y-5.08} 0) (effects (font (size 1.27 1.27)))) (property "Value" {json.dumps(value)} (at {x} {y+5.08} 0) (effects (font (size 1 1)))) (property "Footprint" "{footprint}" (at {x} {y} 0) (effects (font (size 1 1)) (hide yes))) (instances (project "owasso1" (path "/{root_id}/{sheet_id}" (reference "{ref}") (unit 1)))))')
    if mpn:
        s.append(parse(f'(property "MPN" "{mpn}" (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))'))
    sheet.append(s)
    if ref in ('U9','U10','J16'):
        bounds = [pos[1] for _,pos,_ in pin_positions(s,lib)]
        child(prop(s,'Reference'),'at')[2] = str(min(bounds)-7.62)
        child(prop(s,'Value'),'at')[2] = str(max(bounds)+7.62)
    seen = set()
    for n,(px,py),pin in pin_positions(s,lib):
        net = connections.get(n)
        if (px,py) in seen:
            continue
        seen.add((px,py))
        if net:
            a = float(child(pin,'at')[3])
            dx,dy = round(-5.08*math.cos(math.radians(a)),4), round(5.08*math.sin(math.radians(a)),4)
            sheet.extend([wire(px,py,px+dx,py+dy),label(net,px+dx,py+dy,'right' if dx<0 else 'left')])
        else:
            sheet.append(parse(f'(no_connect (at {px} {py}) (uuid "{uid()}"))'))
    libname, name = footprint.split(':')
    directory = BASE/'owasso1.pretty' if libname=='owasso1' else Path('/usr/share/kicad/footprints')/(libname+'.pretty')
    fp = pcbnew.FootprintLoad(str(directory),name)
    if fp is None:
        raise RuntimeError(f'Cannot load {footprint}')
    board.Add(fp)
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetFPID(pcbnew.LIB_ID(libname,name))
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(pcbpos[0]),pcbnew.FromMM(pcbpos[1])))
    if side=='B':
        fp.Flip(fp.GetPosition(),pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(angle)
    fp.SetPath(pcbnew.KIID_PATH('/'+str(root_id)+'/'+sheet_id+'/'+sid))
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    if mpn:
        field = pcbnew.PCB_FIELD(fp,pcbnew.FIELD_T_USER,'MPN')
        field.SetText(mpn)
        field.SetVisible(False)
        fp.Add(field)
        field.thisown = False
    fps[ref] = fp
    new_parts.append({'ref':ref,'value':value,'footprint':footprint,'nets':connections,'mpn':mpn})

R='Resistor_SMD:R_0603_1608Metric'
C='Capacitor_SMD:C_0603_1608Metric'
# UART GPS: no backup battery; V_BCKP open per integration manual R05.
add('U9','RF_GPS:MAX-M10S','MAX-M10S-00B-01','RF_GPS:ublox_MAX',
    {'1':'GND','2':'GPS_TX','3':'GPS_RX','4':'GPS_PPS','7':'3V3','8':'3V3','10':'GND','11':'GPS_ANT','12':'GND'},
    (63.5,63.5),(105,124),angle=180,mpn='MAX-M10S-00B-01')
add('J15','Connector:Conn_Coaxial','GPS PASSIVE ANTENNA','Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical',
    {'1':'GPS_ANT','2':'GND'},(116.84,63.5),(96.5,127),mpn='U.FL-R-SMT-1(10)')
add('C5','Device:C','10uF 10V X5R',C,{'1':'3V3','2':'GND'},(33.02,109.22),(114,120))
add('C6','Device:C','100nF 10V X7R',C,{'1':'3V3','2':'GND'},(58.42,109.22),(114,117))
add('R6','Device:R','1k',R,{'1':'GPS_HOST_TX','2':'GPS_RX'},(88.9,109.22),(113,130))
add('R7','Device:R','1k',R,{'1':'GPS_TX','2':'GPS_HOST_RX'},(116.84,109.22),(116,132))
# Keyed, locking rear wire-to-board connector, power-off swaps only.
add('J16','Connector_Generic:Conn_01x10','REAR EXPANSION - POWER OFF TO SWAP',
    'Connector_JST:JST_GH_BM10B-GHS-TBT_1x10-1MP_P1.25mm_Vertical',
    dict(zip(map(str,range(1,11)),['GND','EXP_3V3','EXP_SCL','EXP_SDA','EXP_SCK','EXP_MOSI','EXP_MISO','EXP_CS_PORT','EXP_IRQ_PORT','GND'])),
    (208.28,60.96),(134,119),mpn='BM10B-GHS-TBT(LF)(SN)')
# Explicit custom symbol pin contract for TPS2553DBVR from TI SLVS841F p5.
tps = parse('(symbol "Owasso:TPS2553DBVR" (pin_names (offset 0.5)) (in_bom yes) (on_board yes) (property "Reference" "U" (at 0 10.16 0) (effects (font (size 1.27 1.27)))) (property "Value" "TPS2553DBVR" (at 0 -10.16 0) (effects (font (size 1.27 1.27)))) (symbol "TPS2553DBVR_0_1" (rectangle (start -7.62 7.62) (end 7.62 -7.62) (stroke (width 0.254) (type default)) (fill (type background)))) (symbol "TPS2553DBVR_1_1"))')
for n,name,typ,x,y,a in [('1','IN','power_in',-10.16,5.08,0),('2','GND','power_in',0,-10.16,90),('3','EN','input',-10.16,0,0),('4','~{FAULT}','open_collector',10.16,0,180),('5','ILIM','passive',10.16,-5.08,180),('6','OUT','power_out',10.16,5.08,180)]:
    children(tps,'symbol')[-1].append(parse(f'(pin {typ} line (at {x} {y} {a}) (length 2.54) (name "{name}" (effects (font (size 1 1)))) (number "{n}" (effects (font (size 1 1)))))'))
tps[1] = Q('TPS2553DBVR')
libcache['Owasso']=['kicad_symbol_lib',tps]
add('U10','Owasso:TPS2553DBVR','TPS2553DBVR','Package_TO_SOT_SMD:SOT-23-6',
    {'1':'3V3','2':'GND','3':'3V3','5':'EXP_ILIM','6':'EXP_3V3'},(162.56,60.96),(122,119),mpn='TPS2553DBVR')
add('R14','Device:R','232k 1%',R,{'1':'EXP_ILIM','2':'GND'},(162.56,109.22),(122,124))
add('C8','Device:C','1uF 10V X7R',C,{'1':'3V3','2':'GND'},(187.96,109.22),(118,119))
add('C9','Device:C','10uF 10V X5R',C,{'1':'EXP_3V3','2':'GND'},(213.36,109.22),(125,115))
for i,(src,dst) in enumerate([('I2C_SCL','EXP_SCL'),('I2C_SDA','EXP_SDA'),('SPI_SCK','EXP_SCK'),('SPI_MOSI','EXP_MOSI'),('SPI_MISO','EXP_MISO'),('EXP_CS','EXP_CS_PORT'),('EXP_IRQ','EXP_IRQ_PORT')]):
    add('R'+str(15+i),'Device:R','33',R,{'1':src,'2':dst},(259.08+(i%3)*40.64,48.26+(i//3)*30.48),(127+i*2.5,128.5),angle=90)
# MCU boot/reset, bus pullups and missing bypass capacitors.
for ref,value,con,sp,pp in [
    ('R8','10k',{'1':'3V3','2':'MCU_EN'},(30.48,172.72),(108,68)),
    ('R9','10k',{'1':'3V3','2':'MCU_BOOT'},(60.96,172.72),(137,84.5)),
    ('R10','4.7k',{'1':'3V3','2':'I2C_SCL'},(91.44,172.72),(130,83.5)),
    ('R11','4.7k',{'1':'3V3','2':'I2C_SDA'},(121.92,172.72),(133,83.5)),
    ('R12','10k',{'1':'3V3','2':'EXP_CS'},(152.4,172.72),(145,128.5)),
    ('R13','10k',{'1':'3V3','2':'EXP_IRQ'},(182.88,172.72),(148,128.5))]:
    add(ref,'Device:R',value,R,con,sp,pp)
for ref,value,con,sp,pp in [
    ('C7','1uF 10V X7R',{'1':'MCU_EN','2':'GND'},(30.48,218.44),(108,71)),
    ('C10','100nF 10V X7R',{'1':'3V3','2':'GND'},(60.96,218.44),(175,151)),
    ('C11','100nF 10V X7R',{'1':'3V3','2':'GND'},(91.44,218.44),(108,65)),
    ('C12','100nF 10V X7R',{'1':'3V3','2':'GND'},(121.92,218.44),(161,54))]:
    add(ref,'Device:C',value,C,con,sp,pp)
add('SW18','Switch:SW_Push','BOOT','Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2',{'1':'MCU_BOOT','2':'GND'},(162.56,218.44),(146,96))
add('SW19','Switch:SW_Push','RESET','Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2',{'1':'MCU_EN','2':'GND'},(200.66,218.44),(106,77))

external = ['GND','3V3','MCU_EN','MCU_BOOT','GPS_HOST_TX','GPS_HOST_RX','GPS_PPS','EXP_CS','EXP_IRQ','I2C_SCL','I2C_SDA','SPI_SCK','SPI_MOSI','SPI_MISO']
parent_sheet = parse(f'(sheet (at 279.4 30.48) (size 81.28 91.44) (fields_autoplaced) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0)) (uuid "{sheet_id}") (property "Sheetname" "GPS and rear expansion" (at 279.4 29.21 0) (effects (font (size 1.27 1.27)) (justify left bottom))) (property "Sheetfile" "gps-expansion.kicad_sch" (at 279.4 123.19 0) (effects (font (size 1.27 1.27)) (justify left top))) (instances (project "owasso1" (path "/{root_id}" (page "2")))))')
for i,net in enumerate(external):
    y = round(38.1+i*5.08,4)
    parent_sheet.append(parse(f'(pin "{net}" bidirectional (at 279.4 {y} 180) (effects (font (size 1 1)) (justify left)) (uuid "{uid()}"))'))
    root.extend([wire(279.4,y,274.32,y),label(net,274.32,y)])
    cy = round(139.7+i*7.62,4)
    sheet.append(parse(f'(hierarchical_label "{net}" (shape bidirectional) (at 340.36 {cy} 0) (effects (font (size 1 1)) (justify left)) (uuid "{uid()}"))'))
    sheet.extend([wire(340.36,cy,335.28,cy),label(net,335.28,cy)])
root.append(parent_sheet)
sheet.append(parse(f'(text "PASSIVE GNSS ANTENNA ONLY. V_BCKP open: cold start after power-off.\nRear port: 3.3V logic, 50mA module budget; no hot swap or external power.\nENGINEERING REVISION: legacy power and radio blockers remain. DO NOT FABRICATE." (at 20.32 259.08 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))'))

(OUT/'owasso1.kicad_sch').write_text(dump(root)+'\n')
(OUT/'gps-expansion.kicad_sch').write_text(dump(sheet)+'\n')
(OUT/'owasso1-review.kicad_sym').write_text(dump(['kicad_symbol_lib',['version','20241209'],['generator',Q('kicad_symbol_editor')]]+contract_libs)+'\n')
(OUT/'sym-lib-table').write_text('(sym_lib_table (lib (name "owasso1-review") (type "KiCad") (uri "${KIPRJMOD}/owasso1-review.kicad_sym") (options "") (descr "Explicit legacy pad contracts; electrical review still required")))\n')
shutil.copy2(BASE/'owasso1.kicad_pro',OUT/'owasso1.kicad_pro')
shutil.copy2(BASE/'fp-lib-table',OUT/'fp-lib-table')
shutil.copytree(BASE/'owasso1.pretty',OUT/'owasso1.pretty',dirs_exist_ok=True)
subprocess.run(['kicad-cli','sch','export','netlist','--format','kicadxml','-o',str(OUT/'netlist.xml'),str(OUT/'owasso1.kicad_sch')],check=True)
xml = ET.parse(OUT/'netlist.xml').getroot()
mapping = {}
for n in xml.findall('nets/net'):
    name = n.attrib['name']
    for p in n.findall('node'):
        mapping[(p.attrib['ref'],p.attrib['pin'])] = name
netmap = {n.GetNetname():n for n in board.GetNetInfo().NetsByNetcode().values()}
for name in set(mapping.values()):
    if name not in netmap:
        item = pcbnew.NETINFO_ITEM(board,name)
        board.Add(item)
        netmap[name] = item
affected = {'/3V3','/I2C_SCL','/I2C_SDA'}
for ref,fp in fps.items():
    for p in fp.Pads():
        number = p.GetNumber()
        if not number or ref.startswith('H'):
            continue
        target = mapping.get((ref,number),'')
        # Keep exposed charger pad grounded; missing legacy symbol pin is audited.
        if ref=='U3' and number=='9':
            target='/GND'
        old = p.GetNetname()
        if old != target:
            if old:
                affected.add(old)
            p.SetNet(netmap[target] if target else netmap[''])
obsolete_tracks = [track for track in board.GetTracks() if track.GetNetname() in affected]
removed_tracks = len(obsolete_tracks)
# A visible release warning, not a hidden DRC waiver.
txt = pcbnew.PCB_TEXT(board)
txt.SetText('REV F ENGINEERING - DO NOT FABRICATE')
txt.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(137),pcbnew.FromMM(190)))
txt.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1),pcbnew.FromMM(1)))
txt.SetLayer(pcbnew.Dwgs_User)
board.Add(txt)
# KiCad 10/Python 3.14: avoid creating SWIG objects after Remove().
for track in obsolete_tracks:
    board.Remove(track)
board.Save(str(OUT/'owasso1.kicad_pcb'))
(OUT/'changes.json').write_text(json.dumps({'pin_changes':changes,'new_parts':new_parts,'removed_obsolete_tracks':removed_tracks,'affected_nets':sorted(affected)},indent=2)+'\n')
print(f'Created {OUT}: {len(new_parts)} added parts; {removed_tracks} obsolete track segments removed. Routing and release review required.')
