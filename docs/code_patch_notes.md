# Code patch notes for SoftwareX preparation

This patch keeps the original prototype architecture intact and focuses on publication-readiness without a risky GUI refactor.

## Implemented fixes

1. **Scene schema compatibility**
   - `solver_simple_torch.py` now accepts both:
     - legacy Slovak schema: `scéna / zdroj / objekty`, and
     - publication-facing English schema: `scene / source / objects`.
   - `scene_cli.py` now also accepts both schemas.

2. **Material-name compatibility**
   - English material names in examples (`air`, `metal`, `concrete`, `glass`, etc.) are mapped to the internal Slovak names used by the legacy solver (`vzduch`, `kov`, `betón`, `sklo`, etc.).
   - This prevents example YAML files from silently using fallback material parameters.

3. **Shape-name compatibility**
   - The solver now accepts both English shapes (`circle`, `square`, `rectangle`, `triangle`) and legacy Slovak shapes (`kruh`, `štvorec`, `obdĺžnik`, `trojuholník`).
   - `scene_cli.py` allows both naming styles and normalizes them.

4. **CLI usability**
   - `scene_cli.py` now accepts `--scene` as an alias for `--scéna`.

5. **Diagnostic accuracy modes warning**
   - `solver_simple_torch.py` now prints a warning when `--perfect_accuracy` or `--exact_finish` is used.
   - These modes are retained for backward compatibility, but explicitly labelled as diagnostic/demo modes not suitable for scientific benchmark claims.

6. **Numerical warning cleanup**
   - The internal sigmoid helper now clips extreme inputs before applying `exp`, avoiding harmless overflow warnings during small smoke runs.

7. **Publication files added**
   - `README.md`, `requirements.txt`, `.gitignore`, `CITATION.cff`, `LICENSE`, `docs/`, `examples/`, `tests/`, and `scripts/` were added from the publication pack.

## Not changed yet

- The large GUI file `gui_scene_builder.py` was not split into smaller modules. This would be a larger refactor and should only be done after preserving a working baseline.
- The solver was not rewritten into a full Maxwell or Modulus PINN solver. The manuscript should still describe the current implementation as a 2D wave-propagation research software prototype.
- Experimental scripts in `Test/` were not deleted. For a clean public repository, consider moving them to `experiments/legacy/` or excluding them from the release.
