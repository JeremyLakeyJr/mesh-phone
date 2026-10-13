"""Finish staged CC1101 fanout against native clearance and connector keepouts."""
from cad_sexpr import parse, dump, child
import pcbnew as p


def finish_board(b, out, original_ids):
    xy = lambda pos: tuple(round(p.ToMM(v), 4) for v in pos)
    point = lambda pos: p.VECTOR2I(*(p.FromMM(v) for v in pos))
    remove = set()
    moved = {'CC_CS': 0, 'CC_GDO2': 0}
    supply = {
        ((118.8, 38.5), (118.3, 38.5)),
        ((118.3, 38.5), (117.78, 39.02)),
        ((117.78, 39.02), (117.78, 39.4)),
    }
    testpoint = {
        ((120.0, 34.4), (119.55, 33.95)),
        ((119.55, 33.95), (119.55, 33.25)),
        ((119.55, 33.25), (120.4, 32.4)),
    }
    unused_mosi = {
        ((120.5, 40.95), (118.8, 40.95)),
        ((118.8, 40.95), (118.45, 41.3)),
    }
    counts = {'CC_VDD': 0, 'CC_GDO2': 0, 'SPI_MOSI': 0}
    seen = set()
    for t in b.GetTracks():
        uid = t.m_Uuid.AsString()
        if uid in original_ids:
            continue
        net = t.GetNetname()
        if t.GetClass() == 'PCB_VIA':
            if net == 'CC_GDO2' and xy(t.GetPosition()) == (118.65, 39.05):
                t.SetPosition(point((118.65, 39.08)))
                moved[net] += 1
            if net == 'SPI_MOSI' and xy(t.GetPosition()) == (118.45, 41.3):
                remove.add(uid)
                counts[net] += 1
            continue
        ends = (xy(t.GetStart()), xy(t.GetEnd()))
        targets = supply if net == 'CC_VDD' else testpoint if net == 'CC_GDO2' else unused_mosi if net == 'SPI_MOSI' else set()
        if t.GetLayer() == p.B_Cu and (ends in targets or ends[::-1] in targets):
            remove.add(uid)
            counts[net] += 1
            continue
        for getter, setter in [(t.GetStart, t.SetStart), (t.GetEnd, t.SetEnd)]:
            if net == 'CC_CS' and xy(getter()) == (121, 36.7):
                setter(point((121, 36.55)))
                moved[net] += 1
            if net == 'CC_GDO2' and xy(getter()) == (118.65, 39.05):
                setter(point((118.65, 39.08)))
                moved[net] += 1
        key = (net, t.GetLayer(), t.GetWidth(), tuple(sorted((xy(t.GetStart()), xy(t.GetEnd())))))
        if key in seen:
            remove.add(uid)
        else:
            seen.add(key)
    assert counts == {'CC_VDD': 3, 'CC_GDO2': 3, 'SPI_MOSI': 3}, counts
    assert moved['CC_CS'] == 2 and moved['CC_GDO2'] >= 3, moved
    raw = out / 'before-local-finish.kicad_pcb'
    p.SaveBoard(str(raw), b)
    tree = parse(raw.read_text())
    tree[:] = [n for n in tree if not (isinstance(n, list) and n and n[0] in ('segment', 'via') and child(n, 'uuid')[1] in remove)]
    clean = out / 'local-finish.kicad_pcb'
    clean.write_text(dump(tree) + '\n')
    b = p.LoadBoard(str(clean))
    for net, width, points in [
        ('CC_VDD', .2, [(118.8, 38.5), (118.73, 38.57), (118.3, 38.57), (117.78, 39.09), (117.78, 39.4)]),
        ('CC_GDO2', .15, [(120, 34.4), (119.85, 34.25), (119.85, 32.95), (120.4, 32.4)]),
    ]:
        for a, z in zip(points, points[1:]):
            t = p.PCB_TRACK(b)
            t.SetStart(point(a))
            t.SetEnd(point(z))
            t.SetWidth(p.FromMM(width))
            t.SetLayer(p.B_Cu)
            t.SetNet(b.FindNet(net))
            b.Add(t)
    return b
