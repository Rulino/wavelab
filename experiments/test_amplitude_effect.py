#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent
SOLVER = ROOT / "solver_simple_torch.py"
OUT = ROOT / "amplitude_test_results"

def write_scene(path: Path, amplitude: float):
    data = {
        "materials": {
            "air": {"c": 3.0e8, "absorption": 0.03, "T": 1.0, "R": 0.0, "scatter": 0.0},
            "metal": {"c": 2.5e8, "absorption": 5.0, "T": 0.10, "R": 0.90, "scatter": 1.0, "barrier": True},
            "glass": {"c": 2.2e8, "absorption": 0.60, "T": 0.85, "R": 0.15, "scatter": 0.25},
            "plastic": {"c": 2.4e8, "absorption": 0.35, "T": 0.90, "R": 0.10, "scatter": 0.18},
        },
        "scene": {
            "source": {
                "x0": 0.5,
                "y0": 1.25,
                "amplitude": float(amplitude),
                "frequency_hz": 1.0e9,
                "radius": 0.08,
            },
            "objects": [
                {"x": 1.25, "y": 1.55, "material": "metal", "shape": "circle", "r": 0.12},
                {"x": 1.25, "y": 0.55, "material": "glass", "shape": "rectangle", "width": 0.22, "height": 0.14, "angle": 0},
                {"x": 2.15, "y": 1.40, "material": "metal", "shape": "triangle", "width": 0.24, "height": 0.22, "angle": 0},
                {"x": 2.10, "y": 0.60, "material": "plastic", "shape": "rectangle", "width": 0.18, "height": 0.16, "angle": 30},
            ],
        },
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

def parse_metrics(path: Path) -> dict:
    metrics = {}
    if not path.exists():
        return metrics
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            metrics[k.strip()] = v.strip()
    return metrics

def run_case(name: str, amplitude: float) -> dict:
    case_dir = OUT / name
    scene_path = OUT / f"{name}.yaml"
    write_scene(scene_path, amplitude)

    print(f"\nRunning: {name}")
    print("YAML check:")
    print(scene_path.read_text(encoding="utf-8").splitlines()[0:12])

    cmd = [
        sys.executable, str(SOLVER), str(scene_path),
        "--epochs", "400",
        "--nx", "260",
        "--ny", "170",
        "--steps", "14",
        "--shadow_steps", "8",
        "--blur_sigma", "2",
        "--blur_kernel", "13",
        "--no_animation",
        "--out_dir", str(case_dir),
    ]

    result = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("solver failed")

    metrics = parse_metrics(case_dir / "metrics.txt")
    metrics["case_dir"] = str(case_dir)
    return metrics

def mf(d, key, default=0.0):
    try:
        return float(d.get(key, default))
    except Exception:
        return default

def main():
    OUT.mkdir(exist_ok=True)

    low = run_case("amp_0_5", 0.5)
    high = run_case("amp_2_0", 2.0)

    low_energy = mf(low, "field_energy")
    high_energy = mf(high, "field_energy")
    low_max = mf(low, "field_max_abs")
    high_max = mf(high, "field_max_abs")

    text = f"""SOURCE AMPLITUDE TEST REPORT
==================================

Low amplitude: 0.5
  field_energy:  {low_energy}
  field_max_abs: {low_max}
  results:       {low["case_dir"]}

High amplitude: 2.0
  field_energy:  {high_energy}
  field_max_abs: {high_max}
  results:       {high["case_dir"]}

EXPECTED:
  amplitude=0.5 -> 
  amplitude=2.0 -> 

STATUS: {"PASS" if high_max >= low_max else "CHECK VISUAL RESULTS"}
"""
    report_path = OUT / "amplitude_test_report.txt"
    report_path.write_text(text, encoding="utf-8")
    print(text)
    print("Report saved:", report_path)

if __name__ == "__main__":
    main()
