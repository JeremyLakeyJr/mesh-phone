#!/usr/bin/env python3
"""Stage a reset-default-off second CE permission; never modify the saved board."""
import copy,csv,hashlib,json,shutil,subprocess,uuid
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as p
from cad_sexpr import Q,parse,dump,child,children,prop
import rebuild_handset_schematics as drawing
from sync_handset_schematic_rebuild import geometry
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hardware/handset-rev-a/generated'
OUT=Path('/tmp/handset-charge-inhibit')
uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'handset-charge-inhibit/'+s))
p.SwigPyIterator.next=p.SwigPyIterator.__next__

def main():
    assert not (SOURCE/'charge-inhibit-update.json').exists(),'Already installed; preserve later edits'
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
    rootid=str(child(parse((SOURCE/'handset.kicad_sch').read_text()),'uuid')[1])
    additions=[]
    def add(ref,template,value,nets,x,y,mpn,role):
        assert ref not in spec
        c=copy.deepcopy(spec[template]);c.update(ref=ref,value=value,nets=nets,x=x,y=y,mpn=mpn,role=role,sheet='power');spec[ref]=c
        inst=copy.deepcopy(instances[template]);child(inst,'uuid')[1]=Q(uid(ref))
        for pin in children(inst,'pin'):child(pin,'uuid')[1]=Q(uid(ref+'.'+str(pin[1])))
        prop(inst,'Reference')[2]=Q(ref);prop(inst,'Value')[2]=Q(value)
        for project in children(child(inst,'instances'),'project'):
            for path in children(project,'path'):child(path,'reference')[1]=Q(ref)
        field=next((v for v in children(inst,'property') if v[1]=='MPN'),None)
        if field:field[2]=Q(mpn)
        else:inst.append(parse(f'(property "MPN" "{mpn}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))'))
        instances[ref]=inst;additions.append(ref)
    add('Q8','Q5','AO3400A',{'1':'CHG_ARM','2':'GND','3':'CHG_CE_RETURN'},112,70,'AO3400A','Second series CE sink; default OFF during STM32 reset')
    add('R79','R7','4.7k 1%',{'1':'CHG_ARM','2':'GND'},108,67,'RC0402FR-074K7L','Local gate pull-down; not on the I2C bus')
    spec['Q5']['nets']['2']='CHG_CE_RETURN';spec['U25']['nets']['6']='CHG_ARM'
    tree=parse((OUT/'power.kicad_sch').read_text())
    ground=next(s for s in children(tree,'symbol') if str(child(s,'lib_id')[1])=='power:GND' and tuple(map(float,child(s,'at')[1:3]))==(111.76,121.92))
    tree.remove(ground)
    page=drawing.Sheet('power','Battery, thermistor and programmable charger',7,'',rootid,spec,instances,symbols)
    page.tree=tree;page.serial=1000;page.used={str(s[1]) for s in children(child(tree,'lib_symbols'),'symbol')}
    page.label('CHG_CE_RETURN',(111.76,121.92))
    q8=page.place('Q8',208.28,231.14);page.bank(['R79'],137.16,231.14)
    for name,y in [('Reference',213.36),('Value',215.90)]:child(prop(q8,name),'at')[1:]=['185.42',str(y),'0']
    page.text('Q5 AND Q8 must both conduct to enable charging.\nU25 PA0 reset/high-Z -> R79 pulls Q8 OFF.\nPreload PA0 low; arm only after verified charger policy.\nIWDG reset and GPIO discharge timing require bench qualification.',264.16,213.36,1.1)
    for txt in children(tree,'text'):
        if str(txt[1]).startswith('Charge enable: default OFF'):txt[1]=Q('Charge enable: default OFF\nCHG_ENABLE alone cannot charge; U25 CHG_ARM is also required.')
    page.finish()
    tree=parse((OUT/'power-supervisor.kicad_sch').read_text())
    page2=drawing.Sheet('power-supervisor','Always-on charging supervisor',23,'',rootid,spec,instances,symbols)
    page2.tree=tree;page2.serial=2000
    # PA0 is pin 6 of UFQFPN28, at the upper right of the retained symbol.
    inst=instances['U25'];cx,cy=map(float,child(inst,'at')[1:3]);sym=symbols[spec['U25']['libid']]
    pin=next(pin for unit in children(sym,'symbol') for pin in children(unit,'pin') if str(child(pin,'number')[1])=='6')
    px,py=map(float,child(pin,'at')[1:3]);pos=(cx+px,cy-py)
    nc=next(n for n in children(tree,'no_connect') if tuple(map(float,child(n,'at')[1:3]))==pos);tree.remove(nc)
    end=(pos[0]+7.62,pos[1]);page2.wire(pos,end);page2.label('CHG_ARM',end,180,'left')
    page2.text('PA0: dedicated active-high charge arm. Reset analog/high-Z\nallows R79 at Q8 to hold charging disabled independently of U24.\nNever retain this output through standby or run bootloader while armed.',15.24,165.1,1)
    (OUT/'power-supervisor.kicad_sch').write_text(dump(tree)+'\n')
    subprocess.run(['kicad-cli','sch','export','netlist',str(OUT/'handset.kicad_sch'),'--format','kicadxml','-o',str(OUT/'netlist.xml')],check=True)
    xml=ET.parse(OUT/'netlist.xml').getroot();native={(n.get('ref'),n.get('pin')):net.get('name') for net in xml.findall('./nets/net') for n in net.findall('node')}
    for c in spec.values():
        for pin,net in c['nets'].items():
            actual=native.get((c['ref'],pin));assert actual==net if net else actual and actual.startswith('unconnected-('),(c['ref'],pin,net,actual)
    b=p.LoadBoard(str(SOURCE/'handset.kicad_pcb'));before=geometry(b);fps={f.GetReference():f for f in b.GetFootprints()}
    def netobj(name):
        n=b.FindNet(name)
        if not n:n=p.NETINFO_ITEM(b,name);b.Add(n)
        return n
    # Remove the old Q5 source ground stub and its now-unused ground via only.
    removed={}
    remove_ids={'504e011d-0a68-4b5b-920a-2baa815e58f1','a8669b04-28ed-467b-ae79-8ce2c3283a6a','3409c1c5-0dbc-4411-b05a-7a3e71476f88'}
    pcbtree=parse((SOURCE/'handset.kicad_pcb').read_text())
    for item in list(children(pcbtree,'segment'))+list(children(pcbtree,'via')):
        ident=str(child(item,'uuid')[1])
        if ident in remove_ids:
            assert before['copper'][ident][7]=='GND'
            removed[ident]=before['copper'][ident];pcbtree.remove(item)
    assert set(removed)==remove_ids
    (OUT/'charge-inhibit-unrouted.kicad_pcb').write_text(dump(pcbtree)+'\n')
    b=p.LoadBoard(str(OUT/'charge-inhibit-unrouted.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()}
    for ref,pin,net in [('Q5','2','CHG_CE_RETURN'),('U25','6','CHG_ARM')]:
        next(pad for pad in fps[ref].Pads() if pad.GetNumber()==pin).SetNet(netobj(net))
    for ref in additions:
        c=spec[ref];lib,name=c['footprint'].split(':');f=p.FootprintLoad('/usr/share/kicad/footprints/'+lib+'.pretty',name);assert f
        f.SetReference(ref);f.SetValue(c['value']);f.SetFPID(p.LIB_ID(lib,name));b.Add(f);f.Flip(f.GetPosition(),False)
        f.SetPosition(p.VECTOR2I(p.FromMM(c['x']),p.FromMM(c['y'])));f.SetOrientationDegrees(c['angle']);f.Reference().SetLayer(p.B_Fab);f.Value().SetVisible(False)
        path=p.KIID_PATH()
        for ident in (rootid,drawing.UID('power'),uid(ref)):path.push_back(p.KIID(ident))
        f.SetPath(path);f.SetSheetname('Battery, thermistor and programmable charger');f.SetSheetfile('power.kicad_sch')
        f.SetField('MPN',c['mpn']);f.GetField('MPN').SetVisible(False)
        for pad in f.Pads():pad.SetNet(netobj(native[(ref,pad.GetNumber())]))
    p.SaveBoard(str(OUT/'charge-inhibit-unrouted.kicad_pcb'),b);shutil.copy2(SOURCE/'handset.kicad_pro',OUT/'handset.kicad_pro')
    after=geometry(b)
    assert before['footprints'].items()<=after['footprints'].items()
    for ident,g in before['copper'].items():
        if ident not in removed:assert after['copper'][ident]==g
    (OUT/'connectivity.json').write_text(json.dumps(list(spec.values()),indent=2)+'\n')
    for name,fields,refs in [('placement.csv',['ref','value','footprint','x','y','side','angle','sheet'],list(spec)),('charge-inhibit-bom.csv',['ref','value','mpn','footprint','role'],additions)]:
        with (OUT/name).open('w') as f:
            w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(spec[r] for r in refs)
    (OUT/'charge-inhibit-update.json').write_text(json.dumps(dict(source_hashes={str(f.relative_to(SOURCE)):hashlib.sha256(f.read_bytes()).hexdigest() for f in SOURCE.rglob('*') if f.is_file() and f.suffix in ('.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym','.kicad_mod','.json','.csv')},added_refs=additions,changed_refs=['Q5','U25'],removed_copper=removed,preserved_copper_items=len(before['copper'])-len(removed),components=len(spec),fabrication_released=False),indent=2)+'\n')
    print('Staged second CE permission:',len(spec),'components')
if __name__=='__main__':main()
