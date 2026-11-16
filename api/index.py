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
    path_info = environ.get("PATH_INFO", "")
    
    # If Vercel stripped '/api' from an API endpoint, restore it
    api_endpoints = ("predict", "health", "auth", "references", "history", "contact")
    trimmed = path_info.lstrip("/")
    if any(trimmed == ep or trimmed.startswith(f"{ep}/") for ep in api_endpoints):
        environ["PATH_INFO"] = f"/api/{trimmed}"
        
    return flask_app(environ, start_response)
