#!/usr/bin/env bash
set -euo pipefail
python solver_simple_torch.py examples/basic_scene.yaml \
  --epochs 100 \
  --nx 96 \
  --ny 64 \
  --steps 8 \
  --no_animation \
  --out_dir results/basic_scene
