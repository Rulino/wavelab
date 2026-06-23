# Recommended repository structure

The current project can be submitted to SoftwareX after a light clean-up. A full architectural refactor is not necessary before the first submission, but the public repository should be made understandable and reproducible.

## Recommended minimal structure

```text
wavelab-studio/
├── README.md
├── LICENSE
├── CITATION.cff
├── requirements.txt
├── .gitignore
├── gui_scene_builder.py
├── scene_cli.py
├── solver_simple_torch.py
├── solver_modulus.py
├── wave_video_renderer.py
├── streamlit_app.py
├── examples/
│   └── basic_scene.yaml
├── docs/
│   ├── usage.md
│   ├── repository_structure.md
│   └── softwarex_preparation.md
├── tests/
│   └── test_smoke_solver.py
└── experiments/
    ├── generate_demo_results.py
    ├── test_amplitude_effect.py
    └── test_object_count_effect.py
```

## Files to rename or move

| Current item | Recommended action |
|---|---|
| `requirements (1).txt` | rename to `requirements.txt` |
| `Test/` | rename to `experiments/` unless files are converted to deterministic tests |
| `sc#U00e9na.yaml` | replace with `examples/basic_scene.yaml`; avoid encoded filename in public repo |
| `scene.yaml` | either convert to the solver schema or move to `examples/english_scene_unvalidated.yaml` |
| `delete.py` | remove unless it has a documented purpose |
| `material/1`, `material/display_material/1` | remove empty/placeholder files |
| generated PNG/GIF/NPY/NPZ outputs | do not commit, or keep only small illustrative examples in `docs/figures/` |

## Longer-term refactor

For a later version, the software would benefit from a package layout:

```text
src/wavelab_studio/
├── gui/
├── solver/
├── scene/
├── visualization/
└── cli/
```

This is not strictly necessary for SoftwareX if the current scripts are documented and reproducible, but it would improve maintainability.
