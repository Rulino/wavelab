# Usage guide

## 1. Running the desktop application

```bash
python gui_scene_builder.py
```

The graphical interface is intended for interactive scene creation and demonstration. It allows users to define the signal source, add material objects, preview the scene, run the solver, inspect generated images, and save selected results.

## 2. Running the solver directly

```bash
python solver_simple_torch.py examples/basic_scene.yaml \
  --epochs 100 \
  --nx 96 \
  --ny 64 \
  --steps 8 \
  --no_animation \
  --out_dir results/basic_scene
```

Recommended options for reproducible documentation examples:

- `--no_animation`: disables GIF generation and makes the example faster;
- `--out_dir`: writes results to a known directory;
- `--nx`, `--ny`: define the simulation grid resolution;
- `--steps`: controls the internal propagation/smoothing iterations;
- `--epochs`: controls the displayed prediction quality level.

## 3. Generated outputs

The solver writes the following core outputs:

| File | Meaning |
|---|---|
| `field_true.png` | reference/target field visualisation |
| `field_pred.png` | predicted/approximated field visualisation |
| `field_err.png` | absolute error map visualisation |
| `U_true.npy` | reference/target field array |
| `U_pred.npy` | predicted/approximated field array |
| `U_err.npy` | absolute error array |
| `metrics.txt` | scalar metrics and solver settings |
| `wave_animation.gif` | optional animation if enabled |

## 4. Scene schema

The currently working solver schema uses Slovak keys:

```yaml
materials:
  air:
    absorption: 0.05
    R: 0.0
    T: 1.0
    scatter: 0.0
scene:
  source:
    x0: 0.65
    y0: 1.45
    amplitude: 2.0
    frequency_hz: 1000000000.0
    radius: 0.12
  objects:
    - x: 0.7
      y: 0.6
      material: concrete
      shape: circle
      r: 0.10
      width: 0.20
      height: 0.20
      angle: 0.0
```

For publication, either keep this schema and document it clearly, or implement a converter that accepts both English and Slovak keys.

## 5. Command-line scene editing

```bash
python scene_cli.py --scene examples/basic_scene.yaml list
python scene_cli.py --scene examples/basic_scene.yaml materials
```

The CLI currently expects the same Slovak-key YAML schema as the solver.

## 6. Accuracy modes warning

The solver contains several demonstration/debugging options that can force the predicted field closer to the target field. These include `--perfect_accuracy`, `--exact_finish`, and `--train_to_target`. Do not use these modes for independent model validation in the SoftwareX article. They should be described as debugging or demonstration utilities only.
