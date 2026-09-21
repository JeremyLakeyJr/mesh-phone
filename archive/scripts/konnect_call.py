#!/usr/bin/env python3
"""Call local Konnect tools, including dynamically loaded toolsets."""
import json
import subprocess
import sys

binary = '/home/lakey/.local/share/kicad/10.0/3rdparty/plugins/com.github.mixelpixx.konnect/bin/konnect'
p = subprocess.Popen([binary, '--client', 'codex'], stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
sequence = 0

def request(method, params):
    global sequence
    sequence += 1
    p.stdin.write(json.dumps(dict(jsonrpc='2.0', id=sequence, method=method, params=params)) + '\n')
    p.stdin.flush()
    for line in p.stdout:
        response = json.loads(line)
        if response.get('id') == sequence:
            if 'error' in response:
                raise RuntimeError(response['error'])
            return response['result']
    raise RuntimeError('Konnect exited without response')

try:
    request('initialize', dict(protocolVersion='2025-03-26', capabilities={},
                               clientInfo=dict(name='codex', version='1')))
    p.stdin.write(json.dumps(dict(jsonrpc='2.0', method='notifications/initialized')) + '\n')
    p.stdin.flush()
    request('tools/call', dict(name='load_toolset', arguments=dict(name=sys.argv[1].split(','))))
    if sys.argv[2] == 'describe':
        result = request('tools/list', {})
        wanted = sys.argv[3:]
        print(json.dumps([t for t in result['tools'] if t['name'] in wanted], indent=2))
    else:
        print(json.dumps(request('tools/call', dict(name=sys.argv[2], arguments=json.loads(sys.argv[3]))), indent=2))
finally:
    p.terminate()
