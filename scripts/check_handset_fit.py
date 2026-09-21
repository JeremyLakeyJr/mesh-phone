#!/usr/bin/env python3
"""Assert no solid overlap between printable parts and explicit fit envelopes."""
from pathlib import Path
import subprocess, tempfile, os, json
ROOT=Path(__file__).resolve().parents[1]
results={}
with tempfile.TemporaryDirectory(prefix='mesh-phone-fit-') as tmp:
    for name in ['halves','battery','display','board','keycaps','cover','pod','modem']:
        run=subprocess.run(['openscad','-o',str(Path(tmp)/(name+'.stl')),'-D',f'check="{name}"',
                            str(ROOT/'mechanical/handset/check_fit.scad')],capture_output=True,text=True,
                           env={**os.environ,'QT_QPA_PLATFORM':'offscreen'})
        log=run.stdout+run.stderr
        results[name]=('Current top level object is empty.' in log and 'ERROR:' not in log and 'WARNING:' not in log)
        print(name+(': clear' if results[name] else ': FAILED'),flush=True)
        if not results[name]: print(log,flush=True)
(ROOT/'mechanical/handset/exports/fit-checks.json').write_text(json.dumps(results,indent=2)+'\n')
assert all(results.values()), 'Mechanical collision or failed OpenSCAD evaluation'
