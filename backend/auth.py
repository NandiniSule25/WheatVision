"""WheatVision Authentication Module.

Provides secure registration, login, logout, and profile management
using Werkzeug password hashing and secure Flask sessions.
"""
import re
import functools
import sqlite3
from flask import Blueprint, request, jsonify, session, g
from werkzeug.security import generate_password_hash, check_password_hash

import database

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def login_required(view):
    """View decorator ensuring the request is made by an authenticated user."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return jsonify({"success": False, "error": "Authentication required. Please log in."}), 401
        return view(**kwargs)
    return wrapped_view


@auth_bp.before_app_request
def load_logged_in_user():
    """Load the current authenticated user into the request context (g.user)."""
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        db = database.get_db()
        user = db.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        if user is None:
            # Session exists for deleted or invalid user id
            session.clear()
            g.user = None
        else:
            g.user = dict(user)


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user account.

    Accepts JSON or form data with 'name', 'email', and 'password'.
    """
    data = request.get_json(silent=True) or request.form

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    # Validation
    if not name:
        return jsonify({"success": False, "error": "Name is required"}), 400
    if len(name) < 2 or len(name) > 100:
        return jsonify({"success": False, "error": "Name must be between 2 and 100 characters"}), 400

    if not email:
        return jsonify({"success": False, "error": "Email is required"}), 400
    if not EMAIL_REGEX.match(email):
        return jsonify({"success": False, "error": "Please provide a valid email address"}), 400

    if not password:
        return jsonify({"success": False, "error": "Password is required"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters long"}), 400
    if len(password) > 128:
        return jsonify({"success": False, "error": "Password cannot exceed 128 characters"}), 400

    # Securely hash the password
    password_hash = generate_password_hash(password)

    db = database.get_db()
    try:
        cursor = db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash)
        )
        db.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({
            "success": False,
            "error": "An account with this email address already exists"
        }), 409
    except Exception as e:
        return jsonify({"success": False, "error": "Failed to create user account"}), 500

    # Automatically log the user in after registration
    session.clear()
    session["user_id"] = user_id
    session.permanent = True

    return jsonify({
        "success": True,
        "message": "User registered successfully",
        "user": {
            "id": user_id,
            "name": name,
            "email": email
        }
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate an existing user.

    Accepts JSON or form data with 'email' and 'password'.
    """
    data = request.get_json(silent=True) or request.form

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password are required"}), 400

    db = database.get_db()
    user = db.execute(
        "SELECT id, name, email, password_hash FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    # Use constant-time comparison via check_password_hash; return generic error on mismatch
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "error": "Invalid email or password"}), 401

    session.clear()
    session["user_id"] = user["id"]
    session.permanent = True

    return jsonify({
        "success": True,
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
    }), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Clear session data and log out the user."""
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"}), 200


@auth_bp.route("/me", methods=["GET"])
@login_required
def get_current_user():
    """Return profile details for the currently authenticated user."""
    return jsonify({
        "success": True,
        "user": g.user
    }), 200
