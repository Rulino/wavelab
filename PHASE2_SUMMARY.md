# WaveLab Studio publication pack: phase 2 summary

This package contains drop-in files that can be copied into the repository before public release and SoftwareX submission.

## Included files

- `README.md` — publication-oriented repository readme.
- `requirements.txt` — renamed and extended dependency list with `pytest`.
- `.gitignore` — ignores Python caches, environments, and generated outputs.
- `LICENSE_MIT_TEMPLATE.txt` — permissive license template; confirm before use.
- `CITATION.cff` — draft citation metadata; update repository URL, DOI, ORCID, and release date.
- `examples/basic_scene.yaml` — small reproducible solver scene using the currently working Slovak-key schema.
- `tests/test_smoke_solver.py` — minimal solver smoke test.
- `docs/usage.md` — usage guide.
- `docs/repository_structure.md` — recommended repository clean-up.
- `docs/softwarex_preparation.md` — checklist and safe publication framing.
- `docs/softwarex_article_draft.md` — first draft of the SoftwareX manuscript text.
- `scripts/run_basic_example.sh` — command-line example runner.

## How to apply

1. Copy these files into the repository root.
2. Rename `requirements (1).txt` to `requirements.txt`, or replace it with the included one.
3. Rename `Test/` to `experiments/` unless the scripts are converted to deterministic tests.
4. Remove or ignore generated artefacts such as PNG/GIF/NPY/NPZ files.
5. Run the smoke test:

```bash
pip install -r requirements.txt
python -m pytest tests/test_smoke_solver.py
```

6. Run the example:

```bash
bash scripts/run_basic_example.sh
```

## Main recommendation

Use the SoftwareX article to present WaveLab Studio as a documented research software prototype for 2D wave-propagation experiments and visualisation. Avoid describing the current version as a validated full Maxwell/PINN solver unless the backend is further developed and benchmarked.
