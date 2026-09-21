#!/usr/bin/env python3
"""Add rev-D power/keypad parts to the last known-good schematic scaffold."""
import json
import re
import uuid
from pathlib import Path

root = Path(__file__).resolve().parent
sch_path = root / "owasso1.kicad_sch"
text = sch_path.read_text()
draft = json.loads((root / "netlist_draft.json").read_text())

def symbol_blocks(source):
    """Yield (start, end, block) for top-level schematic symbol instances."""
    marker = "\n\t(symbol\n"
    pos = 0
    while True:
        start = source.find(marker, pos)
        if start < 0:
            return
        start += 1  # point at the opening parenthesis
        depth = 0
        end = start
        in_string = False
        escaped = False
        for i in range(start, len(source)):
            ch = source[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        yield start, end, source[start:end]
        pos = end

def symbol_ref(block):
    m = re.search(r'\(property "Reference" "([^"]+)"', block)
    return m.group(1) if m else None

# D18 was removed from the corrected synchronous boost design. Remove its old
# schematic instance before comparing references, otherwise the schematic
# keeps advertising a part that is no longer present on the PCB.
for start, end, block in reversed(list(symbol_blocks(text))):
    if symbol_ref(block) == "D18":
        text = text[:start] + text[end:]

def update_properties(source, ref, value, fp):
    for start, end, block in list(symbol_blocks(source)):
        if symbol_ref(block) != ref:
            continue
        block = re.sub(r'(\(property "Value" ")[^"]*(")',
                       lambda m: m.group(1) + value + m.group(2), block, count=1)
        block = re.sub(r'(\(property "Footprint" ")[^"]*(")',
                       lambda m: m.group(1) + (fp or "") + m.group(2), block, count=1)
        source = source[:start] + block + source[end:]
        break
    return source

# Refresh the existing scaffold's value/footprint metadata, including U8's
# new TPS61023 footprint and the corrected FPC/card connector footprints.
for p in draft["parts"]:
    text = update_properties(text, p["ref"], p["value"], p.get("fp"))

existing = set(re.findall(r'\(property "Reference" "([^"]+)"', text))
# Remove schematic instances that are no longer present in the authoritative
# generated netlist (for example the removed camera subsystem).
draft_refs = {p["ref"] for p in draft["parts"]}
for start, end, block in reversed(list(symbol_blocks(text))):
    ref = symbol_ref(block)
    if ref and ref not in draft_refs:
        text = text[:start] + text[end:]
existing = set(re.findall(r'\(property "Reference" "([^"]+)"', text))
new_parts = [p for p in draft["parts"] if p["ref"] not in existing]

def uid(): return str(uuid.uuid4())
def pin_y(n, pin):
    """Return global Y for the connector symbol's numbered pin.

    KiCad's schematic Y axis is inverted relative to the symbol-library
    coordinates.  Conn_01x04 pin 1 is therefore at instance_y-2.54,
    while Conn_01x06 pin 1 is at instance_y-5.08.
    """
    # Connector_Generic is generated with an intentional half-stack offset
    # for even widths: Conn_01x02 is at 0,-2.54 and Conn_01x04 is at
    # +2.54,0,-2.54,-5.08.  Odd widths are centered.  This is the exact
    # library rule, not a visual approximation.
    return (int(n / 2) + (n % 2) - int(pin)) * 2.54

nodes = {}
for n in draft["nets"]:
    for ref, pin in n["nodes"]:
        nodes.setdefault((ref, str(pin)), []).append(n["name"])

instances = []
for i, p in enumerate(new_parts):
    ref = p["ref"]
    n = 8 if ref == "J11" else (6 if ref in {"U8", "Q1"} else 4)
    x = 170 + (i % 6) * 38
    y = 40 + (i // 6) * 25
    lib = f"Connector_Generic:Conn_01x{n:02d}"
    instances.append(f'''\t(symbol
\t\t(lib_id "{lib}")
\t\t(at {x} {y} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
\t\t(uuid "{uid()}")
\t\t(property "Reference" "{ref}" (at {x} {y-8} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "{p["value"]}" (at {x} {y+8} 0) (effects (font (size 1.0 1.0))))
\t\t(property "Footprint" "{p.get("fp") or ""}" (at {x} {y} 0) (hide yes) (effects (font (size 1.0 1.0))))
\t\t(instances (project "owasso1" (path "/{uid()}" (reference "{ref}") (unit 1))))
\t)''')
insert = "\n".join(instances) + "\n"
marker = "\n)"
head, tail = text.rsplit(marker, 1)
text = head + "\n" + insert + "\n)" + tail

def strip_top_level_labels(source):
    blocks = []
    pos = 0
    while True:
        start = source.find("\n\t(label ", pos)
        if start < 0:
            break
        start += 1
        depth = 0
        in_string = False
        escaped = False
        end = start
        for i in range(start, len(source)):
            ch = source[i]
            if in_string:
                if escaped: escaped = False
                elif ch == "\\": escaped = True
                elif ch == '"': in_string = False
                continue
            if ch == '"': in_string = True
            elif ch == '(' : depth += 1
            elif ch == ')' :
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        blocks.append((start, end))
        pos = end
    for start, end in reversed(blocks):
        source = source[:start] + source[end:]
    return source

def strip_top_level_wires(source):
    blocks = []
    pos = 0
    while True:
        start = source.find("\n\t(wire\n", pos)
        if start < 0:
            break
        start += 1
        depth = 0
        in_string = False
        escaped = False
        end = start
        for i in range(start, len(source)):
            ch = source[i]
            if in_string:
                if escaped: escaped = False
                elif ch == "\\": escaped = True
                elif ch == '"': in_string = False
                continue
            if ch == '"': in_string = True
            elif ch == '(' : depth += 1
            elif ch == ')' :
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        blocks.append((start, end))
        pos = end
    for start, end in reversed(blocks):
        source = source[:start] + source[end:]
    return source

PIN_COUNTS = {
    "U1": 41, "U2": 16, "U3": 8, "U4": 6, "U5": 5, "U6": 4,
    "U7": 3, "U8": 6, "U9": 5, "U10": 5,
    "USB1": 22,
    "J1": 23, "J2": 8, "J3": 22, "J4": 4, "J5": 5, "J6": 5,
    "J7": 18, "J8": 24, "J9": 10, "J10": 8, "J11": 8, "J12": 4,
    "SW1": 2, "Q1": 6,
}

def pin_count(ref):
    if ref in PIN_COUNTS:
        return PIN_COUNTS[ref]
    nums = []
    for (r, pin) in nodes:
        if r != ref:
            continue
        m = re.fullmatch(r"\d+", pin)
        if m:
            nums.append(int(pin))
        elif pin.startswith("C") or pin == "CSW":
            nums.append(6)
    return max(2, max(nums, default=2))

# Rebuild the visible schematic instances as correctly-sized generic symbols.
# This keeps the schematic readable while ensuring every numbered net node has
# a real pin; the prior scaffold used Conn_01x04 for almost everything.
text = strip_top_level_labels(text)
text = strip_top_level_wires(text)
ref_order = [p["ref"] for p in draft["parts"]]
for idx, ref in enumerate(ref_order):
    n = pin_count(ref)
    # Keep every instance origin on KiCad's 2.54 mm connection grid.
    x = 76.2 + (idx % 4) * 127.0
    y = 50.8 + (idx // 4) * 101.6
    for start, end, block in list(symbol_blocks(text)):
        if symbol_ref(block) != ref:
            continue
        block = re.sub(r'\(lib_id "[^"]+"\)',
                       f'(lib_id "Connector_Generic:Conn_01x{n:02d}")', block, count=1)
        block = re.sub(r'\n\t\t\(at [^\n]+\)',
                       f'\n\t\t(at {x} {y} 0)', block, count=1)
        block = re.sub(r'(\(property "Reference" "' + re.escape(ref) + r'" \(at )[^ ]+ [^ ]+',
                       rf'\g<1>{x} {y-8}', block, count=1)
        block = re.sub(r'(\(property "Value" ")[^"]*(")',
                       lambda m, ref=ref: m.group(1) + next(p["value"] for p in draft["parts"] if p["ref"] == ref) + m.group(2), block, count=1)
        fp = next(p.get("fp") or "" for p in draft["parts"] if p["ref"] == ref)
        block = re.sub(r'(\(property "Footprint" ")[^"]*(")',
                       lambda m: m.group(1) + fp + m.group(2), block, count=1)
        text = text[:start] + block + text[end:]
        break

labels = []
wires = []
no_connects = []
for idx, p in enumerate(draft["parts"]):
    ref = p["ref"]
    n = pin_count(ref)
    x = 76.2 + (idx % 4) * 127.0
    y = 50.8 + (idx // 4) * 101.6
    for pin in range(1, n + 1):
        pin_nets = nodes.get((ref, str(pin)), [])
        for net in pin_nets:
            ly = y - pin_y(n, pin)
            px = x - 5.08
            # Put the label on the free end of the short wire.  This avoids
            # KiCad treating a label placed directly on a library pin as a
            # dangling annotation in the generic-symbol scaffold.
            labels.append(f'''\t(label "{net}" (at {px-2.540:.3f} {ly:.3f} 0)
\t\t(effects (font (size 1.0 1.0)) (justify left bottom)) (uuid "{uid()}"))''')
            wires.append(f'''\t(wire
\t\t(pts (xy {px:.3f} {ly:.3f}) (xy {px-2.540:.3f} {ly:.3f}))
\t\t(stroke (width 0) (type default)) (uuid "{uid()}"))''')
        if not pin_nets:
            # Generic symbols expose the complete package pin count.  Mark
            # package pins that have no PCB net explicitly so ERC does not
            # confuse intentional NCs with missing schematic connections.
            ly = y - pin_y(n, pin)
            no_connects.append(f'''\t(no_connect
\t\t(at {x-5.080:.3f} {ly:.3f})
\t\t(uuid "{uid()}")
\t)''')

insert = "\n".join(labels + wires + no_connects) + "\n"
head, tail = text.rsplit(marker, 1)
text = head + "\n" + insert + "\n)" + tail

# Embed the generic connector definitions used by the normalized scaffold.
# The earlier file referenced external symbols but had an empty lib_symbols
# section, so KiCad's CLI could not see any pins during ERC/netlist export.
lib_path = Path("/usr/share/kicad/symbols/Connector_Generic.kicad_sym")
lib_text = lib_path.read_text()
defs = []
def library_symbol_blocks(source):
    pos = 0
    while True:
        start = source.find("\n\t(symbol ", pos)
        if start < 0:
            return
        start += 1
        depth = 0
        in_string = False
        escaped = False
        for i in range(start, len(source)):
            ch = source[i]
            if in_string:
                if escaped: escaped = False
                elif ch == "\\": escaped = True
                elif ch == '"': in_string = False
                continue
            if ch == '"': in_string = True
            elif ch == '(' : depth += 1
            elif ch == ')' :
                depth -= 1
                if depth == 0:
                    yield start, i + 1, source[start:i + 1]
                    pos = i + 1
                    break

for start, end, block in library_symbol_blocks(lib_text):
    m = re.match(r'\(symbol "Conn_01x(\d+)"', block.lstrip())
    if not m:
        continue
    n = int(m.group(1))
    if n <= 60:
        block = block.replace(f'(symbol "Conn_01x{n:02d}"',
                              f'(symbol "Connector_Generic:Conn_01x{n:02d}"', 1)
        defs.append(block)
if defs and "\t(lib_symbols)" in text:
    text = text.replace("\t(lib_symbols)",
                        "\t(lib_symbols\n" + "\n".join(defs) + "\n\t)", 1)
sch_path.write_text(text)
print(f"Schematic synchronized: {len(ref_order)} parts, {len(labels)} labels, {len(wires)} pin wires")
