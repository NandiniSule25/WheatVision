"""Checks whether ONNX Runtime can load on this Windows machine.

Run from the backend folder:  python check_onnx.py
"""
import subprocess
import sys

CODE = (
    "import onnxruntime as ort; "
    "print('onnxruntime', ort.__version__); "
    "print('providers', ort.get_available_providers())"
)

result = subprocess.run([sys.executable, "-c", CODE],
                        capture_output=True, text=True, timeout=120)

if result.returncode == 0:
    print("[OK]")
    print(result.stdout.strip())
else:
    print("[FAILED] ONNX Runtime could not be imported.")
    print(result.stderr.strip())