#!/usr/bin/env python3
"""Make a temporary router profile compatible with the board's 0.15 mm escape space."""
from pathlib import Path
import sys

src, dst = map(Path, sys.argv[1:3])
s = src.read_text()
# FreeRouting stores DSN dimensions in micrometres. Keep this temporary route
# profile separate from the PCB's fabrication rules; imported traces are
# normalized and DRC-checked before promotion.
s = s.replace("(width 200)\n        (clearance 200)",
              "(width 150)\n        (clearance 150)")
s = s.replace("(width 200)\n        (clearance 200)",
              "(width 150)\n        (clearance 150)")
dst.write_text(s)
print(dst)
