#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
out="${1:-/tmp/handset-stm32g031}"
mkdir -p "$out"
common=(--target=arm-none-eabi -mcpu=cortex-m0plus -mthumb -ffreestanding -fno-builtin -ffunction-sections -fdata-sections -Os -g)
clang++ "${common[@]}" -std=c++17 -fno-exceptions -fno-rtti -fno-threadsafe-statics -fno-unwind-tables -fno-asynchronous-unwind-tables -Wall -Wextra -Werror -isystem vendor/st -isystem vendor/arm -c main.cpp -o "$out/main.o"
clang "${common[@]}" -c startup.S -o "$out/startup.o"
ld.lld -T linker.ld --gc-sections -Map="$out/supervisor.map" "$out/startup.o" "$out/main.o" -o "$out/supervisor.elf"
llvm-objcopy -O binary "$out/supervisor.elf" "$out/supervisor.bin"
llvm-size "$out/supervisor.elf"
python3 verify_image.py "$out"
