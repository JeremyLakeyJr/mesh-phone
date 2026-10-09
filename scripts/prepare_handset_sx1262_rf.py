#!/usr/bin/env python3
"""Stage the SX1262 RF matching/switch circuit without changing unrelated CAD."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import shutil
import uuid
import pcbnew as p
from cad_sexpr import Q, parse, dump, child, children, prop
import rebuild_handset_schematics as drawing
from sync_handset_schematic_rebuild import geometry

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hardware/handset-rev-a/generated'
OUT=Path('/tmp/handset-sx1262-rf')
uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'handset-sx1262-rf/'+s))
p.SwigPyIterator.next=p.SwigPyIterator.__next__


def main():
    assert not (SOURCE/'sx1262-rf-update.json').exists(), 'Already installed; preserve subsequent edits.'
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
    for lib,name in [('Filter','0900FM15K0039'),('RF_Switch','BGS12WN6E6327')]:
        tree=parse(Path('/usr/share/kicad/symbols',lib+'.kicad_sym').read_text())
        symbol=copy.deepcopy(next(s for s in children(tree,'symbol') if s[1]==name))
        symbol[1]=Q(lib+':'+name);symbols[str(symbol[1])]=symbol
    additions=[]
    def add(ref,value,libid,footprint,nets,x,y,mpn,role):
        assert ref not in spec
        spec[ref]=dict(ref=ref,value=value,libid=libid,footprint=footprint,nets=nets,
                       x=x,y=y,side='F',angle=0,sheet='radios',mpn=mpn,role=role)
        instances[ref]=parse(f'''(symbol (lib_id "{libid}") (at 0 0 0) (unit 1) (in_bom yes) (on_board yes) (dnp no)
          (uuid "{uid(ref)}")
          (property "Reference" "{ref}" (at 0 0 0) (effects (font (size 1 1))))
          (property "Value" "{value}" (at 0 0 0) (effects (font (size 1 1))))
          (property "Footprint" "{footprint}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
          (property "MPN" "{mpn}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
          (instances (project "handset" (path "/{rootid}/{drawing.UID('radios')}" (reference "{ref}") (unit 1)))))''')
        additions.append(ref)
    add('U36','0900FM15K0039001E','Filter:0900FM15K0039','RF_Converter:Balun_Johanson_0900FM15K0039',
        {'1':'SX_RFO','2':'GND','3':'SX_RFI_N','4':'SX_RFI_P','5':'GND','6':'SX_RX_MATCH','7':'GND','8':'SX_TX_MATCH','9':'GND','10':'GND'},
        118,45,'0900FM15K0039001E','Integrated SX1262 matching/filter; RF placement/routing and ground vias require qualification')
    add('U37','BGS12WN6E6327','RF_Switch:BGS12WN6E6327','Package_LGA:Infineon_PG-TSNP-6-10_0.7x1.1mm_0.7x1.1mm_P0.4mm',
        {'1':'SX_TX_AC','2':'GND','3':'SX_RX_AC','4':'SX_SWITCH_VDD','5':'SX_ANT_AC','6':'SX_SWITCH_CTRL'},
        121,45,'BGS12WN6E6327XTSA1','CTRL high selects TX RF2; low selects RX RF1; all RF ports require zero DC')
    for ref,net1,net2,x,y,role in [
        ('R91','SX_RF_SW','SX_SWITCH_CTRL',118,48,'DIO2 control series filter'),
        ('R92','+3V3','SX_SWITCH_VDD',121,48,'Always-powered switch supply series filter')]:
        add(ref,'100R 1%','Device:R','Resistor_SMD:R_0402_1005Metric',{'1':net1,'2':net2},x,y,'RC0402FR-07100RL',role)
    for ref,net,x,y in [('C96','SX_SWITCH_CTRL',116,47.5),('C97','SX_SWITCH_VDD',125,47)]:
        add(ref,'1nF 10% X7R 50V','Device:C','Capacitor_SMD:C_0402_1005Metric',{'1':net,'2':'GND'},x,y,'GRM155R71H102KA01D','Switch control/supply shunt filter')
    for ref,net1,net2,x,y in [('C98','SX_ANT_AC','LORA_RF_50R',123,45),('C99','SX_TX_MATCH','SX_TX_AC',118,42.5),('C100','SX_RX_MATCH','SX_RX_AC',121,43)]:
        add(ref,'100pF 5% C0G 50V','Device:C','Capacitor_SMD:C_0402_1005Metric',{'1':net1,'2':net2},x,y,'GRM1555C1H101JA01D','Explicit RF port DC block; 100pF starting value requires RF validation')
    add('R93','100k 1%','Device:R','Resistor_SMD:R_0402_1005Metric',{'1':'SX_SWITCH_CTRL','2':'GND'},123,48,'RC0402FR-07100KL','Default RX while DIO2 is high impedance')
    page=drawing.Sheet('radios','SX1262 LoRa radio',12,
        'SX1262 clock, supply and RF matching/switch captured. PA feed and RF layout incomplete; do not power.',rootid,spec,instances,symbols)
    inst=page.place('U4',137.16,96.52)
    for name,y in [('Reference',60.96),('Value',63.5)]:child(prop(inst,name),'at')[1:]=['101.6',str(y),'0']
    page.place('J20',386.08,99.06)
    page.passive('L12',208.28,81.28,90)
    # VREG is a core output, distinct from the +3V3 input/PA supply.
    page.path('SX_DCC_SW','U4.9',(175.26,83.82),(175.26,68.58),(195.58,68.58),(195.58,81.28),'L12.1')
    page.path('SX_VREG','U4.7',(167.64,81.28),(167.64,58.42),(228.6,58.42),(228.6,81.28),'L12.2')
    page.passive('C9',228.6,132.08)
    page.path('SX_VREG','C9.1',(228.6,81.28));page.dot((228.6,81.28))
    page.label('SX_VREG',(228.6,58.42));page.label('SX_DCC_SW',(195.58,68.58))
    pos=page.pins['C9.2'][0];page.path('GND','C9.2',(pos[0],pos[1]+7.62),label=True)
    page.bank(['C8','C75','C76'],66.04,187.96)
    page.bank(['C10'],218.44,187.96);page.bank(['R10'],350.52,187.96)
    page.text('C8: VBAT pin10. C75: VDD_IN pin1. C76: VBAT_IO pin11.\nAll use the same +3V3 rail; place each close to its pin.\nC9 replaces the incorrect 100nF with Semtech reference 470nF.',35.56,220.98,1.15)
    page.text('SetRegulatorMode(0x01) only in STDBY_RC, after hardware qualification.\nL12 supplies the core, not the SX1262 high-power PA.\nPA choke/bypass and final RF placement/routing remain open.\nC10 PA bypass and J20 antenna connection remain provisional.',218.44,266.7,1.05)
    oscillator=page.place('Y3',60.96,152.4)
    for name,y in [('Reference',139.7),('Value',142.24)]:child(prop(oscillator,name),'at')[1:]=['40.64',str(y),'0']
    child(child(page.tree,'title_block'),'date')[1]=Q('2026-10-08')
    page.passive('R90',91.44,152.4,90);page.passive('C95',119.38,152.4,90)
    page.path('SX_TCXO_OUT','Y3.3','R90.1')
    page.path('SX_TCXO_COUPLED','R90.2','C95.1')
    page.path('SX_XTA','C95.2',(132.08,152.4),label=True)
    page.bank(['C94'],25.4,152.4)
    page.label('SX_TCXO_OUT',(78.74,152.4),90)
    page.label('SX_TCXO_COUPLED',(101.6,152.4),90)
    page.text('Y3 pads 1/2 = GND, 3 = OUT, 4 = VDD. XTB is intentionally NC.\nConfigure DIO3 for 1.8V; provisional startup allowance 5ms.\nConfirm TCXO output <=1.2Vpp; no qualified maximum in series data.',35.56,243.84,1.05)
    page.place('U36',274.32,106.68)
    switch=page.place('U37',340.36,137.16)
    for name,y in [('Reference',109.22),('Value',111.76)]:child(prop(switch,name),'at')[1:]=['314.96',str(y),'0']
    for ref,x,y in [('C99',312.42,76.2),('C100',312.42,99.06),('C98',365.76,76.2),('R91',264.16,177.8),('R92',264.16,210.82)]:
        page.passive(ref,x,y,90)
    page.bank(['C96','R93'],294.64,177.8)
    page.bank(['C97'],294.64,210.82)
    # Powered through R92 from +3V3; this flag describes a passive supply feed.
    page.flag('U37.4')
    page.text('U37: CTRL=0 selects RF1/RX; CTRL=1 selects RF2/TX.\nR93 defaults to RX. C98/C99/C100 explicitly block DC.\n100pF RF blocks are starting values, subject to RF measurement.\nNo RF route or thermal/ground-via qualification in this checkpoint.',218.44,238.76,1.05)
    page.finish()
    b=p.LoadBoard(str(SOURCE/'handset.kicad_pcb'));before=geometry(b)
    for ref in additions:
        for net in spec[ref]['nets'].values():
            if not b.FindNet(net):b.Add(p.NETINFO_ITEM(b,net))
    for ref in additions:
        c=spec[ref];lib,name=c['footprint'].split(':')
        f=p.FootprintLoad('/usr/share/kicad/footprints/'+lib+'.pretty',name);assert f
        f.SetReference(ref);f.SetValue(c['value']);f.SetFPID(p.LIB_ID(lib,name));b.Add(f)
        f.Reference().SetLayer(p.F_Fab);f.Value().SetVisible(False)
        path=p.KIID_PATH()
        for ident in (rootid,page.id,uid(ref)):path.push_back(p.KIID(ident))
        f.SetPath(path);f.SetSheetname('SX1262 LoRa radio');f.SetSheetfile('radios.kicad_sch')
        for pad in f.Pads():
            if pad.GetNumber():pad.SetNet(b.FindNet(c['nets'][pad.GetNumber()]))
        f.SetPosition(p.VECTOR2I(p.FromMM(c['x']),p.FromMM(c['y'])));f.SetOrientationDegrees(c['angle'])
        f.SetField('MPN',c['mpn']);f.GetField('MPN').SetVisible(False)
    p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
    shutil.copy2(SOURCE/'handset.kicad_pro',OUT/'handset.kicad_pro')
    after=geometry(b);assert before['copper']==after['copper']
    assert all(after['footprints'][k]==v for k,v in before['footprints'].items())
    (OUT/'connectivity.json').write_text(json.dumps(list(spec.values()),indent=2)+'\n')
    for name,fields,refs in [('placement.csv',['ref','value','footprint','x','y','side','angle','sheet'],list(spec)),('sx1262-rf-bom.csv',['ref','value','mpn','footprint','role'],additions)]:
        with (OUT/name).open('w') as f:
            writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(spec[r] for r in refs)
    (OUT/'sx1262-rf-update.json').write_text(json.dumps(dict(source_board_sha256=hashlib.sha256((SOURCE/'handset.kicad_pcb').read_bytes()).hexdigest(),final_board_sha256=hashlib.sha256((OUT/'handset.kicad_pcb').read_bytes()).hexdigest(),added_refs=additions,components=len(spec),preserved_copper_items=len(before['copper']),unchanged_footprints=len(before['footprints']),fabrication_released=False,scope='Matching/filter, RF switch, control and DC blocks captured; placement provisional, PA feed and RF routing incomplete'),indent=2)+'\n')
    print('Staged RF circuit',OUT)

if __name__=='__main__':main()
