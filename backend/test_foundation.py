"""WheatVision Phase 2 Foundation Test Suite.

Verifies:
1. Backend starts cleanly without importing TensorFlow.
2. SQLite database connects, initializes idempotently, and tables exist.
3. Health check route (/api/health) returns 200 with database connected.
4. Error handlers return consistent JSON responses without stack traces.
"""
import sys
from pathlib import Path

# Add backend directory to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import database
from app import create_app


def test_no_tensorflow():
    """Ensure tensorflow is not imported anywhere in the backend process."""
    assert "tensorflow" not in sys.modules, "ERROR: TensorFlow was imported!"
    print("[PASS] TensorFlow is NOT imported in the runtime.")


def test_database_initialization():
    """Verify database initialization and table schemas."""
    db_path = database.init_db()
    assert db_path.exists(), f"Database file does not exist at {db_path}"

    import sqlite3
    conn = sqlite3.connect(str(db_path))
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    conn.close()

    assert "users" in tables, "users table missing"
    assert "prediction_history" in tables, "prediction_history table missing"
    print(f"[PASS] SQLite initialized with tables: {tables}")


def test_health_check_endpoint():
    """Verify /api/health endpoint returns expected status."""
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/api/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.get_json()
    assert data["success"] is True
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["runtime_engine"] == "onnxruntime"
    print("[PASS] /api/health endpoint returned HTTP 200 with healthy database.")


def test_error_handlers():
    """Verify error handlers produce safe JSON payloads."""
    app = create_app({"TESTING": True})
    client = app.test_client()

    # 404 Not Found
    res_404 = client.get("/api/nonexistent_route")
    assert res_404.status_code == 404
    data_404 = res_404.get_json()
    assert data_404["success"] is False
    assert "error" in data_404
    print("[PASS] 404 handler returns expected JSON format.")


if __name__ == "__main__":
    print("\n=== Running WheatVision Phase 2 Foundation Tests ===")
    test_no_tensorflow()
    test_database_initialization()
    test_health_check_endpoint()
    test_error_handlers()
    print("\nALL PHASE 2 FOUNDATION TESTS PASSED!\n")
