#!/usr/bin/env python3
"""Remove only failed partial routing for the currently disconnected nets."""
import sys
import re

FAILED = {
    "3V3", "MODEM_5V", "LTE_RI", "CAM_D0", "CAM_D1", "CAM_D3",
    "CAM_D4", "CAM_PWDN", "CAM_RESET", "SPI_MOSI", "SPI_SCK",
    "SPI_MISO", "SX1262_BUSY", "CC1101_CS", "CC1101_GDO0", "IR_TX",
    "LCD_DC",
}

src, dst = sys.argv[1:3]
text = open(src, encoding="utf-8").read()
net_ids = {
    int(m.group(1)): m.group(2)
    for m in re.finditer(r'\(net\s+(\d+)\s+"([^"]*)"\)', text)
}
failed_ids = {n for n, name in net_ids.items() if name in FAILED}

def blocks(s):
    starts = [m.start() for m in re.finditer(r'(?m)^\s*\((?:segment|via)\s', s)]
    for start in reversed(starts):
        depth = 0
        quote = False
        escape = False
        end = None
        for i in range(start, len(s)):
            c = s[i]
            if quote:
                if escape:
                    escape = False
                elif c == "\\":
                    escape = True
                elif c == '"':
                    quote = False
            elif c == '"':
                quote = True
            elif c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        yield start, end, s[start:end]

removed = 0
for start, end, block in blocks(text):
    m = re.search(r'\(net\s+"([^"]+)"\)', block)
    old = re.search(r'\(net\s+(\d+)\)', block)
    is_failed = (m and m.group(1) in FAILED) or (old and int(old.group(1)) in failed_ids)
    if is_failed:
        text = text[:start] + text[end:]
        removed += 1
open(dst, "w", encoding="utf-8").write(text)
print(f"removed {removed} failed-net tracks/vias; wrote {dst}")
