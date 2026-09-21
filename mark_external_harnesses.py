#!/usr/bin/env python3
"""Mark J11/J12 as schematic-only external harness interfaces."""
import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else 'owasso1.kicad_sch'
text = open(path, encoding='utf-8').read()
changed = []
for ref in ('J11', 'J12'):
    marker = f'\t\t(property "Reference" "{ref}"'
    pos = text.find(marker)
    if pos < 0:
        raise SystemExit(f'{ref} not found')
    start = text.rfind('\n\t(symbol', 0, pos)
    end = text.find('\n\t(symbol', pos)
    if end < 0:
        end = text.find('\n\t)', pos)
    if start < 0 or end < 0:
        raise SystemExit(f'could not isolate {ref} symbol block')
    block = text[start:end]
    old = '(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)'
    new = '(exclude_from_sim no) (in_bom no) (on_board no) (dnp no)'
    if old not in block:
        raise SystemExit(f'{ref} instance flags not found')
    block = block.replace(old, new, 1)
    text = text[:start] + block + text[end:]
    changed.append(ref)
open(path, 'w', encoding='utf-8').write(text)
print('marked external harnesses off-board:', ', '.join(changed))
