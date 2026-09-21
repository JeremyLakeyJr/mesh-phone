import json, os, selectors, subprocess, sys, time

dsn = sys.argv[1]
ses = sys.argv[2]
env = os.environ.copy()
env.pop('DISPLAY', None)
env['JAVA_TOOL_OPTIONS'] = '-Djava.awt.headless=true -Duser.home=/tmp/freerouting-home'

p = subprocess.Popen([
    '/home/lakey/.local/share/kicad/10.0/3rdparty/plugins/com.github.mixelpixx.konnect/bin/konnect',
    '--client', 'codex'
], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
   text=True, bufsize=1)

def send(obj):
    p.stdin.write(json.dumps(obj) + '\n')
    p.stdin.flush()

send({'jsonrpc':'2.0','id':1,'method':'initialize','params':{
    'protocolVersion':'2025-03-26','capabilities':{},
    'clientInfo':{'name':'codex','version':'1'}}})
send({'jsonrpc':'2.0','method':'notifications/initialized','params':{}})

sel = selectors.DefaultSelector()
sel.register(p.stdout, selectors.EVENT_READ, 'out')
sel.register(p.stderr, selectors.EVENT_READ, 'err')

def wait_id(wanted, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        events = sel.select(min(1, max(0, end-time.time())))
        for key, _ in events:
            line = key.fileobj.readline()
            if not line:
                continue
            stream = key.data
            print(('STDERR ' if stream == 'err' else '') + line, end='', flush=True)
            if stream == 'out':
                try:
                    obj = json.loads(line)
                    if obj.get('id') == wanted:
                        return obj
                except Exception:
                    pass
    raise TimeoutError(f'timeout waiting for {wanted}')

wait_id(1, 30)
send({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{
    'name':'load_toolset','arguments':{'name':'integration'}}})
wait_id(2, 60)
send({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{
    'name':'route_specctra_dsn','arguments':{
        'dsn_path':dsn,
        'jar_path':'/tmp/freerouting/freerouting-2.4.1.jar',
        'ses_output_path':ses,
        'max_passes':13,
        'optimizer_enabled':False,
        'overall_timeout_seconds':900
    }}})
result = wait_id(3, 960)
print(json.dumps(result, indent=2), flush=True)
p.terminate()
