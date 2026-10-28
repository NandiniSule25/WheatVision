"""WheatVision Prediction & History API Module.

Implements:
- Validated image upload (multipart/form-data)
- Two-stage detector-first inference with thresholds (0.77 / 0.93)
- Literature-based protein and food suitability lookup
- Comprehensive scientific disclaimer
- Authenticated user prediction history (list, view, delete) strictly scoped to user_id
"""
import io
import json
import logging
from pathlib import Path
from flask import Blueprint, request, jsonify, g, current_app
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError

import database
from auth import login_required
from predictor import get_predictor, SPECIES_CLASSES

logger = logging.getLogger("wheatvision.prediction")

prediction_bp = Blueprint("prediction", __name__, url_prefix="/api")

ALLOWED_IMAGE_FORMATS = {"JPEG", "JPG", "PNG", "WEBP"}
MIN_IMAGE_DIMENSION = 32
MAX_IMAGE_DIMENSION = 8000

BASE_DIR = Path(__file__).resolve().parent


def load_protein_reference() -> dict:
    """Load the literature-based protein and food suitability reference JSON."""
    ref_path_str = current_app.config.get("PROTEIN_REFERENCE_PATH", "data/protein_reference.json")
    p = Path(ref_path_str)
    ref_path = p if p.is_absolute() else (BASE_DIR / p).resolve()

    if not ref_path.is_file():
        logger.warning(f"Protein reference file missing at {ref_path}")
        return {
            "scientific_disclaimer": "Literature reference currently unavailable.",
            "species_reference": {}
        }

    try:
        with open(ref_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read protein reference file: {e}")
        return {"scientific_disclaimer": "Error loading reference.", "species_reference": {}}


@prediction_bp.route("/predict", methods=["POST"])
@login_required
def predict():
    """Two-stage prediction endpoint for authenticated users.

    Accepts multipart/form-data with file field 'image' or 'file'.
    Runs detector -> species classifier -> literature reference lookup -> saves history.
    """
    # 1. Validate file presence
    uploaded_file = request.files.get("image") or request.files.get("file")
    if not uploaded_file or uploaded_file.filename == "":
        return jsonify({
            "success": False,
            "error": "No image file provided. Please upload an image with field name 'image'."
        }), 400

    # 2. Validate file content and dimensions using Pillow
    try:
        file_bytes = uploaded_file.read()
        if len(file_bytes) == 0:
            return jsonify({"success": False, "error": "The uploaded file is empty."}), 400

        image = Image.open(io.BytesIO(file_bytes))
        image_format = (image.format or "").upper()
        if image_format not in ALLOWED_IMAGE_FORMATS and image_format != "MPO":
            return jsonify({
                "success": False,
                "error": f"Unsupported image format ({image_format or 'unknown'}). Supported formats: JPEG, PNG, WEBP."
            }), 400

        width, height = image.size
        if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
            return jsonify({
                "success": False,
                "error": f"Image dimensions ({width}x{height}) are too small. Minimum required: {MIN_IMAGE_DIMENSION}x{MIN_IMAGE_DIMENSION}px."
            }), 400

        if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
            return jsonify({
                "success": False,
                "error": f"Image dimensions ({width}x{height}) exceed maximum allowed dimension of {MAX_IMAGE_DIMENSION}px."
            }), 400

    except UnidentifiedImageError:
        return jsonify({"success": False, "error": "The uploaded file is not a valid or readable image."}), 400
    except Exception as e:
        logger.error(f"Image read error: {e}")
        return jsonify({"success": False, "error": "Failed to process image file."}), 400

    # 3. Check ONNX predictor availability
    predictor = get_predictor(current_app)
    if not predictor.is_available:
        return jsonify({
            "success": False,
            "status": "model_unavailable",
            "error": "Trained ONNX models are not yet deployed. Please convert the .keras models in Google Colab and place the .onnx files in backend/models/."
        }), 503

    # 4. Execute two-stage inference
    pred_result = predictor.predict(image)
    if not pred_result.get("success"):
        return jsonify(pred_result), 500

    # 5. Attach literature reference and scientific disclaimer
    ref_data = load_protein_reference()
    disclaimer = ref_data.get("scientific_disclaimer", "")

    literature_info = None
    protein_range_str = None
    food_suitability_str = None

    predicted_species = pred_result.get("predicted_species")
    if pred_result.get("is_wheat") and predicted_species:
        species_entry = ref_data.get("species_reference", {}).get(predicted_species)
        if species_entry:
            literature_info = species_entry
            prot = species_entry.get("protein_range", {})
            protein_range_str = f"{prot.get('min_percent')}% - {prot.get('max_percent')}% {prot.get('unit', '')}".strip()
            foods = species_entry.get("suitable_food_products", [])
            food_suitability_str = "; ".join(foods) if foods else None

    # 6. Save to prediction history in SQLite
    safe_filename = secure_filename(uploaded_file.filename) or "grain_sample.jpg"
    db = database.get_db()
    try:
        cursor = db.execute("""
            INSERT INTO prediction_history (
                user_id, original_filename, predicted_species,
                detector_confidence, species_confidence,
                protein_reference_range, food_suitability,
                prediction_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            g.user["id"],
            safe_filename,
            predicted_species if pred_result.get("is_wheat") else None,
            pred_result.get("detector_confidence"),
            pred_result.get("species_confidence"),
            protein_range_str,
            food_suitability_str,
            pred_result.get("status")
        ))
        db.commit()
        history_id = cursor.lastrowid
    except Exception as e:
        logger.error(f"Failed to record prediction in database: {e}")
        history_id = None

    # 7. Formulate final response
    response_payload = {
        "success": True,
        "prediction_id": history_id,
        "status": pred_result.get("status"),
        "is_wheat": pred_result.get("is_wheat"),
        "detector_confidence": pred_result.get("detector_confidence"),
        "message": pred_result.get("message"),
        "species_analysis": {
            "predicted_species": pred_result.get("predicted_species"),
            "scientific_name": pred_result.get("scientific_name"),
            "common_name": pred_result.get("common_name"),
            "species_confidence": pred_result.get("species_confidence"),
            "is_confident_species": pred_result.get("is_confident_species"),
            "species_threshold_applied": pred_result.get("species_threshold_applied"),
            "all_species_probabilities": pred_result.get("all_species_probabilities", [])
        } if pred_result.get("is_wheat") else None,
        "literature_insights": literature_info,
        "scientific_disclaimer": disclaimer
    }

    return jsonify(response_payload), 200


@prediction_bp.route("/history", methods=["GET"])
@login_required
def list_history():
    """List authenticated user's prediction history with pagination."""
    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = min(100, max(1, int(request.args.get("limit", 20))))
    except ValueError:
        page, limit = 1, 20

    offset = (page - 1) * limit
    db = database.get_db()

    total_count = db.execute(
        "SELECT COUNT(*) as count FROM prediction_history WHERE user_id = ?",
        (g.user["id"],)
    ).fetchone()["count"]

    rows = db.execute("""
        SELECT id, user_id, original_filename, predicted_species,
               detector_confidence, species_confidence,
               protein_reference_range, food_suitability,
               prediction_status, created_at
        FROM prediction_history
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, (g.user["id"], limit, offset)).fetchall()

    records = [dict(r) for r in rows]

    return jsonify({
        "success": True,
        "history": records,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total_count,
            "pages": (total_count + limit - 1) // limit if total_count > 0 else 1
        }
    }), 200


@prediction_bp.route("/history/<int:record_id>", methods=["GET"])
@login_required
def get_history_record(record_id: int):
    """Retrieve an individual prediction record, strictly owned by current user."""
    db = database.get_db()
    row = db.execute("""
        SELECT id, user_id, original_filename, predicted_species,
               detector_confidence, species_confidence,
               protein_reference_range, food_suitability,
               prediction_status, created_at
        FROM prediction_history
        WHERE id = ? AND user_id = ?
    """, (record_id, g.user["id"])).fetchone()

    if not row:
        return jsonify({
            "success": False,
            "error": "Prediction record not found or access denied."
        }), 404

    record = dict(row)
    ref_data = load_protein_reference()
    if record.get("predicted_species"):
        record["literature_insights"] = ref_data.get("species_reference", {}).get(record["predicted_species"])
        record["scientific_disclaimer"] = ref_data.get("scientific_disclaimer")

    return jsonify({
        "success": True,
        "record": record
    }), 200


@prediction_bp.route("/history/<int:record_id>", methods=["DELETE"])
@login_required
def delete_history_record(record_id: int):
    """Delete an individual prediction record, strictly owned by current user."""
    db = database.get_db()
    cursor = db.execute(
        "DELETE FROM prediction_history WHERE id = ? AND user_id = ?",
        (record_id, g.user["id"])
    )
    db.commit()

    if cursor.rowcount == 0:
        return jsonify({
            "success": False,
            "error": "Prediction record not found or access denied."
        }), 404

    return jsonify({
        "success": True,
        "message": "Prediction record deleted successfully."
    }), 200


@prediction_bp.route("/references", methods=["GET"])
def get_all_references():
    """Return the complete literature reference dataset."""
    ref_data = load_protein_reference()
    return jsonify({
        "success": True,
        "references": ref_data
    }), 200
