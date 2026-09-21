#!/usr/bin/env python3
import os, sys
os.environ['LD_LIBRARY_PATH'] = os.path.expanduser('~/.local/kicad-compat')
import pcbnew

path = sys.argv[1]
b = pcbnew.LoadBoard(path)
nc = b.GetDesignSettings().m_NetSettings.GetDefaultNetclass()
nc.SetTrackWidth(pcbnew.FromMM(0.15))
nc.SetClearance(pcbnew.FromMM(0.15))
b.GetDesignSettings().m_TrackMinWidth = pcbnew.FromMM(0.15)
b.GetDesignSettings().m_MinClearance = pcbnew.FromMM(0.15)
if not b.Save(path): raise SystemExit('save failed')
print(path)
