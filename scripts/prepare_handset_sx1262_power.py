#!/usr/bin/env python3
"""Stage the SX1262 core regulator support without changing unrelated CAD."""
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
OUT=Path('/tmp/handset-sx1262-power')
uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'handset-sx1262-power/'+s))
p.SwigPyIterator.next=p.SwigPyIterator.__next__


def main():
    assert not (SOURCE/'sx1262-power-update.json').exists(), 'Already installed; preserve subsequent edits.'
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
                       x=x,y=y,side='B',angle=0,sheet='radios',mpn=mpn,role=role)
        instances[ref]=parse(f'''(symbol (lib_id "{libid}") (at 0 0 0) (unit 1) (in_bom yes) (on_board yes) (dnp no)
          (uuid "{uid(ref)}")
          (property "Reference" "{ref}" (at 0 0 0) (effects (font (size 1 1))))
          (property "Value" "{value}" (at 0 0 0) (effects (font (size 1 1))))
          (property "Footprint" "{footprint}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
          (property "MPN" "{mpn}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
          (instances (project "handset" (path "/{rootid}/{drawing.UID('radios')}" (reference "{ref}") (unit 1)))))''')
        additions.append(ref)
    add('L12','15uH 20%','Device:L','Inductor_SMD:L_TDK_MLZ2012_h1.25mm',
        {'1':'SX_DCC_SW','2':'SX_VREG'},111,31.5,'MLZ2012M150WT000',
        'Semtech recommended core DC-DC inductor; shielded; DCR max 1.235ohm; Isat 120mA at 50% L reduction')
    for ref,x,y,pin in [('C75',108.6,37.3,'1'),('C76',114.8,30.5,'11')]:
        add(ref,'100nF 10% X7R 16V','Device:C','Capacitor_SMD:C_0402_1005Metric',
            {'1':'+3V3','2':'GND'},x,y,'GRM155R71C104KA88D','Local supply bypass for U4.'+pin)
    spec['C8'].update(value='100nF 10% X7R 16V',mpn='GRM155R71C104KA88D',role='Local bypass for U4.10',x=114.8,y=32)
    spec['C9'].update(value='470nF 10% X5R 10V',mpn='GRM155R61A474KE15D',role='VREG bypass; Semtech C17; never tie VREG to +3V3',x=108.3,y=31.5)
    for ref in ['C8','C9']:
        instances[ref].append(parse(f'(property "MPN" "{spec[ref]["mpn"]}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))'))
    page=drawing.Sheet('radios','SX1262 LoRa radio',12,
        'DC-DC support captured from Semtech DS rev1.2 Fig14-2 and Table5-3. Clock and RF frontend remain incomplete. Do not power.',rootid,spec,instances,symbols)
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
    page.text('SetRegulatorMode(0x01) only in STDBY_RC, after hardware qualification.\nL12 supplies the core, not the SX1262 high-power PA.\nTCXO, PA feed, matching/filter and RF switch are still missing.\nC10 PA bypass and J20 antenna connection remain provisional.',218.44,220.98,1.15)
    page.finish()
    b=p.LoadBoard(str(SOURCE/'handset.kicad_pcb'));before=geometry(b)
    fps={f.GetReference():f for f in b.GetFootprints()}
    for ref in additions:
        c=spec[ref];lib,name=c['footprint'].split(':')
        f=p.FootprintLoad('/usr/share/kicad/footprints/'+lib+'.pretty',name)
        assert f,c['footprint'];f.SetReference(ref);f.SetValue(c['value']);f.SetFPID(p.LIB_ID(lib,name));b.Add(f)
        f.Flip(f.GetPosition(),False);f.Reference().SetLayer(p.B_Fab);f.Value().SetVisible(False)
        path=p.KIID_PATH()
        for ident in (rootid,page.id,uid(ref)):path.push_back(p.KIID(ident))
        f.SetPath(path);f.SetSheetname('SX1262 LoRa radio');f.SetSheetfile('radios.kicad_sch');fps[ref]=f
        for pad in f.Pads():pad.SetNet(b.FindNet(c['nets'][pad.GetNumber()]))
    for ref in additions+['C8','C9']:
        c=spec[ref];f=fps[ref];f.SetPosition(p.VECTOR2I(p.FromMM(c['x']),p.FromMM(c['y'])));f.SetOrientationDegrees(c['angle']);f.SetValue(c['value'])
        f.Reference().SetLayer(p.B_Fab);f.SetField('MPN',c['mpn']);f.GetField('MPN').SetVisible(False)
    p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
    shutil.copy2(SOURCE/'handset.kicad_pro',OUT/'handset.kicad_pro')
    after=geometry(p.LoadBoard(str(OUT/'handset.kicad_pcb')))
    assert before['copper']==after['copper']
    for ref,g in before['footprints'].items():
        if ref not in ('C8','C9'):assert g==after['footprints'][ref],ref
    (OUT/'connectivity.json').write_text(json.dumps(list(spec.values()),indent=2)+'\n')
    for name,fields,refs in [('placement.csv',['ref','value','footprint','x','y','side','angle','sheet'],list(spec)),
      ('sx1262-power-bom.csv',['ref','value','mpn','footprint','role'],additions+['C8','C9'])]:
        with (OUT/name).open('w') as f:
            w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(spec[r] for r in refs)
    (OUT/'sx1262-power-update.json').write_text(json.dumps(dict(
        source_hashes={str(f.relative_to(SOURCE)):hashlib.sha256(f.read_bytes()).hexdigest() for f in SOURCE.rglob('*') if f.is_file() and f.suffix in ('.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym','.kicad_mod','.json','.csv')},
        added_refs=additions,changed_refs=['C8','C9'],components=len(spec),preserved_copper_items=len(before['copper']),
        unchanged_footprints=len(before['footprints'])-2,fabrication_released=False,
        scope='SX1262 core DC-DC support and supply bypass; unrouted; clock and RF frontend incomplete'),indent=2)+'\n')
    print('Staged',len(additions),'new parts;',len(spec),'total; copper preserved.')


if __name__=='__main__':main()
