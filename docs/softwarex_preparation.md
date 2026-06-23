# SoftwareX preparation checklist

## Submission framing

Recommended safe framing:

> WaveLab Studio is a Python-based research software prototype for constructing, running, and visualising two-dimensional wave-propagation experiments in heterogeneous scenes. It supports a PINN-oriented workflow and provides tools for scene configuration, scalar wave-field approximation, visual analysis, animation, and result export.

Avoid overclaiming:

- Do not call the current software a validated full-vector Maxwell solver.
- Do not claim that NVIDIA Modulus is the main production solver unless that path is made reproducible and documented.
- Do not report artificial target-copying or exact-finish modes as scientific accuracy.

## Minimum required before public release

- [ ] Decide license and add `LICENSE`.
- [ ] Rename `requirements (1).txt` to `requirements.txt`.
- [ ] Add `README.md`.
- [ ] Add `CITATION.cff`.
- [ ] Add `examples/basic_scene.yaml`.
- [ ] Add one smoke test under `tests/`.
- [ ] Verify that `python solver_simple_torch.py examples/basic_scene.yaml --no_animation --out_dir results/basic_scene` works from a clean checkout.
- [ ] Remove or ignore generated outputs (`*.png`, `*.gif`, `*.npy`, `*.npz`) unless intentionally kept as documentation figures.
- [ ] Remove personal/local paths and unused files.
- [ ] Archive a release with Zenodo or a similar service to obtain a DOI.

## Recommended article title

**WaveLab Studio: A research software tool for two-dimensional wave-propagation experiments in heterogeneous scenes**

Alternative if the PINN motivation should remain visible:

**WaveLab Studio: A Python environment for PINN-oriented electromagnetic wave-propagation experiments in heterogeneous two-dimensional scenes**

## Recommended paper structure

1. **Metadata table**
2. **Motivation and significance**
3. **Software description**
   - architecture
   - scene representation
   - solver workflow
   - visualisation and outputs
4. **Illustrative examples**
5. **Impact**
6. **Limitations and future work**
7. **Conclusions**

## Claims that are safe

- The software provides an interactive GUI for defining 2D heterogeneous wave-propagation scenes.
- The software stores scenes in YAML and exports result images and arrays.
- The solver produces reference/target, predicted/approximated, and error-map fields.
- The software can be used for teaching, prototyping, and exploratory research workflows.
- The architecture can support further development toward PINN-based or Maxwell-equation solvers.

## Claims that require more evidence

- Quantitative superiority over FDTD/FEM.
- Physically validated electromagnetic field prediction.
- Generalisation to arbitrary multi-object environments.
- GPU-accelerated Modulus-based training as the main implemented method.
- Industrial use without additional validation.
