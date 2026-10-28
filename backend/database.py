"""WheatVision Database Module.

Handles SQLite connection pooling, schema initialization, and teardown.
Safe to run repeatedly.
"""
import os
import sqlite3
from pathlib import Path
from flask import g, current_app

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "instance" / "wheatvision.db"


def get_db_path():
    """Retrieve database path from Flask config or environment variable."""
    if current_app:
        configured_path = current_app.config.get("DATABASE_PATH")
        if configured_path:
            p = Path(configured_path)
            return p if p.is_absolute() else (BASE_DIR / p).resolve()
    env_path = os.getenv("DATABASE_PATH")
    if env_path:
        p = Path(env_path)
        return p if p.is_absolute() else (BASE_DIR / p).resolve()
    return DEFAULT_DB_PATH


def get_db():
    """Get or open a SQLite connection for the current Flask request context."""
    if "db" not in g:
        db_path = get_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(
            str(db_path),
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
        g.db.execute("PRAGMA journal_mode = WAL;")
    return g.db


def close_db(e=None):
    """Close the SQLite connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db_path=None):
    """Initialize database tables idempotently.

    Can be called within or outside of Flask request context.
    """
    target_path = Path(db_path) if db_path else get_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(target_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Prediction history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prediction_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            original_filename TEXT NOT NULL,
            predicted_species TEXT,
            detector_confidence REAL,
            species_confidence REAL,
            protein_reference_range TEXT,
            food_suitability TEXT,
            prediction_status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
    """)

    # Contact messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Performance indices
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_history_user_id ON prediction_history(user_id);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_history_created_at ON prediction_history(created_at DESC);
    """)

    conn.commit()
    conn.close()
    return target_path


def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)


if __name__ == "__main__":
    path = init_db()
    print(f"[OK] Database initialized successfully at: {path}")
