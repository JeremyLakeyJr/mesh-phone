from pathlib import Path
import pcbnew
pcbnew.SwigPyIterator.next=pcbnew.SwigPyIterator.__next__
p=Path(__file__).resolve().parent/'revF-gps-expansion/owasso1.kicad_pcb'
b=pcbnew.LoadBoard(str(p))
obsolete=[]
for t in b.GetTracks():
    if t.m_Uuid.AsString()=='a0765733-9e19-43cd-ba20-77b2e54d0bf7':t.SetPosition(pcbnew.VECTOR2I(98200000,79100000))
    if t.m_Uuid.AsString()=='fca9a68e-0afb-4706-a8d1-bbff4624312b':obsolete.append(t)
points=[(98.7,76.6),(97.8,76.6),(97.8,79.1),(98.2,79.1)]
for (x,y),(u,v) in zip(points,points[1:]):
    t=pcbnew.PCB_TRACK(b);t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y)));t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(u),pcbnew.FromMM(v)))
    t.SetWidth(pcbnew.FromMM(.2));t.SetLayer(pcbnew.F_Cu);t.SetNet(b.FindNet('/GND'));b.Add(t)
for t in obsolete:b.Remove(t)
b.Save(str(p))
