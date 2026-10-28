"""WheatVision environment checker.

Run from the backend folder:  python check_env.py
It only reads information. It does not change anything.
"""
import subprocess
import sys
from importlib import metadata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

PACKAGES = ["Flask", "Werkzeug", "Flask-Cors", "python-dotenv",
            "Pillow", "numpy", "tensorflow", "keras"]

PATHS = {
    "detector model": BASE_DIR / "models" / "wheat_detector.keras",
    "species model": BASE_DIR / "models" / "wheat_species.keras",
    ".env file": BASE_DIR / ".env",
    "uploads folder": BASE_DIR / "uploads",
    "instance folder": BASE_DIR / "instance",
    "frontend folder": BASE_DIR.parent / "frontend",
}


def section(title):
    print(f"\n=== {title} ===")


def check_python():
    section("Python")
    print("Version   :", sys.version.split()[0])
    print("Executable:", sys.executable)
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    print("In venv   :", in_venv)
    if ".venv" not in sys.executable:
        print("WARNING: not using backend/.venv. Activate it first.")


def check_packages():
    section("Installed packages")
    for name in PACKAGES:
        try:
            print(f"{name:15} {metadata.version(name)}")
        except metadata.PackageNotFoundError:
            print(f"{name:15} NOT INSTALLED")


def check_paths():
    section("Files and folders")
    for label, path in PATHS.items():
        if path.exists():
            size = f"{path.stat().st_size / 1_048_576:.2f} MB" if path.is_file() else "folder"
            print(f"[OK]      {label:16} ({size})")
        else:
            print(f"[MISSING] {label:16} -> expected at {path.relative_to(BASE_DIR.parent)}")


def check_tensorflow():
    section("TensorFlow import test (in a separate process)")
    code = "import tensorflow as tf; print('TensorFlow', tf.__version__)"
    result = subprocess.run([sys.executable, "-c", code],
                            capture_output=True, text=True, timeout=180)
    if result.returncode == 0:
        print("[OK]", result.stdout.strip())
    else:
        print("[FAILED] TensorFlow could not be imported.")
        print("--- full error output below ---")
        print(result.stderr.strip())


if __name__ == "__main__":
    check_python()
    check_packages()
    check_paths()
    check_tensorflow()