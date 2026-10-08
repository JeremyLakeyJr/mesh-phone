#!/usr/bin/env python3
"""Verify target image/configuration and bind evidence to hardware and sources."""
import hashlib,json,os,re,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from cad_sexpr import parse,child,children

def pin_checks(header=None):
 text=(ROOT/'firmware/bringup/main/board.hpp').read_text() if header is None else header
 spec=json.loads((ROOT/'hardware/handset-rev-a/generated/connectivity.json').read_text())
 u1=next(c for c in spec if c['ref']=='U1')
 tree=parse((ROOT/'hardware/handset-rev-a/generated/core.kicad_sch').read_text())
 lib=next(s for s in children(child(tree,'lib_symbols'),'symbol') if 'ESP32-S3-WROOM-1' in s[1])
 names={child(p,'number')[1]:child(p,'name')[1] for s in children(lib,'symbol') for p in children(s,'pin')}
 errors=[]
 for name,pin,net in [('sda','18','I2C_SDA'),('scl','17','I2C_SCL'),('irq','12','KEY_IRQ')]:
  match=re.search(r'\b'+name+r'_gpio\s*=\s*(\d+)',text)
  if not match or names.get(pin)!='IO'+match[1] or u1['nets'].get(pin)!=net:errors.append(name)
 return errors

def verify(out):
 assert not pin_checks(),'Firmware GPIO mapping differs from native schematic'
 config=json.loads((out/'config/sdkconfig.json').read_text())
 expected={'IDF_TARGET':'esp32s3','ESPTOOLPY_FLASHSIZE':'16MB','ESP_CONSOLE_NONE':True,'ESP_CONSOLE_SECONDARY_NONE':True,'FREERTOS_HZ':1000,'BOOTLOADER_LOG_LEVEL':0}
 for key,value in expected.items():assert config.get(key)==value,(key,config.get(key),value)
 assert not config.get('SPIRAM') and not config.get('PM_ENABLE')
 description=json.loads((out/'project_description.json').read_text())
 assert description['git_revision']=='v5.4.2',description['git_revision']
 assert description['target']=='esp32s3'
 image=out/'handset_keypad_bringup.bin';data=image.read_bytes()
 assert data[0]==0xe9 and struct.unpack_from('<H',data,12)[0]==9,'Not an ESP32-S3 image'
 assert data[3]>>4==4,'Image does not specify 16MB flash'
 info=subprocess.run([sys.executable,'-m','esptool','--chip','esp32s3','image_info',str(image)],capture_output=True,text=True,check=True)
 assert 'Validation Hash' in info.stdout and '(valid)' in info.stdout,info.stdout
 (out/'image-info.txt').write_text(info.stdout)
 sources=[p for p in (ROOT/'firmware/bringup').rglob('*') if p.is_file() and p.suffix in ('.cpp','.hpp','.py','.sh','.txt','.defaults') and 'validation' not in p.parts and '__pycache__' not in p.parts]
 sources += [ROOT/'firmware/keypad/controller.hpp',ROOT/'hardware/handset-rev-a/generated/core.kicad_sch',ROOT/'hardware/handset-rev-a/generated/connectivity.json']
 artifacts=['handset_keypad_bringup.bin','handset_keypad_bringup.elf','bootloader/bootloader.bin','partition_table/partition-table.bin','flasher_args.json','sdkconfig']
 packages=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True)
 (ROOT/'firmware/bringup/validation/python-packages.txt').write_text(packages)
 compiler=subprocess.check_output([description['c_compiler'],'--version'],text=True).splitlines()[0]
 report=dict(compiler=compiler,python_version=sys.version.split()[0],passed=True,target='esp32s3',idf_version=description['git_revision'],idf_commit=subprocess.check_output(['git','-C',os.environ['IDF_PATH'],'rev-parse','HEAD'],text=True).strip(),flash_size_mb=16,psram_enabled=False,pin_map={'SDA':10,'SCL':9,'KEY_IRQ':8},source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources)},artifacts={name:dict(bytes=(out/name).stat().st_size,sha256=hashlib.sha256((out/name).read_bytes()).hexdigest()) for name in artifacts},hardware_tested=False,flashed=False,fabrication_released=False)
 (ROOT/'firmware/bringup/validation/build-report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','artifacts')},indent=2))
if __name__=='__main__':verify(Path(sys.argv[1]))
