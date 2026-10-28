"""WheatVision Backend Application.

Main Flask application setup, database registration, CORS, error handlers,
and baseline routes.
"""
import os
import sys
import logging
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Load environment variables
load_dotenv(BASE_DIR / ".env")

import database

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("wheatvision")


def create_app(test_config=None):
    """Application factory for WheatVision Flask backend."""
    app = Flask(__name__, instance_relative_config=True)

    # Configuration defaults
    secret_key = os.getenv("SECRET_KEY", "wheatvision-default-secret-dev-only")
    if secret_key == "change-me-to-a-long-random-string" or secret_key == "wheatvision-default-secret-dev-only":
        logger.warning(
            "Running with default/placeholder SECRET_KEY. "
            "For production, set a strong random SECRET_KEY in backend/.env"
        )

    max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "5"))
    database_path = os.getenv("DATABASE_PATH", "instance/wheatvision.db")
    upload_folder = os.getenv("UPLOAD_FOLDER", "uploads")
    allowed_origins_raw = os.getenv(
        "ALLOWED_ORIGINS",
        "http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:5000,http://localhost:5000"
    )
    allowed_origins = [o.strip() for o in allowed_origins_raw.split(",") if o.strip()]

    app.config.from_mapping(
        SECRET_KEY=secret_key,
        DATABASE_PATH=database_path,
        UPLOAD_FOLDER=str((BASE_DIR / upload_folder).resolve()),
        MAX_CONTENT_LENGTH=max_upload_mb * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,  # Set to True when HTTPS is enabled
        WHEAT_THRESHOLD=float(os.getenv("WHEAT_THRESHOLD", "0.77")),
        SPECIES_THRESHOLD=float(os.getenv("SPECIES_THRESHOLD", "0.93")),
        DETECTOR_MODEL_PATH=os.getenv("DETECTOR_MODEL_PATH", "models/wheat_detector.onnx"),
        SPECIES_MODEL_PATH=os.getenv("SPECIES_MODEL_PATH", "models/wheat_species.onnx"),
        PROTEIN_REFERENCE_PATH=os.getenv("PROTEIN_REFERENCE_PATH", "data/protein_reference.json"),
    )

    if test_config:
        app.config.update(test_config)

    # Ensure uploads and instance directories exist
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "instance").mkdir(parents=True, exist_ok=True)

    # Setup database
    database.init_app(app)
    with app.app_context():
        database.init_db()

    # Setup CORS for frontend communication
    CORS(
        app,
        resources={r"/api/*": {"origins": allowed_origins}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    # Register Blueprints
    from auth import auth_bp
    from prediction import prediction_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(prediction_bp)

    # -------------------------------------------------------------
    # Error Handlers (Safe responses, never exposing stack traces)
    # -------------------------------------------------------------
    @app.errorhandler(400)
    def bad_request(error):
        message = getattr(error, "description", "Bad Request")
        return jsonify({"success": False, "error": message}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"success": False, "error": "Authentication required"}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"success": False, "error": "Access denied"}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"success": False, "error": "Requested resource not found"}), 404

    @app.errorhandler(413)
    def file_too_large(error):
        max_mb = app.config.get("MAX_CONTENT_LENGTH", 0) // (1024 * 1024)
        return jsonify({
            "success": False,
            "error": f"Uploaded file exceeds the maximum allowed size of {max_mb} MB"
        }), 413

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({"success": False, "error": "An internal server error occurred"}), 500

    @app.errorhandler(503)
    def service_unavailable(error):
        message = getattr(error, "description", "Service temporarily unavailable")
        return jsonify({"success": False, "error": message}), 503

    # -------------------------------------------------------------
    # Contact & Feedback Route
    # -------------------------------------------------------------
    @app.route("/api/contact", methods=["POST"])
    def submit_contact():
        """Accept public feedback or project inquiries."""
        data = request.get_json(silent=True) or request.form
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip()
        message = (data.get("message") or "").strip()

        if not name or not email or not message:
            return jsonify({"success": False, "error": "Please provide your name, email, and message."}), 400

        try:
            db = database.get_db()
            db.execute(
                "INSERT INTO contact_messages (name, email, message) VALUES (?, ?, ?)",
                (name, email, message)
            )
            db.commit()
            return jsonify({"success": True, "message": "Thank you! Your message has been sent successfully."}), 200
        except Exception as e:
            logger.error(f"Contact submit error: {e}")
            return jsonify({"success": False, "error": "Failed to submit message."}), 500

    # -------------------------------------------------------------
    # Frontend Serving & Health Check Routes
    # -------------------------------------------------------------
    FRONTEND_DIR = (BASE_DIR.parent / "frontend").resolve()

    @app.route("/", methods=["GET"])
    def root():
        """Serve frontend index.html if present, otherwise API status."""
        if (FRONTEND_DIR / "index.html").is_file():
            return send_from_directory(str(FRONTEND_DIR), "index.html")
        return jsonify({
            "message": "WheatVision Backend API is running",
            "health_check_url": "/api/health"
        }), 200

    @app.route("/<path:path>", methods=["GET"])
    def static_proxy(path):
        """Serve frontend static assets (CSS, js, assets)."""
        file_path = FRONTEND_DIR / path
        if file_path.is_file():
            return send_from_directory(str(FRONTEND_DIR), path)
        return jsonify({"success": False, "error": "Requested resource not found"}), 404

    @app.route("/api/health", methods=["GET"])
    def health_check():
        """Returns health status, database connectivity, and ONNX model status."""
        db_status = "error"
        try:
            db = database.get_db()
            db.execute("SELECT 1;").fetchone()
            db_status = "connected"
        except Exception as e:
            logger.error(f"Health check database query failed: {e}")

        # Check model file presence (without attempting execution)
        detector_rel = Path(app.config["DETECTOR_MODEL_PATH"])
        detector_path = detector_rel if detector_rel.is_absolute() else (BASE_DIR / detector_rel).resolve()

        species_rel = Path(app.config["SPECIES_MODEL_PATH"])
        species_path = species_rel if species_rel.is_absolute() else (BASE_DIR / species_rel).resolve()

        detector_present = detector_path.is_file()
        species_present = species_path.is_file()

        return jsonify({
            "success": True,
            "status": "healthy" if db_status == "connected" else "degraded",
            "database": db_status,
            "runtime_engine": "onnxruntime",
            "models": {
                "detector_onnx_present": detector_present,
                "species_onnx_present": species_present,
                "detector_path": str(detector_path.relative_to(BASE_DIR) if detector_path.is_relative_to(BASE_DIR) else detector_path),
                "species_path": str(species_path.relative_to(BASE_DIR) if species_path.is_relative_to(BASE_DIR) else species_path),
            },
            "environment": {
                "python_version": sys.version.split()[0],
                "debug": app.debug
            }
        }), 200

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False)
