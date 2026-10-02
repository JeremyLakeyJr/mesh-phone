#!/usr/bin/env python3
"""Negative tests for the release-image structural checker, using temporary copies."""
import shutil,struct,subprocess,sys,tempfile
from pathlib import Path
base=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/tmp/handset-stm32g031')
for case in ('wrong_cpu','non_thumb_reset','flash_overflow','invalid_stack'):
    with tempfile.TemporaryDirectory(prefix='supervisor-image-test-') as temp:
        out=Path(temp)
        for name in ('supervisor.elf','supervisor.bin'):shutil.copy2(source/name,out/name)
        target=out/('supervisor.elf' if case=='wrong_cpu' else 'supervisor.bin')
        data=bytearray(target.read_bytes())
        if case=='wrong_cpu':struct.pack_into('<H',data,18,3)
        elif case=='non_thumb_reset':struct.pack_into('<I',data,4,struct.unpack_from('<I',data,4)[0]&~1)
        elif case=='flash_overflow':data.extend(b'\xff'*(60*1024+1-len(data)))
        else:struct.pack_into('<I',data,0,0x20004000)
        target.write_bytes(data)
        result=subprocess.run(['python3',str(base/'verify_image.py'),str(out)],capture_output=True,text=True)
        assert result.returncode!=0 and 'AssertionError' in result.stderr,case
        print('Rejected:',case)
