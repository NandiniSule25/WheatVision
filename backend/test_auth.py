"""WheatVision Phase 3 Authentication Test Suite.

Verifies:
1. User registration with validation (valid data, short password, invalid email).
2. Duplicate email rejection (HTTP 409).
3. Secure password hashing (no plaintext passwords in database).
4. User login (valid credentials, invalid password, nonexistent user).
5. Protected route access (/api/auth/me) with and without active session.
6. User logout and session clearing.
"""
import sys
import tempfile
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import database
from app import create_app


def run_auth_tests():
    print("\n=== Running WheatVision Phase 3 Authentication Tests ===")

    # Use a temporary isolated database for testing
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
        temp_db_path = temp_db.name

    test_config = {
        "TESTING": True,
        "DATABASE_PATH": temp_db_path,
        "SECRET_KEY": "test-secret-key-32-bytes-long!!"
    }

    app = create_app(test_config)
    client = app.test_client()

    with app.app_context():
        database.init_db(temp_db_path)

    # -------------------------------------------------------------
    # 1. User Registration Validation
    # -------------------------------------------------------------
    # Test missing fields
    res = client.post("/api/auth/register", json={})
    assert res.status_code == 400, f"Expected 400, got {res.status_code}"

    # Test invalid email
    res = client.post("/api/auth/register", json={
        "name": "Jane Doe",
        "email": "not-an-email",
        "password": "valid_password123"
    })
    assert res.status_code == 400, f"Expected 400 for invalid email, got {res.status_code}"

    # Test short password
    res = client.post("/api/auth/register", json={
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "123"
    })
    assert res.status_code == 400, f"Expected 400 for short password, got {res.status_code}"
    print("[PASS] Registration field validations work correctly.")

    # -------------------------------------------------------------
    # 2. Valid Registration
    # -------------------------------------------------------------
    res = client.post("/api/auth/register", json={
        "name": "Wheat Researcher",
        "email": "researcher@example.com",
        "password": "StrongPassword!987"
    })
    assert res.status_code == 201, f"Expected 201, got {res.status_code}"
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["email"] == "researcher@example.com"
    assert "password" not in data["user"]
    print("[PASS] User registration succeeds with HTTP 201.")

    # -------------------------------------------------------------
    # 3. Duplicate Email Rejection
    # -------------------------------------------------------------
    res_dup = client.post("/api/auth/register", json={
        "name": "Another Name",
        "email": "researcher@example.com",  # Same email
        "password": "AnotherPassword456!"
    })
    assert res_dup.status_code == 409, f"Expected 409 Conflict, got {res_dup.status_code}"
    assert "already exists" in res_dup.get_json()["error"]
    print("[PASS] Duplicate email rejection returns HTTP 409 Conflict.")

    # -------------------------------------------------------------
    # 4. Plaintext Password Absence (Secure Hash Verification)
    # -------------------------------------------------------------
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM users WHERE email = 'researcher@example.com'").fetchone()
    conn.close()

    assert row is not None
    stored_hash = row["password_hash"]
    assert "StrongPassword!987" not in stored_hash, "ERROR: Password stored as plaintext!"
    assert stored_hash.startswith("scrypt:") or stored_hash.startswith("pbkdf2:"), \
        f"Unexpected hash format: {stored_hash}"
    print(f"[PASS] Passwords are secure: stored hash begins with '{stored_hash.split(':')[0]}'.")

    # -------------------------------------------------------------
    # 5. Protected Route Access (/api/auth/me) While Logged In
    # -------------------------------------------------------------
    res_me = client.get("/api/auth/me")
    assert res_me.status_code == 200, f"Expected 200, got {res_me.status_code}"
    me_data = res_me.get_json()
    assert me_data["success"] is True
    assert me_data["user"]["email"] == "researcher@example.com"
    assert "password_hash" not in me_data["user"]
    print("[PASS] Protected /api/auth/me endpoint returns current user profile.")

    # -------------------------------------------------------------
    # 6. Logout
    # -------------------------------------------------------------
    res_logout = client.post("/api/auth/logout")
    assert res_logout.status_code == 200
    print("[PASS] Logout clears session.")

    # -------------------------------------------------------------
    # 7. Protected Route Access While Logged Out
    # -------------------------------------------------------------
    res_unauth = client.get("/api/auth/me")
    assert res_unauth.status_code == 401, f"Expected 401, got {res_unauth.status_code}"
    print("[PASS] Accessing protected route without session returns HTTP 401 Unauthorized.")

    # -------------------------------------------------------------
    # 8. Login (Incorrect & Correct Credentials)
    # -------------------------------------------------------------
    # Wrong password
    res_wrong = client.post("/api/auth/login", json={
        "email": "researcher@example.com",
        "password": "WrongPassword123!"
    })
    assert res_wrong.status_code == 401
    assert "Invalid email or password" in res_wrong.get_json()["error"]

    # Non-existent email
    res_none = client.post("/api/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "StrongPassword!987"
    })
    assert res_none.status_code == 401

    # Correct credentials
    res_correct = client.post("/api/auth/login", json={
        "email": "researcher@example.com",
        "password": "StrongPassword!987"
    })
    assert res_correct.status_code == 200
    assert res_correct.get_json()["success"] is True
    print("[PASS] Login authentication functions correctly for valid and invalid credentials.")

    # Clean up temporary database file
    try:
        Path(temp_db_path).unlink(missing_ok=True)
    except Exception:
        pass

    print("\nALL PHASE 3 AUTHENTICATION TESTS PASSED!\n")


if __name__ == "__main__":
    run_auth_tests()
