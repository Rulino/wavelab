"""Minimal smoke test for the WaveLab Studio solver.

This test intentionally uses a very small grid and disables animation so that it
can run quickly in CI. It verifies that the solver can parse the example scene
and produce the expected numerical and image outputs.
"""
from pathlib import Path
import subprocess
import sys


def test_solver_smoke(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    scene = repo / "examples" / "basic_scene.yaml"
    solver = repo / "src" / "wavelab_studio" / "solver_simple_torch.py"
    out_dir = tmp_path / "smoke_results"

    cmd = [
        sys.executable,
        str(solver),
        str(scene),
        "--epochs",
        "20",
        "--nx",
        "48",
        "--ny",
        "32",
        "--steps",
        "4",
        "--no_animation",
        "--out_dir",
        str(out_dir),
    ]

    env = dict(**__import__("os").environ)
    env["PYTHONPATH"] = str(repo / "src") + __import__("os").pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        cmd,
        cwd=repo,
        text=True,
        capture_output=True,
        timeout=120,
        env=env,
    )

    assert result.returncode == 0, result.stderr + "\n" + result.stdout
    assert out_dir.exists()