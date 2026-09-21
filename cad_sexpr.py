"""Small lossless-atom S-expression utility for KiCad revision tooling."""
import json
import re

class Q(str):
    pass

def parse(text):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    stack = []
    root = None
    for token in tokens:
        if token == '(':
            node = []
            if stack:
                stack[-1].append(node)
            else:
                root = node
            stack.append(node)
        elif token == ')':
            stack.pop()
        else:
            stack[-1].append(Q(json.loads(token, strict=False)) if token.startswith('"') else token)
    if stack:
        raise ValueError('Unbalanced S-expression')
    return root

def dump(node, level=0):
    if isinstance(node, Q):
        return json.dumps(str(node), ensure_ascii=False)
    if not isinstance(node, list):
        return str(node)
    if not any(isinstance(n, list) for n in node):
        return '(' + ' '.join(dump(n) for n in node) + ')'
    return '(' + ''.join(('\n' + '  ' * (level + 1) if isinstance(n, list) else (' ' if i else '')) + dump(n, level + 1) for i, n in enumerate(node)) + ')'

def children(node, key):
    return [n for n in node if isinstance(n, list) and n and n[0] == key]

def child(node, key):
    return next(iter(children(node, key)), None)

def prop(node, name):
    return next((n for n in children(node, 'property') if n[1] == name), None)
