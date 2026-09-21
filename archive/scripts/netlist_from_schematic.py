#!/usr/bin/env python3
"""Convert KiCad's legacy sexpr netlist into rebuild_pcb.py's draft JSON."""
import json
import re
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
sch = root / "owasso1.kicad_sch"
net = Path("/tmp/owasso1-from-sch.net")
subprocess.run(["kicad-cli", "sch", "export", "netlist", "-o", str(net), str(sch)], check=True)
text = net.read_text()

parts = []
for block in re.findall(r"\(comp\s+(.*?)\n\s*\)\n\s*\(comp|\n\s*\)\n\s*\(nets", text, re.S):
    pass

# Component blocks are bounded by the next top-level component or nets list.
components_section = text.split("\n\t(components\n", 1)[1].split("\n\t(nets\n", 1)[0]
for block in re.findall(r"\t\t\(comp\n(.*?)(?=\n\t\t\(comp\n|\Z)", components_section, re.S):
    ref = re.search(r'\(ref "([^"]+)"\)', block)
    value = re.search(r'\(value "([^"]*)"\)', block)
    footprint = re.search(r'\(footprint "([^"]*)"\)', block)
    if ref:
        parts.append({
            "ref": ref.group(1),
            "value": value.group(1) if value else "",
            "fp": footprint.group(1) if footprint and footprint.group(1) else None,
        })

nets = []
nets_section = text.split("\n\t(nets\n", 1)[1]
for block in re.findall(r"\t\t\(net\n(.*?)(?=\n\t\t\(net\n|\n\t\)\n\))", nets_section, re.S):
    name_match = re.search(r'\(name "([^"]*)"\)', block)
    if not name_match:
        continue
    name = name_match.group(1).lstrip("/")
    if name.startswith("unconnected-("):
        continue
    nodes = [[r, p] for r, p in re.findall(r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', block)]
    if nodes:
        nets.append({"name": name, "nodes": nodes})

out = {"parts": parts, "nets": nets}
(root / "netlist_draft.json").write_text(json.dumps(out, indent=2) + "\n")
print(f"Wrote netlist_draft.json: {len(parts)} parts, {len(nets)} named nets")
