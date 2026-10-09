#!/usr/bin/env python3
"""Stage the SX1262 PA choke/bypass circuit without changing unrelated CAD."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import uuid
import pcbnew as p
from cad_sexpr import Q, parse, child, children, prop
import rebuild_handset_schematics as drawing
from sync_handset_schematic_rebuild import geometry

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hardware/handset-rev-a/generated'
OUT=Path('/tmp/handset-sx1262-pa')
uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'handset-sx1262-pa/'+s))
p.SwigPyIterator.next=p.SwigPyIterator.__next__


def main():
    assert not (SOURCE/'sx1262-pa-update.json').exists(), 'Already installed; preserve subsequent edits.'
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
    add('L13','47nH 2%','Device:L','Inductor_SMD:L_0402_1005Metric',
        {'1':'SX_VR_PA','2':'SX_RFO'},115,45,'LQW15AN47NG80D',
        'PA RF choke; 47nH baseline from RAK4270; qualify current, RF loss and harmonics')
    add('C101','47pF 5% C0G 50V','Device:C','Capacitor_SMD:C_0402_1005Metric',
        {'1':'SX_VR_PA','2':'GND'},115,43.7,'C1005C0G1H470J050BA',
        'PA high-frequency bypass on VR_PA side of choke; provisional RF placement')
    spec['C10'].update(value='47nF 10% X7R 25V',mpn='GRM155R71E473KA88D',
                       role='PA bypass on VR_PA side of choke; replaces provisional 100nF')
    prop(instances['C10'],'Value')[2]=Q(spec['C10']['value'])
    field=prop(instances['C10'],'MPN')
    if field is None:
        field=parse('(property "MPN" "" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))')
        instances['C10'].append(field)
    field[2]=Q(spec['C10']['mpn'])
    page=drawing.Sheet('radios','SX1262 LoRa radio',12,
        'SX1262 clock, supply, PA feed and RF matching/switch captured. RF layout incomplete; do not power.',rootid,spec,instances,symbols)
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
    page.bank(['C10','C101'],203.2,187.96)
    page.passive('L13',208.28,160.02,90)
    feed_x=page.pins['L13.1'][0][0]
    page.path('SX_VR_PA','L13.1',(feed_x,177.8),(203.2,177.8))
    page.dot((203.2,177.8))
    page.bank(['R10'],350.52,187.96)
    page.text('C8: VBAT pin10. C75: VDD_IN pin1. C76: VBAT_IO pin11.\nAll use the same +3V3 rail; place each close to its pin.\nC9 replaces the incorrect 100nF with Semtech reference 470nF.',35.56,220.98,1.15)
    page.text('SetRegulatorMode(0x01) only in STDBY_RC, after hardware qualification.\nL12 supplies the core, not the SX1262 high-power PA.\nL13: 47nH PA choke; C10/C101: 47nF/47pF bypass.\nRAK4270 values; final RF layout and qualification remain open.',218.44,266.7,1.05)
    oscillator=page.place('Y3',60.96,152.4)
    for name,y in [('Reference',132.08),('Value',134.62)]:child(prop(oscillator,name),'at')[1:]=['40.64',str(y),'0']
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
    c10=next(f for f in b.GetFootprints() if f.GetReference()=='C10')
    c10.SetValue(spec['C10']['value']);c10.SetField('MPN',spec['C10']['mpn'])
    c10.GetField('MPN').SetVisible(False)
    # Only C10's value/MPN changes; preserve its position, pads and all copper.
    before['footprints']['C10'][5]=spec['C10']['value']
    p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
    shutil.copy2(SOURCE/'handset.kicad_pro',OUT/'handset.kicad_pro')
    after=geometry(b);assert before['copper']==after['copper']
    assert all(after['footprints'][k]==v for k,v in before['footprints'].items())
    (OUT/'connectivity.json').write_text(json.dumps(list(spec.values()),indent=2)+'\n')
    for name,fields,refs in [('placement.csv',['ref','value','footprint','x','y','side','angle','sheet'],list(spec)),('sx1262-pa-bom.csv',['ref','value','mpn','footprint','role'],['C10']+additions)]:
        with (OUT/name).open('w') as f:
            writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(spec[r] for r in refs)
    (OUT/'sx1262-pa-update.json').write_text(json.dumps(dict(source_board_sha256=hashlib.sha256((SOURCE/'handset.kicad_pcb').read_bytes()).hexdigest(),final_board_sha256=hashlib.sha256((OUT/'handset.kicad_pcb').read_bytes()).hexdigest(),added_refs=additions,modified_refs=['C10'],components=len(spec),preserved_copper_items=len(before['copper']),geometry_preserved_footprints=len(before['footprints']),fabrication_released=False,scope='PA choke and bypass values captured; placement provisional, PA and RF copper incomplete'),indent=2)+'\n')
    print('Staged PA circuit',OUT)

if __name__=='__main__':main()
