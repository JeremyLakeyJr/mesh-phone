#!/usr/bin/env python3
import os
import sys
os.environ["LD_LIBRARY_PATH"] = os.path.expanduser("~/.local/kicad-compat")
import pcbnew

board_path = sys.argv[1] if len(sys.argv) > 1 else "owasso1.kicad_pcb"
ses_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/owasso1.ses"
out_path = sys.argv[3] if len(sys.argv) > 3 else "owasso1-routed.kicad_pcb"
board = pcbnew.LoadBoard(board_path)
if not pcbnew.ImportSpecctraSES(board, ses_path):
    raise SystemExit("Specctra SES import failed")
# Keep the imported candidate on the same fab rules as the placement source.
# FreeRouting emits 0.15 mm traces and the source footprints require 0.20 mm
# drills with 0.18 mm shell-to-pad clearance.
design = board.GetDesignSettings()
design.m_TrackMinWidth = pcbnew.FromMM(0.15)
design.m_MinThroughDrill = pcbnew.FromMM(0.20)
design.m_HoleClearance = pcbnew.FromMM(0.18)
try:
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
except Exception as exc:
    print(f"Zone refill skipped: {exc}")
if not board.Save(out_path):
    raise SystemExit("Could not save routed board")
print(out_path)
