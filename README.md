# WaveLab Studio

WaveLab Studio is a Python-based research software prototype for building, running, and visualising two-dimensional electromagnetic/wave-propagation scenarios in heterogeneous scenes with multiple material objects. The project provides a graphical scene editor, command-line scene tools, a lightweight wave-field solver, result visualisation, and animation utilities.

The software was developed as an experimental tool for exploring AI/PINN-oriented workflows for electromagnetic signal propagation. The current public version should be described as a **2D scalar wave-field approximation and visualisation environment**, not as a production-grade full-vector Maxwell solver.

## Main features

- interactive Tkinter GUI for scene construction and visual inspection;
- YAML-based scene configuration with configurable materials and objects;
- support for circular, rectangular, and triangular scene objects;
- lightweight PyTorch/NumPy solver for wave-field approximation;
- generation of predicted field, reference/target field, and error-map images;
- optional GIF animation rendering for wave propagation;
- command-line scene editing and solver execution;
- export of numerical arrays and basic metrics.

## Repository layout

A recommended publication-ready layout is:

```text
wavelab-studio/
├── README.md
├── LICENSE
├── CITATION.cff
├── requirements.txt
├── gui_scene_builder.py
├── scene_cli.py
├── solver_simple_torch.py
├── solver_modulus.py
├── wave_video_renderer.py
├── streamlit_app.py
├── examples/
│   └── basic_scene.yaml
├── tests/
│   └── test_smoke_solver.py
└── docs/
    ├── usage.md
    ├── repository_structure.md
    └── softwarex_preparation.md
```

The existing experimental scripts may be kept under `experiments/` or `notebooks/`, but they should not be presented as formal tests unless they are reproducible and deterministic.

## Installation

Create a virtual environment and install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

For CPU-only use, the standard PyTorch installation is sufficient. For GPU execution, install the PyTorch build that matches the local CUDA version.

## Quick start

Run a small example simulation:

```bash
python solver_simple_torch.py examples/basic_scene.yaml \
  --epochs 100 \
  --nx 96 \
  --ny 64 \
  --steps 8 \
  --no_animation \
  --out_dir results/basic_scene
```

Expected output files include:

```text
results/basic_scene/field_true.png
results/basic_scene/field_pred.png
results/basic_scene/field_err.png
results/basic_scene/U_true.npy
results/basic_scene/U_pred.npy
results/basic_scene/U_err.npy
results/basic_scene/metrics.txt
```

## GUI

Launch the desktop GUI:

```bash
python gui_scene_builder.py
```

The GUI allows the user to define a scene, add or move material objects, run the solver, inspect result images, generate animations, and save generated outputs.

## Command-line scene editor

The command-line editor currently uses the Slovak scene schema used by the solver, for example keys such as `scéna`, `zdroj`, and `objekty`.

```bash
python scene_cli.py --scéna examples/basic_scene.yaml list
python scene_cli.py --scéna examples/basic_scene.yaml materials
```

## Minimal test

After installing the dependencies, run:

```bash
python -m pytest tests/test_smoke_solver.py
```

The smoke test runs a low-resolution solver configuration and checks that the expected result files are created.

## Scientific scope and limitations

This software is intended as a research prototype for fast scenario construction, visualisation, and exploratory wave-field experiments. The current solver is a simplified scalar-field approximation with material attenuation, transmission, reflection, shadowing/occlusion, and smoothing heuristics. It should not be advertised as a validated full-vector Maxwell solver.

When using this software in publications, avoid reporting results obtained with artificial accuracy modes such as `--perfect_accuracy`, `--exact_finish`, or target-copying modes as independent scientific validation. These modes can be useful for debugging and demonstrations, but they are not suitable for quantitative claims about model accuracy.

## Citation

If you use this software, please cite the associated SoftwareX article and the archived software release DOI. A draft `CITATION.cff` file is included in this publication pack and should be updated after the repository is published and archived.

## License

Choose and include an open-source license before submission. MIT or BSD-3-Clause are simple permissive options. GPL-3.0 is suitable if derivative work should remain open-source.
