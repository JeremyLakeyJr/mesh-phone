#!/usr/bin/env python3
"""Stage the SX1262 TCXO clock circuit without changing unrelated CAD."""
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
OUT=Path('/tmp/handset-sx1262-clock')
uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'handset-sx1262-clock/'+s))
p.SwigPyIterator.next=p.SwigPyIterator.__next__


def main():
    assert not (SOURCE/'sx1262-clock-update.json').exists(), 'Already installed; preserve subsequent edits.'
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
    symbol=parse('''(symbol "ECS_TXO_32CSMV"
      (pin_names (offset 0.508)) (in_bom yes) (on_board yes)
      (property "Reference" "Y" (at 0 10.16 0) (effects (font (size 1.27 1.27))))
      (property "Value" "ECS_TXO_32CSMV" (at 0 7.62 0) (effects (font (size 1.27 1.27))))
      (symbol "ECS_TXO_32CSMV_0_1" (rectangle (start -7.62 5.08) (end 7.62 -5.08) (stroke (width 0) (type default)) (fill (type background))))
      (symbol "ECS_TXO_32CSMV_1_1"
        (pin power_in line (at 0 7.62 270) (length 2.54) (name "VDD" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at -2.54 -7.62 90) (length 2.54) (name "GND1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 2.54 -7.62 90) (length 2.54) (name "GND2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin output line (at 10.16 0 180) (length 2.54) (name "OUT" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))))''')
    library=parse((OUT/'Handset.kicad_sym').read_text());library.append(copy.deepcopy(symbol))
    (OUT/'Handset.kicad_sym').write_text(dump(library)+'\n')
    symbol[1]=Q('Handset:ECS_TXO_32CSMV');symbols[str(symbol[1])]=symbol
    footprint=['(footprint "ECS_TXO_32CSMV_3225" (version 20241229) (generator "pcbnew") (layer "F.Cu") (attr smd)',
        '(descr "ECS-TXO-32CSMV manufacturer land pattern; pads 1/2 GND, 3 OUT, 4 VDD")',
        '(property "Reference" "Y**" (at 0 -2.2 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
        '(property "Value" "ECS_TXO_32CSMV" (at 0 2.2 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
        '(fp_rect (start -1.6 -1.25) (end 1.6 1.25) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))',
        '(fp_line (start -1.6 0.75) (end -1.1 1.25) (stroke (width 0.1) (type default)) (layer "F.Fab"))',
        '(fp_rect (start -2.05 -1.65) (end 2.05 1.65) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))']
    for number,x,y in [(1,-1.1,.8),(2,1.1,.8),(3,1.1,-.8),(4,-1.1,-.8)]:
        footprint.append(f'(pad "{number}" smd rect (at {x} {y}) (size 1.4 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))')
    (OUT/'Handset.pretty/ECS_TXO_32CSMV_3225.kicad_mod').write_text('\n'.join(footprint)+')\n')
    # DIO3 is dedicated to its documented regulated TCXO supply function.
    radio=copy.deepcopy(symbols['RF:SX1262IMLTRT']);radio[1]=Q('SX1262_TCXO_DIO3Supply')
    for unit in children(radio,'symbol'):
        unit[1]=Q(str(unit[1]).replace('SX1262IMLTRT','SX1262_TCXO_DIO3Supply'))
        for pin in children(unit,'pin'):
            if child(pin,'number')[1]=='6':pin[1]='power_out'
    library=parse((OUT/'Handset.kicad_sym').read_text());library.append(copy.deepcopy(radio))
    (OUT/'Handset.kicad_sym').write_text(dump(library)+'\n')
    radio[1]=Q('Handset:SX1262_TCXO_DIO3Supply');symbols[str(radio[1])]=radio
    spec['U4']['libid']='Handset:SX1262_TCXO_DIO3Supply'
    child(instances['U4'],'lib_id')[1]=Q(spec['U4']['libid'])
    spec['U4']['nets']['4']=None
    additions=[]
    def add(ref,value,libid,footprint,nets,x,y,mpn,role):
        assert ref not in spec
        spec[ref]=dict(ref=ref,value=value,libid=libid,footprint=footprint,nets=nets,
                       x=x,y=y,side='B',angle=0,sheet='radios',mpn=mpn,role=role)
        instances[ref]=parse(f'''(symbol (lib_id "{libid}") (at 0 0 0) (unit 1) (in_bom yes) (on_board yes) (dnp no)
          (uuid "{uid(ref)}")
          (property "Reference" "{ref}" (at 0 0 0) (effects (font (size 1 1))))
          (property "Value" "{value}" (at 0 0 0) (effects (font (size 1 1))))
          (property "Footprint" "{footprint}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
          (property "MPN" "{mpn}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
          (instances (project "handset" (path "/{rootid}/{drawing.UID('radios')}" (reference "{ref}") (unit 1)))))''')
        additions.append(ref)
    add('Y3','32MHz TCXO 0.5ppm temp','Handset:ECS_TXO_32CSMV','Handset:ECS_TXO_32CSMV_3225',
        {'1':'GND','2':'GND','3':'SX_TCXO_OUT','4':'SX_TCXO_PWR'},113.3,40.6,
        'ECS-TXO-32CSMV-320-AN-TR','1.8V DIO3 supply; clipped sine; maximum amplitude requires supplier/bench qualification')
    add('R90','220R 1%','Device:R','Resistor_SMD:R_0402_1005Metric',
        {'1':'SX_TCXO_OUT','2':'SX_TCXO_COUPLED'},109.4,39.8,'RC0402FR-07220RL','Semtech series clock resistor')
    add('C94','100nF 10% X7R 16V','Device:C','Capacitor_SMD:C_0402_1005Metric',
        {'1':'SX_TCXO_PWR','2':'GND'},116.5,39.0,'GRM155R71C104KA88D','Local TCXO supply bypass')
    add('C95','10pF 5% C0G 50V','Device:C','Capacitor_SMD:C_0402_1005Metric',
        {'1':'SX_TCXO_COUPLED','2':'SX_XTA'},109.4,38.6,'GRM1555C1H100JA01D','Semtech XTA series DC blocking capacitor')
    spec['Y3']['angle']=180
    spec['R90']['angle']=180
    page=drawing.Sheet('radios','SX1262 LoRa radio',12,
        'SX1262 core supply and DIO3-controlled TCXO captured. RF frontend remains incomplete; do not power.',rootid,spec,instances,symbols)
    inst=page.place('U4',137.16,96.52)
    for name,y in [('Reference',60.96),('Value',63.5)]:child(prop(inst,name),'at')[1:]=['101.6',str(y),'0']
    page.place('J20',327.66,96.52)
    page.passive('L12',208.28,81.28,90)
    # VREG is a core output, distinct from the +3V3 input/PA supply.
    page.path('SX_DCC_SW','U4.9',(175.26,83.82),(175.26,68.58),(195.58,68.58),(195.58,81.28),'L12.1')
    page.path('SX_VREG','U4.7',(167.64,81.28),(167.64,58.42),(228.6,58.42),(228.6,81.28),'L12.2')
    page.passive('C9',228.6,132.08)
    page.path('SX_VREG','C9.1',(228.6,81.28));page.dot((228.6,81.28))
    page.label('SX_VREG',(228.6,58.42));page.label('SX_DCC_SW',(195.58,68.58))
    pos=page.pins['C9.2'][0];page.path('GND','C9.2',(pos[0],pos[1]+7.62),label=True)
    page.bank(['C8','C75','C76'],66.04,187.96)
    page.bank(['C10'],218.44,187.96);page.bank(['R10'],320.04,187.96)
    page.text('C8: VBAT pin10. C75: VDD_IN pin1. C76: VBAT_IO pin11.\nAll use the same +3V3 rail; place each close to its pin.\nC9 replaces the incorrect 100nF with Semtech reference 470nF.',35.56,220.98,1.15)
    page.text('SetRegulatorMode(0x01) only in STDBY_RC, after hardware qualification.\nL12 supplies the core, not the SX1262 high-power PA.\nPA feed, matching/filter and RF switch are still missing.\nC10 PA bypass and J20 antenna connection remain provisional.',218.44,220.98,1.15)
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
    page.finish()
    b=p.LoadBoard(str(SOURCE/'handset.kicad_pcb'));before=geometry(b)
    fps={f.GetReference():f for f in b.GetFootprints()}
    fps['U12'].Reference().SetLayer(p.B_Fab) # Keep its reference clear of new clock lands.
    for name in ('SX_TCXO_OUT','SX_TCXO_COUPLED','unconnected-(U4-XTB-Pad4)'):
        if not b.FindNet(name):b.Add(p.NETINFO_ITEM(b,name))
    for pad in fps['U4'].Pads():
        if pad.GetNumber()=='4':pad.SetNet(b.FindNet('unconnected-(U4-XTB-Pad4)'))
    for ref in additions:
        c=spec[ref];lib,name=c['footprint'].split(':')
        path=OUT/'Handset.pretty' if lib=='Handset' else Path('/usr/share/kicad/footprints')/(lib+'.pretty')
        f=p.FootprintLoad(str(path),name);assert f,c['footprint']
        f.SetReference(ref);f.SetValue(c['value']);f.SetFPID(p.LIB_ID(lib,name));b.Add(f)
        f.Flip(f.GetPosition(),False);f.Reference().SetLayer(p.B_Fab);f.Value().SetVisible(False)
        path=p.KIID_PATH()
        for ident in (rootid,page.id,uid(ref)):path.push_back(p.KIID(ident))
        f.SetPath(path);f.SetSheetname('SX1262 LoRa radio');f.SetSheetfile('radios.kicad_sch')
        for pad in f.Pads():pad.SetNet(b.FindNet(c['nets'][pad.GetNumber()]))
        f.SetPosition(p.VECTOR2I(p.FromMM(c['x']),p.FromMM(c['y'])));f.SetOrientationDegrees(c['angle'])
        f.SetField('MPN',c['mpn']);f.GetField('MPN').SetVisible(False)
    p.SaveBoard(str(OUT/'handset.kicad_pcb'),b);shutil.copy2(SOURCE/'handset.kicad_pro',OUT/'handset.kicad_pro')
    after=geometry(b);assert before['copper']==after['copper']
    for ref,item in before['footprints'].items():assert item==after['footprints'][ref],ref
    (OUT/'connectivity.json').write_text(json.dumps(list(spec.values()),indent=2)+'\n')
    for name,fields,refs in [('placement.csv',['ref','value','footprint','x','y','side','angle','sheet'],list(spec)),
       ('sx1262-clock-bom.csv',['ref','value','mpn','footprint','role'],additions)]:
        with (OUT/name).open('w') as f:
            writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(spec[r] for r in refs)
    (OUT/'sx1262-clock-update.json').write_text(json.dumps(dict(
        source_board_sha256=hashlib.sha256((SOURCE/'handset.kicad_pcb').read_bytes()).hexdigest(),
        added_refs=additions,changed_pin_nets={'U4.4':'intentional NC'},reference_to_fab=['U12'],components=len(spec),
        preserved_copper_items=len(before['copper']),unchanged_footprints=len(before['footprints']),
        fabrication_released=False,scope='TCXO schematic and placement; RF frontend and clock qualification remain open'),indent=2)+'\n')
    print('Staged TCXO circuit:',OUT)

if __name__=='__main__':main()
