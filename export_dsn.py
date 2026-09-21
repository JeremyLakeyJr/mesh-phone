#!/usr/bin/env python3
import os
import sys
os.environ["LD_LIBRARY_PATH"] = os.path.expanduser("~/.local/kicad-compat")
import pcbnew

board_path = sys.argv[1] if len(sys.argv) > 1 else "owasso1.kicad_pcb"
dsn_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/owasso1.dsn"
board = pcbnew.LoadBoard(board_path)
if not pcbnew.ExportSpecctraDSN(board, dsn_path):
    raise SystemExit("Specctra DSN export failed")
print(dsn_path)
