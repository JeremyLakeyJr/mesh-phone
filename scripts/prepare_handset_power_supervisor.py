#!/usr/bin/env python3
"""Stage the separate charging supervisor; retain saved placement and copper geometry."""
import copy, csv, hashlib, json, shutil, subprocess, uuid
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as p
from cad_sexpr import Q, parse, dump, child, children, prop
import rebuild_handset_schematics as drawing
from sync_handset_schematic_rebuild import geometry
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hardware/handset-rev-a/generated'
OUT=Path('/tmp/handset-power-supervisor')
uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'handset-power-supervisor/'+s))
p.SwigPyIterator.next=p.SwigPyIterator.__next__

def main():
    assert not (SOURCE/'power-supervisor-update.json').exists(), 'Already installed; preserve subsequent edits.'
    OUT.mkdir(exist_ok=True)
    for f in SOURCE.iterdir():
        if f.is_file() and f.suffix not in ('.lck','.prl'):shutil.copy2(f,OUT/f.name)
    shutil.copytree(SOURCE/'Handset.pretty',OUT/'Handset.pretty',dirs_exist_ok=True)
    drawing.OUT=OUT
    spec={c['ref']:c for c in json.loads((SOURCE/'connectivity.json').read_text())}
    symbols={};instances={}
    for f in SOURCE.glob('*.kicad_sch'):
        tree=parse(f.read_text())
        for s in children(child(tree,'lib_symbols'),'symbol'):symbols[str(s[1])]=s
        for s in children(tree,'symbol'):instances[str(prop(s,'Reference')[2])]=s
    root=parse((SOURCE/'handset.kicad_sch').read_text());rootid=str(child(root,'uuid')[1])
    def stock(library,name,target=None):
        allsyms={str(s[1]):s for s in children(parse(Path('/usr/share/kicad/symbols',library+'.kicad_sym').read_text()),'symbol')}
        original=allsyms[name];parent=child(original,'extends')
        sym=copy.deepcopy(allsyms[str(parent[1])] if parent else original)
        old=str(sym[1]);new=target or library+':'+name
        for unit in children(sym,'symbol'):unit[1]=Q(str(unit[1]).replace(old+'_',new.split(':')[1]+'_',1))
        sym[1]=Q(new);symbols[new]=sym
        return new
    mcu=stock('MCU_ST_STM32G0','STM32G031G8Ux','Handset:STM32G031G8U6')
    ldo=stock('Regulator_Linear','AP2204K-1.5','Handset:TPS7A0230PDBV')
    prop(symbols[ldo],'Value')[2]=Q('TPS7A0230PDBVR')
    buf=stock('Interface','TCA9800');tp=stock('Connector','TestPoint')
    lib=parse((OUT/'Handset.kicad_sym').read_text());ls=copy.deepcopy(symbols[ldo]);ls[1]=Q(ldo.split(':')[1]);lib.append(ls)
    ms=copy.deepcopy(symbols[mcu]);ms[1]=Q(mcu.split(':')[1]);prop(ms,'Value')[2]=Q('STM32G031G8U6');symbols[mcu]=copy.deepcopy(ms);symbols[mcu][1]=Q(mcu);lib.append(ms)
    (OUT/'Handset.kicad_sym').write_text(dump(lib)+'\n')
    additions=[]
    def add(ref,value,libid,fp,nets,x,y,mpn,role):
        assert ref not in spec
        spec[ref]=dict(ref=ref,value=value,libid=libid,footprint=fp,nets=nets,x=x,y=y,side='B',angle=0,sheet='power-supervisor',mpn=mpn,role=role)
        instances[ref]=parse(f'''(symbol (lib_id "{libid}") (at 0 0 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid(ref)}")
        (property "Reference" "{ref}" (at 0 0 0) (effects (font (size 1 1))))
        (property "Value" "{value}" (at 0 0 0) (effects (font (size 1 1))))
        (property "Footprint" "{fp}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
        (property "MPN" "{mpn}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
        (instances (project "handset" (path "/{rootid}/{drawing.UID('power-supervisor')}" (reference "{ref}") (unit 1)))))''')
        additions.append(ref)
    aon='PWR_AON_3V0'
    nets={str(i):None for i in range(1,29)}
    nets.update({'3':aon,'4':'GND','5':'PWR_NRST','18':'PWR_HOST_SCL','19':'PWR_HOST_SDA','20':'PWR_SWDIO','21':'PWR_SWCLK','27':'CHG_I2C_SDA','28':'CHG_I2C_SCL'})
    add('U25','STM32G031G8U6',mcu,'Package_DFN_QFN:QFN-28_4x4mm_P0.5mm',nets,100,113,'STM32G031G8U6','Always-on charger supervisor; firmware not yet ported')
    add('U26','TPS7A0230PDBVR',ldo,'Package_TO_SOT_SMD:SOT-23-5',{'1':'VSYS','2':'GND','3':'VSYS','4':None,'5':aon},91,111,'TPS7A0230PDBVR','Always-on 3.0 V supply upstream of SW19')
    add('U27','TCA9800DGKR',buf,'Package_SO:VSSOP-8_3x3mm_P0.65mm',{'1':'+3V3','2':'I2C_SCL','3':'I2C_SDA','4':'GND','5':'+3V3','6':'PWR_HOST_SDA','7':'PWR_HOST_SCL','8':aon},111,115,'TCA9800DGKR','Powered-off host bus isolation; no B-side pull-ups')
    for ref,net,x,y,big in [('C77','VSYS',88,108,True),('C78',aon,94,108,True),('C79',aon,100,109,False),('C80',aon,103,109,True),('C81','+3V3',114,111,False),('C82',aon,106,111,False),('C83','PWR_NRST',98,118,False)]:
        add(ref,'4.7uF 10% X5R 25V' if big else '100nF 10% X7R 16V','Device:C','Capacitor_SMD:C_0603_1608Metric' if big else 'Capacitor_SMD:C_0402_1005Metric',{'1':net,'2':'GND'},x,y,'GRM188R61E475KE11D' if big else 'GRM155R71C104KA88D','Local bypass / reset filter')
    for ref,net,x,y in [('R76','CHG_I2C_SCL',96,113),('R77','CHG_I2C_SDA',96,115),('R78','PWR_NRST',98,120)]:
        add(ref,'10k 1%','Device:R','Resistor_SMD:R_0402_1005Metric',{'1':aon,'2':net},x,y,'RC0402FR-0710KL','Private bus or reset pull-up')
    for ref,net,x in [('TP2',aon,90),('TP3','GND',94),('TP4','PWR_SWDIO',98),('TP5','PWR_SWCLK',102),('TP6','PWR_NRST',106)]:
        add(ref,net,tp,'TestPoint:TestPoint_Pad_D1.0mm',{'1':net},x,125,'PCB copper','SWD service pad; VTREF is sense only')
    changes={('U3','7'):'CHG_I2C_SDA',('U3','8'):'CHG_I2C_SCL',('U24','6'):'CHG_I2C_SCL',('U24','7'):'CHG_I2C_SDA',('U24','8'):aon,('C60','1'):aon,('R66','1'):aon,('R69','1'):aon}
    for (ref,pin),net in changes.items():spec[ref]['nets'][pin]=net
    for name in ('power','power-control','usb-detect','usb-input'):
        tree=parse((OUT/(name+'.kicad_sch')).read_text())
        for lab in children(tree,'global_label'):
            net=str(lab[1]);x,y=map(float,child(lab,'at')[1:3])
            if name=='power' and net in ('I2C_SCL','I2C_SDA'):lab[1]=Q('CHG_'+net)
            if name=='power-control' and x<150:
                if net in ('I2C_SCL','I2C_SDA'):lab[1]=Q('CHG_'+net)
                if net=='+3V3':lab[1]=Q(aon)
            if name in ('usb-detect','usb-input') and net=='+3V3':lab[1]=Q(aon)
        (OUT/(name+'.kicad_sch')).write_text(dump(tree)+'\n')
    page=drawing.Sheet('power-supervisor','Always-on charging supervisor',23,'Separate supervisor selected. U3 remains the charger. Main host powers off at SW19. Circuit capture only; routing, STM32 firmware and fault qualification pending.',rootid,spec,instances,symbols)
    page.place('U25',203.2,99.06);page.place('U26',60.96,66.04);page.place('U27',337.82,76.2)
    page.bank(['C77'],30.48,137.16);page.bank(['C78','C79','C80'],81.28,137.16)
    page.bank(['C81'],299.72,137.16);page.bank(['C82'],350.52,137.16)
    for ref,x in [('R76',50.8),('R77',116.84),('R78',182.88),('C83',248.92)]:page.bank([ref],x,198.12)
    for ref,x in [('TP2',40.64),('TP3',106.68),('TP4',172.72),('TP5',238.76),('TP6',304.8)]:page.place(ref,x,236.22)
    page.text('I2C1: PB8/PB7 AF6 -> charger 0x6A + expander 0x41.\nI2C2: remap PA9/PA10 to PA11/PA12, AF6.\nHost slave address 0x42 reserved; protocol not implemented.',157.48,160.02,1)
    page.text('TCA9800 B side: NO external/internal MCU pull-ups.\nA-side pull-ups are on switched +3V3. EN follows +3V3.\nDebug VTREF is sense only; never power from debugger.',279.4,99.06,1)
    for ref,x,y in [('U25',175.26,60.96),('U27',307.34,48.26)]:
        inst=next(i for i in children(page.tree,'symbol') if str(prop(i,'Reference')[2])==ref)
        for name,dy in [('Reference',0),('Value',2.54)]:child(prop(inst,name),'at')[1:]=[str(x),str(y+dy),'0']
    page.finish()
    sh=copy.deepcopy(children(root,'sheet')[0]);child(sh,'uuid')[1]=Q(page.id);child(sh,'at')[1:]=['25.4','365.76']
    prop(sh,'Sheetname')[2]=Q('Always-on charging supervisor');child(prop(sh,'Sheetname'),'at')[1:]=['25.4','363.22','0']
    prop(sh,'Sheetfile')[2]=Q('power-supervisor.kicad_sch');child(prop(sh,'Sheetfile'),'at')[1:]=['25.4','393.7','0']
    child(child(child(child(sh,'instances'),'project'),'path'),'page')[1]=Q('23');root.append(sh)
    (OUT/'handset.kicad_sch').write_text(dump(root)+'\n')
    subprocess.run(['kicad-cli','sch','export','netlist',str(OUT/'handset.kicad_sch'),'--format','kicadxml','-o',str(OUT/'netlist.xml')],check=True)
    xml=ET.parse(OUT/'netlist.xml').getroot();native={(nd.get('ref'),nd.get('pin')):nt.get('name') for nt in xml.findall('./nets/net') for nd in nt.findall('node')}
    for c in spec.values():
        for pin,net in c['nets'].items():
            actual=native.get((c['ref'],pin));assert actual==net if net else actual and actual.startswith('unconnected-('),(c['ref'],pin,net,actual)
    b=p.LoadBoard(str(SOURCE/'handset.kicad_pcb'));before=geometry(b);fps={f.GetReference():f for f in b.GetFootprints()}
    def netobj(net):
        n=b.FindNet(net)
        if not n:n=p.NETINFO_ITEM(b,net);b.Add(n)
        return n
    # Discover only the existing local islands, never rename the whole host net.
    conn=b.GetConnectivity();groups=[]
    for start,new,expected in [('8',aon,{('U24','8'),('C60','1'),('R66','1'),('R69','1')}),('6','CHG_I2C_SCL',{('U3','8'),('U24','6')}),('7','CHG_I2C_SDA',{('U3','7'),('U24','7')})]:
        seed=next(pad for pad in fps['U24'].Pads() if pad.GetNumber()==start);pending=[seed];seen={};pads=set()
        while pending:
            item=pending.pop();ident=item.m_Uuid.AsString()
            if ident in seen:continue
            seen[ident]=item
            if isinstance(item,p.PAD):pads.add((item.GetParentFootprint().GetReference(),item.GetNumber()))
            pending.extend(conn.GetConnectedTracks(item));pending.extend(conn.GetConnectedPads(item))
        assert pads==expected,(new,pads,expected)
        groups.append((new,seen))
    renamed={}
    for net,items in groups:
        for ident,item in items.items():item.SetNet(netobj(net));renamed[ident]=net
    for ref in additions:
        c=spec[ref];lib,name=c['footprint'].split(':');f=p.FootprintLoad('/usr/share/kicad/footprints/'+lib+'.pretty',name);assert f
        f.SetReference(ref);f.SetValue(c['value']);f.SetFPID(p.LIB_ID(lib,name));b.Add(f);f.Flip(f.GetPosition(),False)
        f.SetAttributes(f.GetAttributes() & ~p.FP_EXCLUDE_FROM_BOM)
        f.Reference().SetLayer(p.B_Fab);f.Value().SetVisible(False);f.SetPosition(p.VECTOR2I(p.FromMM(c['x']),p.FromMM(c['y'])))
        path=p.KIID_PATH()
        for ident in (rootid,page.id,uid(ref)):path.push_back(p.KIID(ident))
        f.SetPath(path);f.SetSheetname('Always-on charging supervisor');f.SetSheetfile('power-supervisor.kicad_sch')
        f.SetField('MPN',c['mpn']);f.GetField('MPN').SetVisible(False)
        for pad in f.Pads():
            if pad.GetNumber():pad.SetNet(netobj(native[(ref,pad.GetNumber())]))
    p.SaveBoard(str(OUT/'handset.kicad_pcb'),b);shutil.copy2(SOURCE/'handset.kicad_pro',OUT/'handset.kicad_pro')
    after=geometry(p.LoadBoard(str(OUT/'handset.kicad_pcb')))
    assert before['footprints'].items()<=after['footprints'].items()
    for ident,g in before['copper'].items():
        expect=list(g)
        if ident in renamed:expect[7]=renamed[ident]
        assert expect==after['copper'][ident],ident
    (OUT/'connectivity.json').write_text(json.dumps(list(spec.values()),indent=2)+'\n')
    for name,fields,refs in [('placement.csv',['ref','value','footprint','x','y','side','angle','sheet'],list(spec)),('power-supervisor-bom.csv',['ref','value','mpn','footprint','role'],additions)]:
        with (OUT/name).open('w') as f:
            w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(spec[r] for r in refs)
    (OUT/'power-supervisor-update.json').write_text(json.dumps(dict(source_hashes={str(f.relative_to(SOURCE)):hashlib.sha256(f.read_bytes()).hexdigest() for f in SOURCE.rglob('*') if f.is_file() and f.suffix in ('.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym','.kicad_mod','.json','.csv')},added_refs=additions,components=len(spec),preserved_copper_items=len(before['copper']),renamed_local_items=renamed,fabrication_released=False,scope='Separate always-on charging supervisor capture and placement; unrouted; firmware and reset-fault shutdown unqualified'),indent=2)+'\n')
    print('Staged',len(additions),'new parts;',len(spec),'total; existing placement and copper geometry preserved.')
if __name__=='__main__':main()
