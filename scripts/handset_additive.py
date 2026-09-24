"""Add a sheet and matching physical footprints to an existing handset project."""
import copy
import csv
import json
import math
from pathlib import Path
import uuid
import pcbnew as p
from cad_sexpr import Q, parse, dump, child, children, prop

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/handset-rev-a/generated'
p.SwigPyIterator.next=p.SwigPyIterator.__next__

def add_sheet(name, entries, symbols, page, position):
    """Caller must snapshot first. Preserve existing sheets, copper and placement."""
    b=p.LoadBoard(str(OUT/'handset.kicad_pcb'))
    existing={f.GetReference() for f in b.GetFootprints()}
    assert not existing.intersection(c['ref'] for c in entries)
    uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'handset-'+name+'/'+s))
    root=parse((OUT/'handset.kicad_sch').read_text());rootid=child(root,'uuid')[1];sid=uid('sheet')
    sch=parse(f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{sid}") (paper "A2") (lib_symbols))')
    seen=set()
    for i,c in enumerate(entries):
        c['sheet']=name;c['nets']={str(k):n for k,n in c['nets'].items()}
        if c['libid'] in symbols:s=copy.deepcopy(symbols[c['libid']])
        else:
            lib,part=c['libid'].split(':')
            s=copy.deepcopy(next(s for s in children(parse(Path('/usr/share/kicad/symbols',lib+'.kicad_sym').read_text()),'symbol') if s[1]==part))
        assert child(s,'extends') is None
        s[1]=Q(c['libid'])
        if c['libid'] not in seen:child(sch,'lib_symbols').append(s);seen.add(c['libid'])
        sx=63.5+(i%4)*132.08;sy=63.5+(i//4)*76.2;ref=c['ref']
        inst=parse(f'''(symbol (lib_id "{c['libid']}") (at {sx} {sy} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid(ref)}")
         (property "Reference" "{ref}" (at {sx} {sy-27.94} 0) (effects (font (size 1.27 1.27))))
         (property "Value" "{c['value']}" (at {sx} {sy-25.4} 0) (effects (font (size 1.27 1.27))))
         (property "Footprint" "{c['footprint']}" (at {sx} {sy} 0) (effects (font (size 1.27 1.27)) (hide yes)))
         (instances (project "handset" (path "/{rootid}/{sid}" (reference "{ref}") (unit 1)))))''')
        for u in children(s,'symbol'):
            for pin in children(u,'pin'):
                num=str(child(pin,'number')[1]);at=child(pin,'at');px=sx+float(at[1]);py=sy-float(at[2]);a=float(at[3]);net=c['nets'].get(num)
                inst.append(parse(f'(pin "{num}" (uuid "{uid(ref+num)}"))'))
                if net:
                    ex=round(px-5.08*math.cos(math.radians(a)),6);ey=round(py+5.08*math.sin(math.radians(a)),6)
                    sch.append(parse(f'(wire (pts (xy {px} {py}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(ref+num+"w")}"))'))
                    sch.append(parse(f'(global_label "{net}" (shape input) (at {ex} {ey} {a}) (effects (font (size 1 1)) (justify left)) (uuid "{uid(ref+num+"l")}"))'))
                else:sch.append(parse(f'(no_connect (at {px} {py}) (uuid "{uid(ref+num+"nc")}"))'))
        sch.append(inst)
        lib,part=c['footprint'].split(':');f=p.FootprintLoad(str(OUT/'Handset.pretty') if lib=='Handset' else '/usr/share/kicad/footprints/'+lib+'.pretty',part)
        assert f,c['footprint']
        f.SetReference(ref);f.SetValue(c['value']);f.SetFPID(p.LIB_ID(lib,part));b.Add(f)
        f.SetPosition(p.VECTOR2I(p.FromMM(c['x']),p.FromMM(c['y'])))
        if c.get('side','B')=='B':f.Flip(f.GetPosition(),False)
        f.SetOrientationDegrees(c.get('angle',0));f.Value().SetVisible(False)
        path=p.KIID_PATH()
        for ident in (str(rootid),sid,uid(ref)):path.push_back(p.KIID(ident))
        f.SetPath(path)
        for pad in f.Pads():
            net=c['nets'].get(pad.GetNumber())
            if net:
                n=b.FindNet(net)
                if not n:n=p.NETINFO_ITEM(b,net);b.Add(n)
                pad.SetNet(n)
    x,y=position
    root.append(parse(f'''(sheet (at {x} {y}) (size 90 35) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0)) (uuid "{sid}")
     (property "Sheetname" "{name}" (at {x} {y-1} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
     (property "Sheetfile" "{name}.kicad_sch" (at {x} {y+36} 0) (effects (font (size 1.27 1.27)) (justify left top)))
     (instances (project "handset" (path "/{rootid}" (page "{page}")))))'''))
    (OUT/'handset.kicad_sch').write_text(dump(root)+'\n');(OUT/(name+'.kicad_sch')).write_text(dump(sch)+'\n')
    libroot=parse((OUT/'Handset.kicad_sym').read_text())
    for libid,s in symbols.items():
        entry=copy.deepcopy(s);entry[1]=Q(libid.split(':')[1]);libroot.append(entry)
    (OUT/'Handset.kicad_sym').write_text(dump(libroot)+'\n')
    spec=json.loads((OUT/'connectivity.json').read_text())+entries
    p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
    (OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
    with (OUT/'placement.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec)
