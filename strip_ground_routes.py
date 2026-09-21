#!/usr/bin/env python3
import re, sys

path = sys.argv[1]
text = open(path).read()

def blocks(src):
    out = []
    for m in re.finditer(r'(?m)^\s*\((segment|via)\s*$', src):
        start = m.start()
        depth = 0
        pos = start
        while pos < len(src):
            if src[pos] == '(':
                depth += 1
            elif src[pos] == ')':
                depth -= 1
                if depth == 0:
                    out.append((start, pos + 1, src[start:pos + 1]))
                    break
            pos += 1
    return out

remove = []
for start, end, block in blocks(text):
    if '(net "GND")' in block:
        remove.append((start, end))
for start, end in reversed(remove):
    text = text[:start] + text[end:]
open(path, 'w').write(text)
print(f'removed {len(remove)} GND route items')
