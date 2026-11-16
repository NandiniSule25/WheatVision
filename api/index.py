"""Vercel Serverless Function entrypoint for WheatVision.

Exposes the Flask application WSGI handler for the Vercel Python runtime.
"""
import os
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Mark serverless environment
os.environ["VERCEL"] = "1"

from app import app as flask_app


def app(environ, start_response):
    """WSGI wrapper ensuring path compatibility on Vercel."""
    # When Vercel rewrites to /api/index.py, the original request path is in HTTP_X_MATCHED_PATH
    matched = environ.get("HTTP_X_MATCHED_PATH") or environ.get("HTTP_X_VERCEL_MATCHED_PATH")
    if matched and not matched.endswith("index.py"):
        environ["PATH_INFO"] = matched.split("?")[0]

    path_info = environ.get("PATH_INFO", "")

    # If Vercel stripped '/api' from an API endpoint, restore it for Flask blueprints
    api_endpoints = ("predict", "health", "auth", "references", "history", "contact")
    trimmed = path_info.lstrip("/")
    if any(trimmed == ep or trimmed.startswith(f"{ep}/") for ep in api_endpoints):
        environ["PATH_INFO"] = f"/api/{trimmed}"

    return flask_app(environ, start_response)
