#!/usr/bin/env python3
"""Check local PA/RF-input continuity and geometry; no impedance/RF approval."""
import json,math,sys
from pathlib import Path
import pcbnew as p
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
GROUPS={'SX_VR_PA':'U4.24 L13.1 C10.1 C101.1',
        'SX_RFO':'U4.23 L13.2 U36.1','SX_RFI_N':'U4.22 U36.3','SX_RFI_P':'U4.21 U36.4',
        'GND':'U1.1 C10.2 C101.2'}
RF_NETS=('SX_RFO','SX_RFI_N','SX_RFI_P')

def check_board(b):
    b.BuildConnectivity();pads={f.GetReference()+'.'+q.GetNumber():q for f in b.GetFootprints() for q in f.Pads()}
    checks=[];lengths={};missing=[];samples=0
    def check(name,passed):checks.append(dict(check=name,passed=bool(passed)))
    for net,names in GROUPS.items():
        entries=[pads[key] for key in names.split()];seed=entries[0]
        connected=list(b.GetConnectivity().GetConnectedItems(seed));ids={q.m_Uuid.AsString() for q in connected}|{seed.m_Uuid.AsString()}
        check(net+' continuity',all(q.GetNetname()==net and q.m_Uuid.AsString() in ids for q in entries) and all(q.GetNetname()==net for q in connected))
    for ref in ['U4','L13','C10','C101','U36']:
        f=next(f for f in b.GetFootprints() if f.GetReference()==ref)
        check(ref+' back-layer placement',f.GetLayer()==p.B_Cu)
    planes=[z.GetFilledPolysList(p.In2_Cu) for z in b.Zones() if z.GetNetname()=='GND' and z.IsOnLayer(p.In2_Cu)]
    for net in RF_NETS+('SX_VR_PA',):
        copper=[t for t in b.GetTracks() if t.GetNetname()==net]
        check(net+' local back-layer copper without vias',bool(copper) and all(t.GetClass()=='PCB_TRACK' and t.GetLayer()==p.B_Cu for t in copper))
        lengths[net]=round(sum(p.ToMM(t.GetLength()) for t in copper if t.GetClass()=='PCB_TRACK'),4)
        # Engineering bounds prevent accidental long detours; not RF electrical lengths.
        check(net+' bounded route length',0<lengths[net]<(6 if net in ('SX_RFO','SX_VR_PA') else 4))
        if net not in RF_NETS:continue
        for t in copper:
            if t.GetClass()!='PCB_TRACK':continue
            a=(p.ToMM(t.GetStart().x),p.ToMM(t.GetStart().y));z=(p.ToMM(t.GetEnd().x),p.ToMM(t.GetEnd().y));d=math.dist(a,z)
            if not d:continue
            n=(-(z[1]-a[1])/d,(z[0]-a[0])/d);steps=max(1,math.ceil(d/.1))
            for i in range(steps+1):
                for offset in (0,-p.ToMM(t.GetWidth())/2-.1,p.ToMM(t.GetWidth())/2+.1):
                    pt=(a[0]+(z[0]-a[0])*i/steps+n[0]*offset,a[1]+(z[1]-a[1])*i/steps+n[1]*offset);samples+=1
                    if not any(poly.Contains(p.VECTOR2I(p.FromMM(pt[0]),p.FromMM(pt[1]))) for poly in planes):missing.append(pt)
    check('filled In2 ground beneath RF input corridors',not missing)
    ground_captured=any(z.GetZoneName()=='SX1262 IPD ground' for z in b.Zones())
    return dict(passed=all(c['passed'] for c in checks),checks=checks,
                route_lengths_mm=lengths,reference_samples=samples,reference_gaps=missing,
                physical_pads=sum(len(v.split()) for v in GROUPS.values()),
                qualification_open=[
                    ('U36 grounds are captured; validate detailed return geometry and complete downstream TX/RX switch/antenna copper.' if ground_captured else 'U36 ground lands/via geometry and downstream TX/RX switch/antenna copper remain incomplete.'),
                    'The 0.2mm RF input fanouts are local routing candidates, not validated 50-ohm lines; resolve geometry against Johanson layout and selected stackup.',
                    ('The scoped 0.2mm ground-via rule is captured; confirm hole/tenting and reference-layout implementation with the fabricator.' if ground_captured else 'Johanson specifies crucial 0.2mm ground vias; reconcile the selected implementation with board/fabricator drill rules before release.'),
                    'Qualify clock, PA supply/thermal behavior, RF matching, conducted power/harmonics, receive sensitivity and antenna coexistence.'],
                fabrication_released=False)

if __name__=='__main__':
    out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
    r=check_board(p.LoadBoard(str(out/'handset.kicad_pcb')))
    (out/'sx1262-local-rf-checks.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));sys.exit(not r['passed'])
