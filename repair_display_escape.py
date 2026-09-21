"""Make room for the display ground via by straightening a backlight escape jog."""
from pathlib import Path
import pcbnew
pcbnew.SwigPyIterator.next=pcbnew.SwigPyIterator.__next__
p=Path(__file__).resolve().parent/'revF-gps-expansion/owasso1.kicad_pcb'
b=pcbnew.LoadBoard(str(p));obsolete=[]
for t in b.GetTracks():
    if t.m_Uuid.AsString()=='a0765733-9e19-43cd-ba20-77b2e54d0bf7':t.SetPosition(pcbnew.VECTOR2I(99600000,76600000))
    if t.GetNetname()=='/GND' and not isinstance(t,pcbnew.PCB_VIA):
        if any(abs(t.GetStart().x/1e6-x)<.001 and abs(t.GetStart().y/1e6-y)<.001 for x,y in [(98.7,76.6),(97.8,76.6),(97.8,79.1)]):obsolete.append(t)
    if t.GetNetname()=='/LCD_BL' and not isinstance(t,pcbnew.PCB_VIA):
        for getter,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
            v=getter()
            if 99.6<v.x/1e6<100 and 77<v.y/1e6<77.11:setter(pcbnew.VECTOR2I(v.x,77170000))
for t in obsolete:b.Remove(t)
b.Save(str(p))
