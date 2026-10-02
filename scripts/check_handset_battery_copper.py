#!/usr/bin/env python3
"""Resistance screening of the serial J1-to-F2 route, not thermal qualification."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
from cad_sexpr import parse, child, children


def serial_route(segments, start, end, thickness_um=35, temperature_c=20):
    if thickness_um <= 0 or not math.isfinite(thickness_um):
        raise ValueError('Positive finite copper thickness required')
    factor=1+0.00393*(temperature_c-20)
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError('Invalid temperature assumption')
    graph=defaultdict(list)
    for index,(a,b,width) in enumerate(segments):
        if width <= 0 or not math.isfinite(width) or a == b:
            raise ValueError('Invalid trace geometry')
        graph[a].append((b,index));graph[b].append((a,index))
    if start not in graph or end not in graph or start == end:
        raise ValueError('Missing route endpoints')
    if any(len(edges)!=(1 if point in (start,end) else 2) for point,edges in graph.items()):
        raise ValueError('Branched or disconnected path; re-audit resistance model')
    used=set();point=start
    while point != end:
        choices=[(other,index) for other,index in graph[point] if index not in used]
        if len(choices)!=1:
            raise ValueError('Path is not a single serial route')
        point,index=choices[0];used.add(index)
    if len(used)!=len(segments):
        raise ValueError('Disconnected copper outside route')
    length=sum(math.dist(a,b) for a,b,w in segments)
    # 1.724e-8 ohm*m at 20 C; dimensions converted from mm and micrometres.
    resistance=sum(1.724e-8*math.dist(a,b)/(w*thickness_um*1e-6) for a,b,w in segments)*factor
    return dict(length_mm=length,resistance_ohm=resistance,
                minimum_width_mm=min(w for a,b,w in segments),
                maximum_width_mm=max(w for a,b,w in segments))


def inspect(path):
    import pcbnew as p
    p.SwigPyIterator.next=p.SwigPyIterator.__next__
    board=p.LoadBoard(str(path));fps={f.GetReference():f for f in board.GetFootprints()}
    def endpoint(ref,number):
        pad=next(pad for pad in fps[ref].Pads() if pad.GetNumber()==number)
        assert pad.GetNetname()=='BAT_PACK_POS'
        return tuple(round(p.ToMM(v),6) for v in (pad.GetPosition().x,pad.GetPosition().y))
    tree=parse(path.read_text());segments=[]
    for kind in ('segment','via','arc','zone'):
        for item in children(tree,kind):
            net=child(item,'net')
            if net and net[1]=='BAT_PACK_POS':
                if kind!='segment' or child(item,'layer')[1]!='B.Cu':
                    raise ValueError('Route topology changed; re-audit layer/via/plane model')
                segments.append((tuple(float(v) for v in child(item,'start')[1:]),
                                 tuple(float(v) for v in child(item,'end')[1:]),float(child(item,'width')[1])))
    start,end=endpoint('J1','1'),endpoint('F2','1')
    cases=[]
    for thickness in (18,35):
        for temp in (20,70):
            result=serial_route(segments,start,end,thickness,temp)
            cases.append(dict(copper_thickness_um_assumed=thickness,copper_temperature_c_assumed=temp,
                **result,loads=[dict(current_a=current,voltage_drop_v=current*result['resistance_ohm'],
                    dissipation_w=current**2*result['resistance_ohm']) for current in (3.302,5.0)]))
    return dict(scope='J1.1 to F2.1 only; excludes fuse, contact, harness, VBAT distribution and return',
        board_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),segment_count=len(segments),cases=cases,
        assumptions='18/35 um copper and 20/70 C are sensitivity cases, not fabrication or temperature specifications. Uniform cross-section DC model excludes pads and spreading.',
        thermal_current_rating_established=False,fabrication_released=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('board',type=Path);args=parser.parse_args()
    report=inspect(args.board)
    (args.board.parent/'battery-copper-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
