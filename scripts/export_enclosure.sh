#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"
python scripts/enclosure_geometry.py
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
model=mechanical/enclosure/enclosure.scad
output=mechanical/enclosure/exports
mkdir -p "$output"
for part in rear front port_cover module_pod; do
    openscad -o "$output/$part.stl" -D "part=\"$part\"" "$model"
done
python scripts/preview_enclosure.py
