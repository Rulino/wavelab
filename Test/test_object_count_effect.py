#!/usr/bin/env python3
# test_object_count_effect.py
#
# Testy pre 2, 4 a 6 objektov.
# Vytvorí tri scény, spustí solver a uloží výsledky do:
#   object_count_test_results/objects_2
#   object_count_test_results/objects_4
#   object_count_test_results/objects_6
#
# Spustenie:
#   python test_object_count_effect.py

import sys
import subprocess
from pathlib import Path

try:
    import yaml
    import numpy as np
except Exception:
    print("Install: pip install pyyaml numpy")
    raise

ROOT = Path(__file__).resolve().parent
SOLVER = ROOT / "solver_simple_torch.py"
OUT = ROOT / "object_count_test_results"

MATERIALS = {
    "vzduch": {"c": 3.0e8, "absorption": 0.03, "T": 1.00, "R": 0.00, "scatter": 0.00},
    "kov": {"c": 2.5e8, "absorption": 0.10, "T": 0.03, "R": 0.90, "scatter": 1.00, "barrier": True},
    "betón": {"c": 2.0e8, "absorption": 0.08, "T": 0.18, "R": 0.60, "scatter": 0.55, "barrier": True},
    "sklo": {"c": 2.2e8, "absorption": 0.05, "T": 0.65, "R": 0.15, "scatter": 0.25},
    "plast": {"c": 2.4e8, "absorption": 0.05, "T": 0.82, "R": 0.10, "scatter": 0.18},
    "voda": {"c": 1.5e8, "absorption": 0.06, "T": 0.85, "R": 0.10, "scatter": 0.25},
}

ALL_OBJECTS = [
    {"x": 0.75, "y": 0.55, "material": "kov", "shape": "triangle", "r": 0.10, "width": 0.20, "height": 0.20, "angle": 0},
    {"x": 1.20, "y": 1.25, "material": "betón", "shape": "rectangle", "r": 0.09, "width": 0.18, "height": 0.18, "angle": 0},
    {"x": 1.75, "y": 0.85, "material": "sklo", "shape": "circle", "r": 0.10, "width": 0.20, "height": 0.20, "angle": 0},
    {"x": 2.30, "y": 1.55, "material": "plast", "shape": "triangle", "r": 0.09, "width": 0.18, "height": 0.20, "angle": 0},
    {"x": 2.65, "y": 0.35, "material": "voda", "shape": "circle", "r": 0.10, "width": 0.20, "height": 0.20, "angle": 0},
    {"x": 0.45, "y": 1.55, "material": "betón", "shape": "square", "r": 0.08, "width": 0.16, "height": 0.16, "angle": 25},
]

def make_scene(count: int) -> dict:
    return {
        "materials": MATERIALS,
        "scéna": {
            "world": {"xmin": 0.0, "xmax": 3.0, "ymin": 0.0, "ymax": 2.0},
            "zdroj": {
                "x0": 0.25,
                "y0": 1.25,
                "frequency_hz": 1.0e9,
                "amplitude": 1.0,
                "radius": 0.08,
            },
            "objekty": ALL_OBJECTS[:count],
        },
    }

def write_scene(path: Path, count: int) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(make_scene(count), f, sort_keys=False, allow_unicode=True)

def run_case(count: int) -> dict:
    case_dir = OUT / f"objects_{count}"
    case_dir.mkdir(parents=True, exist_ok=True)

    scene_path = OUT / f"scene_objects_{count}.yaml"
    write_scene(scene_path, count)

    cmd = [
        sys.executable,
        str(SOLVER),
        str(scene_path),
        "--epochs", "2000",
        "--true_epochs", "20000",
        "--nx", "420",
        "--ny", "280",
        "--no_animation",
        "--out_dir", str(case_dir),
    ]

    print(f"\n=== Test: {count} objekty ===")
    result = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)

    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(f"Solver failed for {count} objects")

    metrics = {}
    metrics_path = case_dir / "metrics.txt"
    if metrics_path.exists():
        for line in metrics_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                metrics[k.strip()] = v.strip()

    u_pred = np.load(case_dir / "U_pred.npy")
    u_true = np.load(case_dir / "U_true.npy")
    diff = np.abs(u_true - u_pred)

    return {
        "objects": count,
        "mean_abs_error": float(diff.mean()),
        "max_abs_error": float(diff.max()),
        "pred_energy": float(np.mean(np.abs(u_pred))),
        "true_energy": float(np.mean(np.abs(u_true))),
        "accuracy_percent": float(metrics.get("accuracy_percent", 0.0)),
        "folder": str(case_dir),
    }

def main():
    OUT.mkdir(parents=True, exist_ok=True)

    results = []
    for count in (2, 4, 6):
        results.append(run_case(count))

    report_path = OUT / "object_count_test_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("Test objektov: 2 / 4 / 6\n")
        f.write("=" * 42 + "\n\n")
        for r in results:
            f.write(f"Objekty: {r['objects']}\n")
            f.write(f"Presnosť: {r['accuracy_percent']:.6f}%\n")
            f.write(f"Priemerná absolútna chyba: {r['mean_abs_error']:.8f}\n")
            f.write(f"Maximálna absolútna chyba: {r['max_abs_error']:.8f}\n")
            f.write(f"Energia predikcie: {r['pred_energy']:.8f}\n")
            f.write(f"Energia referencie: {r['true_energy']:.8f}\n")
            f.write(f"Priečinok: {r['folder']}\n\n")

    print("\nHotovo.")
    print("Report:", report_path)
    for r in results:
        print(f"{r['objects']} objekty -> {r['folder']}")

if __name__ == "__main__":
    main()
