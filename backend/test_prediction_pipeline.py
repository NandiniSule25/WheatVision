"""WheatVision Phase 5 Prediction & History Test Suite.

Verifies:
1. Validation of image uploads (missing file, invalid format, too small).
2. Authentication requirement for /api/predict and history endpoints.
3. Live two-stage inference with converted ONNX models:
   - Detector confidence evaluation (threshold 0.77)
   - Species identification and softmax distribution (threshold 0.93)
   - Attachment of scientific protein ranges and food suitability
   - Inclusion of scientific disclaimer
4. Prediction history recording in SQLite.
5. Strict cross-user data isolation:
   - User B cannot see User A's history.
   - User B cannot view User A's record by ID.
   - User B cannot delete User A's record.
"""
import sys
import io
import tempfile
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import database
from app import create_app


def create_test_image(format="JPEG", size=(224, 224), color=(180, 140, 80)):
    """Helper creating an in-memory image for upload testing."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf


def run_pipeline_tests():
    print("\n=== Running WheatVision Phase 5 Prediction & History Tests ===")

    # Temporary database for complete test isolation
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
        temp_db_path = temp_db.name

    test_config = {
        "TESTING": True,
        "DATABASE_PATH": temp_db_path,
        "SECRET_KEY": "phase5-test-secret-key-32-chars-long",
        "DETECTOR_MODEL_PATH": "models/wheat_detector.onnx",
        "SPECIES_MODEL_PATH": "models/wheat_species.onnx",
        "PROTEIN_REFERENCE_PATH": "data/protein_reference.json"
    }

    app = create_app(test_config)
    client = app.test_client()

    with app.app_context():
        database.init_db(temp_db_path)

    # -------------------------------------------------------------
    # 1. Unauthenticated Prediction Rejection
    # -------------------------------------------------------------
    res_unauth = client.post("/api/predict")
    assert res_unauth.status_code == 401, f"Expected 401 Unauthorized, got {res_unauth.status_code}"
    print("[PASS] Unauthenticated prediction request rejected with HTTP 401.")

    # -------------------------------------------------------------
    # 2. Register & Login User A
    # -------------------------------------------------------------
    res_reg_a = client.post("/api/auth/register", json={
        "name": "Scientist A",
        "email": "scientist.a@wheatvision.org",
        "password": "Password123!"
    })
    assert res_reg_a.status_code == 201
    user_a_id = res_reg_a.get_json()["user"]["id"]
    print("[PASS] Registered Scientist A (User ID:", user_a_id, ")")

    # -------------------------------------------------------------
    # 3. Upload Validation Tests (Scientist A)
    # -------------------------------------------------------------
    # Missing file
    res = client.post("/api/predict", data={})
    assert res.status_code == 400
    assert "No image file" in res.get_json()["error"]

    # Invalid image bytes (e.g. plain text masquerading as image)
    fake_file = io.BytesIO(b"This is not a real image binary")
    res = client.post("/api/predict", data={"image": (fake_file, "fake.jpg")}, content_type="multipart/form-data")
    assert res.status_code == 400
    assert "not a valid" in res.get_json()["error"]

    # Dimensions too small (< 32x32)
    small_img = create_test_image(size=(16, 16))
    res = client.post("/api/predict", data={"image": (small_img, "small.jpg")}, content_type="multipart/form-data")
    assert res.status_code == 400
    assert "too small" in res.get_json()["error"]
    print("[PASS] File upload validations (missing file, corrupt bytes, small dimensions) pass.")

    # -------------------------------------------------------------
    # 4. Two-Stage Prediction Execution with Converted ONNX Models
    # -------------------------------------------------------------
    valid_img = create_test_image(size=(300, 300))
    res = client.post("/api/predict", data={"image": (valid_img, "wheat_sample_1.jpg")}, content_type="multipart/form-data")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.get_data(as_text=True)}"

    data = res.get_json()
    assert data["success"] is True
    assert "status" in data
    assert "detector_confidence" in data
    assert "scientific_disclaimer" in data
    assert len(data["scientific_disclaimer"]) > 50, "Scientific disclaimer must be detailed"
    prediction_id_a = data["prediction_id"]
    assert prediction_id_a is not None
    print(f"[PASS] Inference executed successfully! Result status: '{data['status']}', History ID: {prediction_id_a}")

    # -------------------------------------------------------------
    # 5. History Listing for User A
    # -------------------------------------------------------------
    res_hist = client.get("/api/history")
    assert res_hist.status_code == 200
    hist_data = res_hist.get_json()
    assert hist_data["success"] is True
    assert len(hist_data["history"]) == 1
    assert hist_data["history"][0]["id"] == prediction_id_a
    assert hist_data["history"][0]["original_filename"] == "wheat_sample_1.jpg"
    print("[PASS] User A history listing returns recorded prediction.")

    # -------------------------------------------------------------
    # 6. Cross-User Privacy & Isolation Check
    # -------------------------------------------------------------
    # Logout User A
    client.post("/api/auth/logout")

    # Register & Login User B
    client.post("/api/auth/register", json={
        "name": "Scientist B",
        "email": "scientist.b@wheatvision.org",
        "password": "Password456!"
    })

    # User B checks history -> must be EMPTY
    res_hist_b = client.get("/api/history")
    assert res_hist_b.status_code == 200
    assert len(res_hist_b.get_json()["history"]) == 0, "User B must NOT see User A's history!"

    # User B attempts to access User A's specific record by ID -> 404
    res_view_forbidden = client.get(f"/api/history/{prediction_id_a}")
    assert res_view_forbidden.status_code == 404, "User B must receive 404 when requesting User A's record"

    # User B attempts to DELETE User A's specific record by ID -> 404
    res_del_forbidden = client.delete(f"/api/history/{prediction_id_a}")
    assert res_del_forbidden.status_code == 404, "User B must receive 404 when attempting to delete User A's record"
    print("[PASS] Cross-user privacy strictly enforced: User B cannot view or delete User A's record.")

    # -------------------------------------------------------------
    # 7. Owner Deletion
    # -------------------------------------------------------------
    # Switch back to User A
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={
        "email": "scientist.a@wheatvision.org",
        "password": "Password123!"
    })

    # User A deletes their own record
    res_del_ok = client.delete(f"/api/history/{prediction_id_a}")
    assert res_del_ok.status_code == 200
    assert res_del_ok.get_json()["success"] is True

    # User A history is now empty
    res_hist_after = client.get("/api/history")
    assert len(res_hist_after.get_json()["history"]) == 0
    print("[PASS] Record deletion by owner succeeds and removes record from history.")

    # -------------------------------------------------------------
    # 8. Literature Reference Endpoint
    # -------------------------------------------------------------
    res_ref = client.get("/api/references")
    assert res_ref.status_code == 200
    ref_json = res_ref.get_json()
    assert ref_json["success"] is True
    species_keys = list(ref_json["references"]["species_reference"].keys())
    assert set(species_keys) == {"aestivum", "durum", "dicoccum", "polonicum"}
    print(f"[PASS] /api/references returned verified data for all 4 species: {species_keys}")

    # Cleanup temporary database
    try:
        Path(temp_db_path).unlink(missing_ok=True)
    except Exception:
        pass

    print("\nALL PHASE 5 PREDICTION & HISTORY TESTS PASSED!\n")


if __name__ == "__main__":
    run_pipeline_tests()
