#!/usr/bin/env python3
import sys

src, dst = sys.argv[1:3]
s = open(src, encoding="utf-8").read()
starts = []
pos = 0
while True:
    i = s.find("\n\t(zone", pos)
    if i < 0:
        break
    starts.append(i + 1)
    pos = i + 1
for start in reversed(starts):
    depth = 0
    quote = False
    escape = False
    for i in range(start, len(s)):
        c = s[i]
        if quote:
            if escape: escape = False
            elif c == "\\": escape = True
            elif c == '"': quote = False
        elif c == '"': quote = True
        elif c == '(' : depth += 1
        elif c == ')' :
            depth -= 1
            if depth == 0:
                s = s[:start] + s[i+1:]
                break
open(dst, "w", encoding="utf-8").write(s)
print(f"removed {len(starts)} copper zones")
