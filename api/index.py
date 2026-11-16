"""Vercel Serverless Function entrypoint for WheatVision.

Exposes the Flask application WSGI handler for the Vercel Python runtime.
"""
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode

# Ensure backend directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Mark serverless environment
os.environ["VERCEL"] = "1"

from app import app as flask_app


def app(environ, start_response):
    """WSGI wrapper ensuring exact path compatibility on Vercel."""
    query_string = environ.get("QUERY_STRING", "")
    params = parse_qs(query_string, keep_blank_values=True)

    # Check if __path__ was captured by vercel.json rewrite
    if "__path__" in params:
        subpath = params.pop("__path__")[0].strip("/")
        environ["QUERY_STRING"] = urlencode(params, doseq=True)
        environ["PATH_INFO"] = f"/api/{subpath}"
    else:
        # Check HTTP_X_MATCHED_PATH header
        matched = environ.get("HTTP_X_MATCHED_PATH") or environ.get("HTTP_X_VERCEL_MATCHED_PATH")
        if matched and not matched.endswith("index.py") and not matched.endswith("index"):
            environ["PATH_INFO"] = matched.split("?")[0]
        elif environ.get("PATH_INFO", "").endswith("index.py") or environ.get("PATH_INFO", "").endswith("index"):
            environ["PATH_INFO"] = "/api"

    return flask_app(environ, start_response)
