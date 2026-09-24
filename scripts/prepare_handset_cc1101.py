#!/usr/bin/env python3
"""Stage the CC1101 clock, supply bypass and 868/915 MHz frontend.

Never overwrites the saved project. Native checks and source-hash guarded
installation are separate from circuit generation. RF layout is not qualified.
"""
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

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hardware/handset-rev-a/generated'
OUT=Path('/tmp/handset-cc1101')
uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'handset-cc1101/'+s))
p.SwigPyIterator.next=p.SwigPyIterator.__next__


def main():
    assert not (SOURCE/'cc1101-update.json').exists(), 'Already installed; preserve later manual edits.'
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
    for libid in ('Device:L','Device:C','Device:FerriteBead','Device:Crystal_GND24','Connector:TestPoint'):
        lib,name=libid.split(':')
        s=copy.deepcopy(next(s for s in children(parse(Path('/usr/share/kicad/symbols',lib+'.kicad_sym').read_text()),'symbol') if s[1]==name))
        s[1]=Q(libid);symbols[libid]=s
    additions=[]
    def add(ref,value,libid,footprint,nets,x,y,mpn,role,angle=0):
        assert ref not in spec
        spec[ref]=dict(ref=ref,value=value,libid=libid,footprint=footprint,nets={str(k):v for k,v in nets.items()},
                       x=x,y=y,side='B',angle=angle,sheet='cc-radio',mpn=mpn,role=role)
        instances[ref]=parse(f'''(symbol (lib_id "{libid}") (at 0 0 0) (unit 1) (in_bom yes) (on_board yes) (dnp no)
          (uuid "{uid(ref)}")
          (property "Reference" "{ref}" (at 0 0 0) (effects (font (size 1 1))))
          (property "Value" "{value}" (at 0 0 0) (effects (font (size 1 1))))
          (property "Footprint" "{footprint}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
          (property "MPN" "{mpn}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
          (instances (project "handset" (path "/{rootid}/{drawing.UID('cc-radio')}" (reference "{ref}") (unit 1)))))''')
        additions.append(ref)
    def cap(ref,value,a,z,x,y,mpn,role,angle=0):
        add(ref,value,'Device:C','Capacitor_SMD:C_0402_1005Metric',{1:a,2:z},x,y,mpn,role,angle)
    def coil(ref,value,a,z,x,y,mpn,role,angle=0):
        add(ref,value,'Device:L','Inductor_SMD:L_0402_1005Metric',{1:a,2:z},x,y,mpn,role,angle)
    # ABM8 manufacturer land recommendation: 1.3 x 1.05 mm, gaps 1.0 x 0.7 mm.
    fp=parse(Path('/usr/share/kicad/footprints/Crystal.pretty/Crystal_SMD_3225-4Pin_3.2x2.5mm.kicad_mod').read_text())
    fp[1]=Q('ABM8_3225');child(fp,'descr')[1]=Q('Abracon ABM8 recommended lands; datasheet 2020-07-29 page 2. Pins 1/3 crystal, 2/4 ground.')
    for pad in children(fp,'pad'):
        x,y={1:(-1.15,.875),2:(1.15,.875),3:(1.15,-.875),4:(-1.15,-.875)}[int(pad[1])]
        child(pad,'at')[1:]=[str(x),str(y)];child(pad,'size')[1:]=['1.3','1.05']
    (OUT/'Handset.pretty/ABM8_3225.kicad_mod').write_text(dump(fp)+'\n')
    add('Y2','26MHz CL10pF','Device:Crystal_GND24','Handset:ABM8_3225',
        {1:'CC_X1',2:'GND',3:'CC_X2',4:'GND'},123.5,31.5,'ABM8-26.000MHZ-10-D-1-G-T','26MHz; +/-10ppm initial, +/-15ppm temperature; ESR <=50ohm; -40..85C')
    for ref,net,x in [('C61','CC_X1',120.5),('C62','CC_X2',126.5)]:
        cap(ref,'15pF 5% C0G 50V',net,'GND',x,31.5,'GRM1555C1H150JA01D','Crystal load: CL=15/2+2.5=10pF; tune on assembled PCB',90)
    rf=[
      ('C63','1pF 0.25pF C0G 50V','CC_BAL_P','CC_BAL_N',128,36,'GRM1555C1H1R0CA01D','TI C121'),
      ('C64','1.5pF 0.25pF C0G 50V','CC_BAL_P','CC_MATCH',130,35,'GRM1555C1H1R5CA01D','TI C122'),
      ('C65','3.3pF 0.25pF C0G 50V','CC_LPF','GND',131,38,'GRM1555C1H3R3CA01D','TI C123'),
      ('C66','100pF 5% C0G 50V','CC_SHUNT','GND',127,33,'GRM1555C1H101JA01D','TI C124'),
      ('C67','12pF 5% C0G 50V','CC_DC_BLOCK','CC_RF_50R',130,41,'GRM1555C1H120JA01D','TI C125 / DC block'),
      ('C68','1.5pF 0.25pF C0G 50V','CC_BAL_N','GND',127,38,'GRM1555C1H1R5CA01D','TI C131')]
    for args in rf:cap(*args)
    for args in [
      ('L5','12nH 5%','CC_RF_P','CC_BAL_P',126,35,'LQW15AN12NJ00D','TI L121'),
      ('L6','12nH 5%','CC_RF_N','CC_BAL_N',126,36.5,'LQW15AN12NJ00D','TI L131'),
      ('L7','18nH 5%','CC_BAL_P','CC_SHUNT',128,34,'LQW15AN18NJ00D','TI L122'),
      ('L8','18nH 5%','CC_BAL_N','CC_MATCH',130,36.5,'LQW15AN18NJ00D','TI L132'),
      ('L9','12nH 5%','CC_MATCH','CC_LPF',131,37.5,'LQW15AN12NJ00D','TI L123'),
      ('L10','12nH 5%','CC_LPF','CC_DC_BLOCK',131,39.5,'LQW15AN12NJ00D','TI L124')]:coil(*args)
    # TI's optional C126/L125 spur notch is not fitted in this revision.
    # Its requirement must be decided by conducted emissions on the final layout.
    for ref,pin,x,y in [('C69','9',123.5,33),('C70','11',124.5,34),('C71','14',125,38),('C72','15',125,39.5),('C73','18',122,39.5)]:
        cap(ref,'100nF 10% X7R 16V','CC_VDD','GND',x,y,'GRM155R71C104KA88D','Local bypass for U5.'+pin)
    cap('C74','1uF 10% X5R 10V','CC_VDD','GND',119.5,40,'GRM155R61A105KE15D','Filtered rail bulk capacitor')
    add('L11','1kohm @100MHz','Device:FerriteBead','Inductor_SMD:L_0402_1005Metric',
        {1:'+3V3',2:'CC_VDD'},119.5,38.5,'BLM15HG102SN1D','TI L1 supply bead')
    add('TP1','CC_GDO2_TEST','Connector:TestPoint','TestPoint:TestPoint_Pad_D1.0mm',
        {1:'CC_GDO2'},119.5,35,'PCB_PAD','Optional GDO2 debug endpoint; firmware IOCFG2=0x2E when unused')
    for pin in ('4','9','11','14','15','18'):spec['U5']['nets'][pin]='CC_VDD'
    spec['C12']['nets']['1']='CC_VDD'
    spec['C11'].update(value='100nF 10% X7R 16V',mpn='GRM155R71C104KA88D')
    spec['C12'].update(value='100nF 10% X7R 16V',mpn='GRM155R71C104KA88D',role='Local bypass for U5.4')
    moves={'U5':(121.5,39,0),'C11':(118,38.8,90),'C12':(118,40.8,90),
           'R11':(123.8,42.85,90),'R12':(121.2,44.2,0),'J21':(130.2,42.8,0)}
    positions={'Y2':(123.5,31,0),'C61':(120.9,30.4,90),'C62':(126.5,30.4,90),
      'C63':(127.8,37.6,90),'C64':(130,35.6,0),'C65':(132,37,90),'C66':(125.6,34,0),
      'C67':(126,42.8,0),'C68':(127.8,39.3,0),
      'L5':(125.6,37,0),'L6':(125.6,38.3,0),'L7':(127.8,35.4,0),
      'L8':(130,38.2,0),'L9':(130,39.5,0),'L10':(130,36.9,0),
      'C69':(121.5,35.7,0),'C70':(123.6,34.5,0),'C71':(125.6,39.7,0),
      'C72':(125.6,41,0),'C73':(121.5,42.5,0),'C74':(121.2,46,90),
      'L11':(116.8,41.3,90),'TP1':(118.2,30,0)}
    for ref,(x,y,a) in {**moves,**positions}.items():spec[ref].update(x=x,y=y,angle=a)
    # Logical presentation preserves manufacturer pin numbers and electrical types.
    chip=symbols['Handset:CC1101']
    locations={1:(-20.32,15.24,0),20:(-20.32,10.16,0),2:(-20.32,5.08,0),7:(-20.32,0,0),6:(-20.32,-5.08,0),3:(-20.32,-10.16,0),
      12:(20.32,10.16,180),13:(20.32,-10.16,180),5:(20.32,-20.32,180),17:(20.32,-25.4,180),
      8:(-10.16,-35.56,90),10:(-5.08,-35.56,90),16:(0,-35.56,90),19:(5.08,-35.56,90),21:(10.16,-35.56,90)}
    locations.update({n:(-12.7+i*5.08,35.56,270) for i,n in enumerate((4,9,11,14,15,18))})
    for unit in children(chip,'symbol'):
        for rect in children(unit,'rectangle'):
            child(rect,'start')[1:]=['-15.24','30.48'];child(rect,'end')[1:]=['15.24','-30.48']
        for pin in children(unit,'pin'):
            number=int(child(pin,'number')[1])
            child(pin,'at')[1:]=list(map(str,locations[number]))
            child(pin,'length')[1]='5.08'
            # SWRS061I Table 19: SPI inputs, tri-state SO, GDO2 output,
            # and the dedicated internally regulated DCOUPL supply output.
            if number in (1,2,3,5,7,20):pin[1]={1:'input',2:'tri_state',3:'output',5:'power_out',7:'input',20:'input'}[number]
    page=drawing.Sheet('cc-radio','CC1101 sub-GHz radio',13,
        '868/915MHz frontend: TI SWRR045 rev3.0 / SWRS061I Fig11. RF layout and tuning are NOT qualified. Separate 50-ohm antenna.',rootid,spec,instances,symbols)
    inst=page.place('U5',86.36,93.98)
    for name,yy in [('Reference',35.56),('Value',38.1)]:child(prop(inst,name),'at')[1:]=['86.36',str(yy),'0']
    for pin in ('4','9','11','14','15','18'):
        pos=page.pins['U5.'+pin][0];page.path('CC_VDD','U5.'+pin,(pos[0],50.8));page.dot((pos[0],50.8))
    page.path('CC_VDD',(73.66,50.8),(99.06,50.8),label=True)
    for ref,x,y,a in [('L5',129.54,83.82,90),('L6',129.54,104.14,90),('C63',154.94,93.98,0),
      ('L7',167.64,43.18,90),('C66',190.5,50.8,0),('C64',185.42,83.82,90),('L8',185.42,104.14,90),
      ('C68',154.94,129.54,0),('L9',233.68,93.98,90),('C65',254,119.38,0),('L10',279.4,93.98,90),('C67',314.96,93.98,90)]:page.passive(ref,x,y,a)
    page.place('J21',350.52,93.98)
    for net,a,z in [('CC_RF_P','U5.12','L5.1'),('CC_RF_N','U5.13','L6.1')]:page.path(net,a,z)
    page.path('CC_BAL_P','L5.2',(154.94,83.82),'C64.1')
    page.path('CC_BAL_P','C63.1',(154.94,83.82),(154.94,43.18),'L7.1');page.dot((154.94,83.82))
    page.path('CC_SHUNT','L7.2',(190.5,43.18),'C66.1')
    page.path('CC_BAL_N','L6.2',(154.94,104.14),'L8.1')
    page.path('CC_BAL_N','C63.2','C68.1');page.dot((154.94,104.14))
    page.path('CC_MATCH','C64.2',(210.82,83.82),(210.82,104.14),'L8.2')
    page.path('CC_MATCH',(210.82,93.98),'L9.1');page.dot((210.82,93.98))
    page.path('CC_LPF','L9.2',(254,93.98),'L10.1')
    page.path('CC_LPF','C65.1',(254,93.98));page.dot((254,93.98))
    page.path('CC_DC_BLOCK','L10.2','C67.1');page.path('CC_RF_50R','C67.2','J21.1')
    for net,xy in [('CC_RF_P',(114.3,83.82)),('CC_RF_N',(114.3,104.14)),
        ('CC_BAL_P',(154.94,83.82)),('CC_BAL_N',(154.94,104.14)),
        ('CC_SHUNT',(190.5,43.18)),('CC_MATCH',(210.82,93.98)),
        ('CC_LPF',(254,93.98)),('CC_DC_BLOCK',(294.64,93.98)),('CC_RF_50R',(340.36,93.98))]:
        page.label(net,xy,0,'right')
    for key in ('C66.2','C68.2','C65.2','J21.2'):
        pos=page.pins[key][0];page.path('GND',key,(pos[0],pos[1]+7.62),label=True)
    page.place('Y2',76.2,170.18)
    page.passive('C61',58.42,190.5);page.passive('C62',101.6,190.5)
    page.path('CC_X1','U5.8',(76.2,149.86),(58.42,149.86),(58.42,170.18),'Y2.1')
    page.path('CC_X1','C61.1',(58.42,170.18));page.dot((58.42,170.18))
    page.path('CC_X2','U5.10',(81.28,147.32),(101.6,147.32),(101.6,170.18),'Y2.3')
    page.path('CC_X2','C62.1',(101.6,170.18));page.dot((101.6,170.18))
    page.label('CC_X1',(58.42,170.18),0,'right');page.label('CC_X2',(101.6,170.18))
    for key in ('C61.2','C62.2'):
        pos=page.pins[key][0];page.path('GND',key,(pos[0],pos[1]+5.08),label=True)
    page.bank(['C11'],124.46,139.7);page.bank(['R11'],167.64,149.86)
    page.bank(['R12'],35.56,63.5);page.place('TP1',35.56,139.7)
    page.passive('L11',228.6,170.18,90)
    page.bank(['C12','C69','C70','C71','C72','C73','C74'],177.8,208.28)
    page.flag('C74.1')
    page.text('CC_VDD flag: main +3V3 through passive L11; not an independent source.\nPlace one 100nF at each supply pin group, plus local 1uF bulk.',177.8,233.68,1.1)
    page.text('Y2: ABM8-26.000MHZ-10-D-1-G-T\nCL = 15pF / 2 + estimated 2.5pF stray = 10pF.\nMeasure oscillator frequency, startup and drive level.',35.56,228.6,1.1)
    page.text('C126/L125 optional notch from TI reference is omitted.\nDetermine need by final conducted emissions. No 315/433MHz matching claim.\nGDO2 is a debug pad; set IOCFG2=0x2E when unused.',233.68,137.16,1.1)
    page.finish()
    lib=parse((OUT/'Handset.kicad_sym').read_text())
    for old in children(lib,'symbol'):
        if old[1]=='CC1101':lib.remove(old)
    entry=copy.deepcopy(chip);entry[1]=Q('CC1101');lib.append(entry)
    (OUT/'Handset.kicad_sym').write_text(dump(lib)+'\n')
    b=p.LoadBoard(str(SOURCE/'handset.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()}
    for ref in additions:
        c=spec[ref];lib,name=c['footprint'].split(':')
        f=p.FootprintLoad(str(OUT/'Handset.pretty') if lib=='Handset' else '/usr/share/kicad/footprints/'+lib+'.pretty',name)
        assert f,c['footprint'];f.SetReference(ref);f.SetValue(c['value']);f.SetFPID(p.LIB_ID(lib,name));b.Add(f)
        f.Flip(f.GetPosition(),False);f.Reference().SetLayer(p.B_Fab);f.Value().SetVisible(False)
        path=p.KIID_PATH()
        for ident in (rootid,page.id,uid(ref)):path.push_back(p.KIID(ident))
        f.SetPath(path);f.SetSheetname('CC1101 sub-GHz radio');f.SetSheetfile('cc-radio.kicad_sch');fps[ref]=f
        f.SetField('MPN',c['mpn']);f.GetField('MPN').SetVisible(False)
        if ref=='TP1':f.SetAttributes(f.GetAttributes() & ~p.FP_EXCLUDE_FROM_BOM)
    for ref in list(additions)+list(moves):
        c=spec[ref];f=fps[ref];f.SetPosition(p.VECTOR2I(p.FromMM(c['x']),p.FromMM(c['y'])));f.SetOrientationDegrees(c['angle']);f.SetValue(c['value'])
        f.Reference().SetLayer(p.B_Fab)
        for pad in f.Pads():
            name=c['nets'].get(pad.GetNumber())
            if name:
                net=b.FindNet(name)
                if not net:net=p.NETINFO_ITEM(b,name);b.Add(net)
                pad.SetNet(net)
    p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
    shutil.copy2(SOURCE/'handset.kicad_pro',OUT/'handset.kicad_pro')
    (OUT/'connectivity.json').write_text(json.dumps(list(spec.values()),indent=2)+'\n')
    with (OUT/'placement.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec.values())
    with (OUT/'cc1101-bom.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=['ref','value','mpn','footprint','role'],extrasaction='ignore');w.writeheader()
        w.writerows(spec[ref] for ref in additions+['C11','C12'])
    (OUT/'cc1101-update.json').write_text(json.dumps(dict(
        source_hashes={str(f.relative_to(SOURCE)):hashlib.sha256(f.read_bytes()).hexdigest() for f in SOURCE.rglob('*') if f.is_file() and f.suffix in ('.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym','.kicad_mod','.json','.csv')},
        added_refs=additions,changed_refs=list(moves),components=len(spec),fabrication_released=False,
        scope='CC1101 circuit completion and initial placement; RF routing/tuning not qualified'),indent=2)+'\n')
    print('Staged CC1101:',len(additions),'new parts;',len(spec),'total')


if __name__=='__main__':main()
