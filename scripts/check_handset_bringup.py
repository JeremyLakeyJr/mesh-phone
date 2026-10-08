#!/usr/bin/env python3
"""Host regression tests plus native-schematic GPIO contract."""
import hashlib,importlib.util,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bringup_verify',ROOT/'firmware/bringup/verify_build.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert not module.pin_checks()
header=(ROOT/'firmware/bringup/main/board.hpp').read_text()
assert module.pin_checks(header.replace('irq_gpio = 8','irq_gpio = 18'))==['irq']
assert module.pin_checks(header.replace('sda_gpio = 10','sda_gpio = 9'))==['sda']
with tempfile.TemporaryDirectory(prefix='bringup-tests-') as directory:
 binary=str(Path(directory)/'session')
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-pedantic','-fsanitize=undefined','-I',str(ROOT/'firmware'),str(ROOT/'firmware/bringup/tests/session_test.cpp'),'-o',binary],check=True)
 result=subprocess.run([binary],capture_output=True,text=True,check=True)
 print(result.stdout.strip());print('Native GPIO mapping and two negative controls passed')
 files=['firmware/bringup/main/board.hpp','firmware/bringup/main/session.hpp','firmware/bringup/tests/session_test.cpp','firmware/keypad/controller.hpp']
 report=dict(passed=True,session_tests=12,pin_contract_checks=3,source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files},hardware_tested=False)
 (ROOT/'firmware/bringup/validation/host-tests.json').write_text(json.dumps(report,indent=2)+'\n')
