#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${IDF_PATH:?Source ESP-IDF v5.4.2 export.sh first}"
expected=f5c3654a1c2d2a01f7f67def7a0dc48e691f63c0
actual=$(git -C "$IDF_PATH" rev-parse HEAD)
if [[ "$actual" != "$expected" ]]; then
  echo "Expected ESP-IDF v5.4.2 commit $expected; found $actual" >&2
  exit 1
fi
out="${1:-/tmp/handset-esp32-bringup}"
mkdir -p "$out"
out=$(cd "$out" && pwd)
idf.py -B "$out" -D "SDKCONFIG=$out/sdkconfig" build
python3 verify_build.py "$out"
