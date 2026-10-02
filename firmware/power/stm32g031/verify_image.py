#!/usr/bin/env python3
"""Validate the actual linked ARM image, vector table and memory limits."""
import hashlib,json,struct,subprocess,sys
from pathlib import Path
out=Path(sys.argv[1]);elf=(out/'supervisor.elf').read_bytes();binary=(out/'supervisor.bin').read_bytes()
assert elf[:7]==b'\x7fELF\x01\x01\x01','Expected little-endian ELF32'
h=struct.unpack_from('<HHIIIIIHHHHHH',elf,16)
kind,machine,version,entry,phoff,shoff,flags,ehsize,phsize,phnum,shsize,shnum,shstr=h
assert kind==2 and machine==40 and version==1,'Expected ARM executable'
assert flags&0xff000000==0x05000000,'Expected EABI5'
assert not flags&0x400,'Hard-float ABI is incompatible with Cortex-M0+'
assert 0<len(binary)<=60*1024,'Application crossed reserved journal pages'
regions=[]
for i in range(phnum):
    typ,offset,vaddr,paddr,filesz,memsz,perms,align=struct.unpack_from('<IIIIIIII',elf,phoff+i*phsize)
    if typ!=1:continue
    if 0x08000000<=vaddr<0x0800f000:assert vaddr+memsz<=0x0800f000
    elif 0x20000000<=vaddr<0x20002000:assert vaddr+memsz<=0x20001c00
    else:raise AssertionError(('Unexpected load region',hex(vaddr)))
    if filesz:assert 0x08000000<=paddr and paddr+filesz<=0x0800f000
    regions.append(dict(address=hex(vaddr),file_bytes=filesz,memory_bytes=memsz))
symbols={}
for line in subprocess.check_output(['llvm-nm','--defined-only',str(out/'supervisor.elf')],text=True).splitlines():
    fields=line.split()
    if len(fields)==3:symbols[fields[2]]=int(fields[0],16)
assert not subprocess.check_output(['llvm-nm','--undefined-only',str(out/'supervisor.elf')],text=True).strip()
vectors=struct.unpack_from('<48I',binary)
assert vectors[0]==0x20002000
assert vectors[1]==symbols['Reset_Handler']|1 and entry==vectors[1]
assert vectors[15]==symbols['SysTick_Handler']|1
for i,address in enumerate(vectors[1:],1):
    if address:assert address&1 and 0x08000000<=address<0x08000000+len(binary),(i,hex(address))
assert symbols['_ebss']<=symbols['_stack_limit'] and symbols['_stack_top']-symbols['_stack_limit']==1024
report=dict(passed=True,target='STM32G031G8U6 / Cortex-M0+',binary_bytes=len(binary),static_ram_bytes=symbols['_ebss']-0x20000000,reserved_stack_bytes=1024,reserved_flash_bytes=4096,load_regions=regions,sha256=hashlib.sha256(binary).hexdigest(),charging_enabled=False,hardware_tested=False)
(out/'build-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
