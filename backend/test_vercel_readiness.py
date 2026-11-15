"""Test Vercel serverless readiness and read-only environment compatibility."""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR.parent / "api"))

# Simulate Vercel environment
os.environ["VERCEL"] = "1"

import database
from index import app as wsgi_app


def test_vercel_db_fallback():
    """Verify that Vercel environment automatically redirects SQLite to temp dir."""
    db_path = database.get_db_path()
    assert "tmp" in str(db_path).lower() or "temp" in str(db_path).lower(), f"Expected temp in db_path, got {db_path}"
    print(f"[PASS] Vercel environment successfully routes SQLite to: {db_path}")


def test_vercel_wsgi_handler():
    """Simulate a WSGI call through api/index.py."""
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/api/health",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "5000",
        "wsgi.url_scheme": "http",
        "wsgi.input": None,
    }

    status_code = None
    headers = []

    def start_response(status, response_headers, exc_info=None):
        nonlocal status_code, headers
        status_code = status
        headers = response_headers

    response = wsgi_app(environ, start_response)
    assert status_code.startswith("200"), f"Expected 200 OK, got {status_code}"
    print(f"[PASS] Vercel WSGI entrypoint responds with HTTP {status_code}")


if __name__ == "__main__":
    print("\n=== Running Vercel Readiness Tests ===")
    test_vercel_db_fallback()
    test_vercel_wsgi_handler()
    print("\nALL VERCEL READINESS TESTS PASSED!\n")
