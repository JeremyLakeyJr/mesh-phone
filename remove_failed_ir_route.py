import pcbnew
path='/home/lakey/Documents/owasso1-pcb/owasso1-routed-user-edit.kicad_pcb'
b=pcbnew.LoadBoard(path)
for item in list(b.GetTracks()):
    if item.GetNetname() == 'IR_TX':
        b.Remove(item)
b.Save(path)
print(path)
