#!/usr/bin/env python3
"""Build/run host keypad tests and record source-bound evidence."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='keypad-test-') as directory:
 binary=str(Path(directory)/'test')
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-pedantic','-fsanitize=undefined',str(ROOT/'firmware/keypad/tests/controller_test.cpp'),'-o',binary],check=True)
 result=subprocess.run([binary],check=True,capture_output=True,text=True)
 print(result.stdout,end='')
 report=dict(passed=True,scope='Host fake-bus tests only; no ESP32 target build or hardware execution',result=result.stdout.strip(),source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'firmware/keypad/controller.hpp',ROOT/'firmware/keypad/tests/controller_test.cpp']},fabrication_released=False)
 (ROOT/'firmware/keypad/test-report.json').write_text(json.dumps(report,indent=2)+'\n')
