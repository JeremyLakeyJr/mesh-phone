"""DRC-guided relocation of three ground vias and removal of a redundant trial."""
from pathlib import Path
import pcbnew
pcbnew.SwigPyIterator.next=pcbnew.SwigPyIterator.__next__
p=Path(__file__).resolve().parent/'revF-gps-expansion/owasso1.kicad_pcb'
b=pcbnew.LoadBoard(str(p))
moves={(99.6,76.57):(97.4,76.6)}
for f in b.GetFootprints():
    if f.GetReference()=='C7':f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(107.5),pcbnew.FromMM(71)))
for t in b.GetTracks():
    if isinstance(t,pcbnew.PCB_VIA):continue
    if t.m_Uuid.AsString()=='1876f5ec-2bc8-485c-83b0-a1008816728c':
        t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(106.725),pcbnew.FromMM(71)))
track=pcbnew.PCB_TRACK(b)
track.SetStart(pcbnew.VECTOR2I(98700000,76600000));track.SetEnd(pcbnew.VECTOR2I(97400000,76600000))
track.SetWidth(pcbnew.FromMM(.2));track.SetLayer(pcbnew.F_Cu);track.SetNet(b.FindNet('/GND'));b.Add(track)
via=pcbnew.PCB_VIA(b)
via.SetPosition(pcbnew.VECTOR2I(103950000,76200000));via.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
via.SetWidth(pcbnew.FromMM(.5));via.SetDrill(pcbnew.FromMM(.3));via.SetNet(b.FindNet('/GND'));b.Add(via)
remove=[]
for t in b.GetTracks():
    if not isinstance(t,pcbnew.PCB_VIA) or t.GetNetname()!='/GND':continue
    pos=(round(t.GetPosition().x/1e6,3),round(t.GetPosition().y/1e6,3))
    if pos==(98.8,76.6):remove.append(t)
    if pos in moves:
        x,y=moves[pos]; t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y)))
for t in remove:b.Remove(t)
b.Save(str(p))
