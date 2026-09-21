#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
for part in rear front keycap port_cover module_pod; do
    openscad -o "mechanical/handset/exports/$part.stl" -D "part=\"$part\"" mechanical/handset/handset.scad
done
for part in display ball ring screws legends ui; do
    openscad -o "mechanical/handset/exports/visual_$part.stl" -D "part=\"$part\"" mechanical/handset/appearance.scad
done
python scripts/preview_handset.py
python scripts/check_handset_fit.py
