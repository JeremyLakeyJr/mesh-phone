"""Bridge the verified front ground island to the rear main ground plane."""
from pathlib import Path
import pcbnew
pcbnew.SwigPyIterator.next=pcbnew.SwigPyIterator.__next__
p=Path(__file__).resolve().parent/'revF-gps-expansion/owasso1.kicad_pcb'
b=pcbnew.LoadBoard(str(p))
via=pcbnew.PCB_VIA(b)
via.SetPosition(pcbnew.VECTOR2I(103950000,80000000));via.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
via.SetWidth(pcbnew.FromMM(.5));via.SetDrill(pcbnew.FromMM(.3));via.SetNet(b.FindNet('/GND'));b.Add(via)
b.Save(str(p))
