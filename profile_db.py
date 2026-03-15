import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "profiles.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    # WAL mode: allows simultaneous reads during writes, no blocking
    conn.execute("PRAGMA journal_mode=WAL")
    # If DB is locked, retry for up to 10 seconds instead of crashing
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def init_db():
    """Create tables if they don't exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                account_id   TEXT PRIMARY KEY,
                platform     TEXT NOT NULL,
                nume         TEXT,
                varsta       TEXT,
                oras         TEXT,
                job          TEXT,
                relatii      TEXT,
                interese     TEXT,
                familie      TEXT,
                stare        TEXT,
                extra        TEXT,
                updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def get_profile(account_id: str, platform: str) -> dict:
    """Load profile for an account. Returns empty dict if not found."""
    init_db()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM profiles WHERE account_id = ? AND platform = ?",
            (account_id, platform),
        ).fetchone()

    if not row:
        return {}

    profile = dict(row)

    # Parse extra JSON field
    if profile.get("extra"):
        try:
            profile["extra"] = json.loads(profile["extra"])
        except Exception:
            profile["extra"] = {}

    # Remove None values
    return {k: v for k, v in profile.items() if v is not None}


def update_profile(account_id: str, platform: str, new_data: dict):
    """
    Merge new_data into existing profile.
    Only updates fields that have a value in new_data.
    """
    init_db()

    known_fields = {"nume", "varsta", "oras", "job", "relatii", "interese", "familie", "stare"}

    extra = {}
    updates = {}

    for key, value in new_data.items():
        if not value:
            continue
        if key in known_fields:
            updates[key] = value
        else:
            extra[key] = value

    with _get_conn() as conn:
        # Upsert
        existing = conn.execute(
            "SELECT extra FROM profiles WHERE account_id = ? AND platform = ?",
            (account_id, platform),
        ).fetchone()

        if existing:
            # Merge extra
            existing_extra = {}
            if existing["extra"]:
                try:
                    existing_extra = json.loads(existing["extra"])
                except Exception:
                    pass
            existing_extra.update(extra)

            set_clauses = ", ".join([f"{k} = ?" for k in updates])
            values = list(updates.values())

            if extra:
                if set_clauses:
                    set_clauses += ", extra = ?, updated_at = CURRENT_TIMESTAMP"
                else:
                    set_clauses = "extra = ?, updated_at = CURRENT_TIMESTAMP"
                values.append(json.dumps(existing_extra))
            else:
                if set_clauses:
                    set_clauses += ", updated_at = CURRENT_TIMESTAMP"

            if set_clauses:
                conn.execute(
                    f"UPDATE profiles SET {set_clauses} WHERE account_id = ? AND platform = ?",
                    values + [account_id, platform],
                )
        else:
            fields = list(updates.keys()) + ["account_id", "platform"]
            values = list(updates.values()) + [account_id, platform]

            if extra:
                fields.append("extra")
                values.append(json.dumps(extra))

            placeholders = ", ".join(["?" for _ in fields])
            field_names = ", ".join(fields)
            conn.execute(
                f"INSERT INTO profiles ({field_names}) VALUES ({placeholders})",
                values,
            )

        conn.commit()


def profile_to_context(profile: dict) -> str:
    """
    Convert a profile dict into a natural language string
    to inject into the Cohere prompt.
    """
    if not profile:
        return ""

    lines = ["Informatii cunoscute despre persoana cu care vorbesti:"]

    field_labels = {
        "nume": "Nume",
        "varsta": "Varsta",
        "oras": "Oras",
        "job": "Job",
        "relatii": "Situatie relationala",
        "interese": "Interese / hobby-uri",
        "familie": "Familie",
        "stare": "Stare emotionala recenta",
    }

    for field, label in field_labels.items():
        value = profile.get(field)
        if value:
            lines.append(f"- {label}: {value}")

    extra = profile.get("extra")
    if isinstance(extra, dict):
        for key, value in extra.items():
            lines.append(f"- {key}: {value}")

    if len(lines) == 1:
        return ""

    return "\n".join(lines)