import sys
import subprocess
from pathlib import Path

def find_solver_script() -> Path:
    """
    Run the solver first to create a video output.
    Priority: solver_simple_torch.py, then older material-specific scripts.
    """
    candidates = ["solver_simple_torch.py", "metal.py", "wood.py", "water.py", "time.py"]
    for name in candidates:
        p = Path(__file__).with_name(name)
        if p.exists():
            return p
    raise FileNotFoundError(
        "No solver found. Expected one of: solver_simple_torch.py / metal.py / wood.py / water.py / time.py "
        "in the project directory."
    )

def main() -> int:
    solver = find_solver_script()

    # Implementation note.
    cmd = [sys.executable, str(solver), *sys.argv[1:]]

    print(f"[solver_modulus] Using solver: {solver.name}", flush=True)
    print(f"[solver_modulus] Running: {' '.join(cmd)}", flush=True)

    return subprocess.call(cmd)

if __name__ == "__main__":
    raise SystemExit(main())
