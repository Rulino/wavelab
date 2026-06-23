#!/usr/bin/env python3
# test_amplitude_effect.py

import sys
import subprocess
from pathlib import Path

try:
    import yaml
except Exception:
    print("ERROR: Install PyYAML: pip install pyyaml")
    raise

ROOT = Path(__file__).resolve().parent
SOLVER = ROOT / "solver_simple_torch.py"
OUT = ROOT / "amplitude_test_results"

BASE_SCENE = {
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
            "amplitude": 1.0,
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


def write_scene(path: Path, amplitude: float) -> None:
    data = {
        "materials": dict(BASE_SCENE["materials"]),
        "scene": {
            "source": dict(BASE_SCENE["scene"]["source"]),
            "objects": [dict(o) for o in BASE_SCENE["scene"]["objects"]],
        },
    }

    data["scene"]["source"]["amplitude"] = float(amplitude)

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def parse_metrics(path: Path) -> dict:
    metrics = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            metrics[k.strip()] = v.strip()
    return metrics


def metric_float(metrics: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(metrics.get(key, default))
    except Exception:
        return float(default)


def run_case(name: str, amplitude: float) -> dict:
    case_dir = OUT / name
    case_dir.mkdir(parents=True, exist_ok=True)

    scene_path = OUT / f"{name}.yaml"
    write_scene(scene_path, amplitude)

    cmd = [
        sys.executable,
        str(SOLVER),
        str(scene_path),
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

    print(f"\nRunning: {name}")
    print(" ".join(cmd))

    result = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)

    print(result.stdout)

    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("solver failed")

    metrics_path = case_dir / "metrics.txt"
    if not metrics_path.exists():
        raise FileNotFoundError(f"Missing metrics.txt: {metrics_path}")

    metrics = parse_metrics(metrics_path)
    metrics["case_dir"] = str(case_dir)
    metrics["scene_path"] = str(scene_path)
    metrics["amplitude"] = str(amplitude)

    return metrics


def main() -> None:
    if not SOLVER.exists():
        raise FileNotFoundError(f"solver_simple_torch.py not found: {SOLVER}")

    OUT.mkdir(exist_ok=True)

    low = run_case("amp_0_5", 0.5)
    high = run_case("amp_2_0", 2.0)

    low_amp = metric_float(low, "source_amplitude", 0.5)
    high_amp = metric_float(high, "source_amplitude", 2.0)

    low_energy = metric_float(low, "field_energy", 0.0)
    high_energy = metric_float(high, "field_energy", 0.0)

    low_max = metric_float(low, "field_max_abs", 0.0)
    high_max = metric_float(high, "field_max_abs", 0.0)

    passed = True
    reasons = []

    if not (high_amp > low_amp):
        passed = False
        reasons.append("high amplitude is not bigger than low amplitude")

    if low_energy > 0 and high_energy > 0 and not (high_energy > low_energy):
        passed = False
        reasons.append("high amplitude field_energy is not bigger than low amplitude field_energy")

    if low_max > 0 and high_max > 0 and not (high_max > low_max):
        passed = False
        reasons.append("high amplitude field_max_abs is not bigger than low amplitude field_max_abs")

    report = []
    report.append("SOURCE AMPLITUDE TEST REPORT")
    report.append("=" * 34)
    report.append("")
    report.append("Low amplitude: 0.5")
    report.append(f"  source_amplitude: {low_amp}")
    report.append(f"  field_energy:     {low_energy}")
    report.append(f"  field_max_abs:    {low_max}")
    report.append(f"  results:          {low['case_dir']}")
    report.append("")
    report.append("High amplitude: 2.0")
    report.append(f"  source_amplitude: {high_amp}")
    report.append(f"  field_energy:     {high_energy}")
    report.append(f"  field_max_abs:    {high_max}")
    report.append(f"  results:          {high['case_dir']}")
    report.append("")
    report.append("EXPECTED VISUAL RESULT:")
    report.append("  amplitude=0.5 -> weaker/darker waves")
    report.append("  amplitude=2.0 -> stronger/brighter waves")
    report.append("")
    report.append("STATUS: " + ("PASS" if passed else "FAIL"))

    if reasons:
        report.append("")
        report.append("Reasons:")
        for r in reasons:
            report.append("  - " + r)

    text = "\n".join(report)
    report_path = OUT / "amplitude_test_report.txt"
    report_path.write_text(text, encoding="utf-8")

    print("\n" + text)
    print(f"\nReport saved: {report_path}")

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
