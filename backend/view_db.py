"""WheatVision Database Viewer Utility.

Run from PowerShell:
    python backend/view_db.py

Displays all stored users, prediction history, and contact messages.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "instance" / "wheatvision.db"


def view_database():
    if not DB_PATH.exists():
        print(f"[!] Database file not found at: {DB_PATH}")
        return

    print("=" * 80)
    print(f"DATABASE FILE: {DB_PATH}")
    print("=" * 80)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Users Table
    print("\n--- 1. TABLE: users ---")
    users = cursor.execute("SELECT id, name, email, created_at FROM users").fetchall()
    if not users:
        print("   (No users registered yet)")
    else:
        for u in users:
            print(f"   [ID: {u['id']}] Name: {u['name']} | Email: {u['email']} | Registered: {u['created_at']}")

    # 2. Prediction History Table
    print("\n--- 2. TABLE: prediction_history ---")
    history = cursor.execute("""
        SELECT id, user_id, original_filename, predicted_species,
               detector_confidence, species_confidence, prediction_status, created_at
        FROM prediction_history
        ORDER BY created_at DESC
    """).fetchall()
    if not history:
        print("   (No prediction history records yet)")
    else:
        for h in history:
            det = f"{h['detector_confidence'] * 100:.1f}%" if h['detector_confidence'] else "N/A"
            spec = f"{h['species_confidence'] * 100:.1f}%" if h['species_confidence'] else "N/A"
            print(f"   [ID: {h['id']}] UserID: {h['user_id']} | File: {h['original_filename']} | "
                  f"Status: {h['prediction_status']} | Species: {h['predicted_species']} ({spec}) | "
                  f"Detector: {det} | Date: {h['created_at']}")

    # 3. Contact Messages Table
    print("\n--- 3. TABLE: contact_messages ---")
    messages = cursor.execute("SELECT id, name, email, message, created_at FROM contact_messages").fetchall()
    if not messages:
        print("   (No contact messages yet)")
    else:
        for m in messages:
            print(f"   [ID: {m['id']}] From: {m['name']} <{m['email']}> on {m['created_at']}")
            print(f"        Message: \"{m['message']}\"")

    print("\n" + "=" * 80 + "\n")
    conn.close()


if __name__ == "__main__":
    view_database()
