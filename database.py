"""
SafeRide AI - Module 2: Backend Database Layer (database.py)
-----------------------------------------------------------
PostgreSQL relational database storage for emergency incident records,
rider statuses, GPS coordinates, and multilingual communication threads.

Schema:
  - incidents table:
      incident_id (TEXT PRIMARY KEY)
      timestamp (TEXT)
      vehicle_type (TEXT)
      latitude (REAL)
      longitude (REAL)
      confidence (REAL)
      rider_status (TEXT)  # 'NORMAL', 'PENDING_CHECK', "I'M OK", 'NEED HELP', 'NO RESPONSE'
      language (TEXT)      # 'Telugu', 'English'
      message (TEXT)       # Primary/latest message
      status (TEXT)        # 'REPORTED', 'DISPATCHED', 'RESOLVED', 'CLOSED'
  
  - incident_messages table:
      message_id (INTEGER PRIMARY KEY AUTOINCREMENT)
      incident_id (TEXT, FOREIGN KEY)
      sender (TEXT)        # 'Rider', 'Responder', 'System'
      original_text (TEXT)
      translated_text (TEXT)
      timestamp (TEXT)
"""

import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saferide.db")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


def get_connection(db_path: str = DB_FILE):
    """Return a PostgreSQL connection using the DATABASE_URL environment variable.

    The db_path argument is preserved for compatibility with the legacy public API
    but is ignored because PostgreSQL connections come from DATABASE_URL.
    """
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL must be set for the PostgreSQL backend. "
            "Example: postgresql://user:pass@host:5432/dbname"
        )
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db(db_path: str = DB_FILE, seed_sample_data: bool = True) -> None:
    """Creates required tables and indices if they do not exist."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            confidence DOUBLE PRECISION NOT NULL,
            rider_status TEXT NOT NULL DEFAULT 'PENDING_CHECK',
            language TEXT NOT NULL DEFAULT 'Telugu',
            message TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'REPORTED',
            address TEXT DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incident_messages (
            message_id SERIAL PRIMARY KEY,
            incident_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            original_text TEXT NOT NULL,
            translated_text TEXT DEFAULT '',
            timestamp TEXT NOT NULL,
            CONSTRAINT fk_incident_messages_incident
                FOREIGN KEY (incident_id) REFERENCES incidents (incident_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_timestamp ON incidents(timestamp DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_incident_messages_incident_id ON incident_messages(incident_id)")

    conn.commit()

    if seed_sample_data:
        cursor.execute("SELECT COUNT(*) AS c FROM incidents")
        row = cursor.fetchone()
        if row and int(row["c"]) == 0:
            seed_initial_data(conn)

    conn.close()


def create_incident(
    vehicle_type: str,
    latitude: float,
    longitude: float,
    confidence: float,
    rider_status: str = "NEED HELP",
    language: str = "Telugu",
    message: str = "",
    status: str = "REPORTED",
    address: str = "",
    incident_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    db_path: str = DB_FILE
) -> str:
    """Creates a new accident incident record."""
    if not incident_id:
        incident_id = f"INC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    if not timestamp:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO incidents (
            incident_id, timestamp, vehicle_type, latitude, longitude,
            confidence, rider_status, language, message, status, address
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        incident_id, timestamp, vehicle_type, latitude, longitude,
        confidence, rider_status, language, message, status, address
    ))

    if message:
        cursor.execute("""
            INSERT INTO incident_messages (incident_id, sender, original_text, translated_text, timestamp)
            VALUES (%s, 'Rider', %s, '', %s)
        """, (incident_id, message, timestamp))

    conn.commit()
    conn.close()
    return incident_id


def update_incident(incident_id: str, db_path: str = DB_FILE, **kwargs) -> bool:
    """
    Updates specific fields of an incident record.
    Usage: update_incident("INC-101", status="DISPATCHED", rider_status="NEED HELP")
    """
    if not kwargs:
        return False

    allowed_fields = {
        "timestamp", "vehicle_type", "latitude", "longitude",
        "confidence", "rider_status", "language", "message", "status", "address"
    }

    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed_fields:
            fields.append(f"{k} = %s")
            values.append(v)

    if not fields:
        return False

    values.append(incident_id)
    query = f"UPDATE incidents SET {', '.join(fields)} WHERE incident_id = %s"

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(query, values)
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def get_incident(incident_id: str, db_path: str = DB_FILE) -> Optional[Dict[str, Any]]:
    """Retrieves a single incident by its ID as a dictionary."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents WHERE incident_id = %s", (incident_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_incidents(limit: int = 50, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """Retrieves all incidents sorted by most recent first."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents ORDER BY timestamp DESC LIMIT %s", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_incident_message(
    incident_id: str,
    sender: str,
    original_text: str,
    translated_text: str = "",
    db_path: str = DB_FILE
) -> int:
    """Appends a message to the incident communication thread."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO incident_messages (incident_id, sender, original_text, translated_text, timestamp)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING message_id
    """, (incident_id, sender, original_text, translated_text, ts))

    row = cursor.fetchone()
    msg_id = row["message_id"] if row else 0

    cursor.execute("""
        UPDATE incidents SET message = %s WHERE incident_id = %s
    """, (original_text, incident_id))

    conn.commit()
    conn.close()
    return int(msg_id)


def get_incident_messages(incident_id: str, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """Retrieves all messages for an incident ordered chronologically."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM incident_messages
        WHERE incident_id = %s
        ORDER BY message_id ASC
    """, (incident_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def seed_initial_data(conn) -> None:
    """Pre-populates realistic incident records for immediate demo readiness."""
    cursor = conn.cursor()

    demo_incidents = [
        (
            "INC-2026-HYD-001",
            "2026-09-07 10:15:20",
            "Motorcycle",
            17.4435,
            78.3772,
            94.5,
            "NEED HELP",
            "Telugu",
            "?? ???? ???? ???? ??????????????, ?????? ????? ??????.",
            "REPORTED"
        ),
        (
            "INC-2026-HYD-002",
            "2026-09-07 09:42:10",
            "Scooter",
            17.4156,
            78.4350,
            72.8,
            "NO RESPONSE",
            "Telugu",
            "?????? ????????: 10 ?????? ???? ????? ????? ??????? ??????.",
            "DISPATCHED"
        ),
        (
            "INC-2026-HYD-003",
            "2026-09-07 08:30:45",
            "Electric Bike",
            17.4239,
            78.3374,
            42.0,
            "I'M OK",
            "English",
            "Slipped on gravel during rain. No injuries, I'm safe.",
            "RESOLVED"
        ),
    ]

    cursor.executemany("""
        INSERT INTO incidents (
            incident_id, timestamp, vehicle_type, latitude, longitude,
            confidence, rider_status, language, message, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, demo_incidents)

    messages = [
        ("INC-2026-HYD-001", "Rider", "?? ???? ???? ???? ??????????????, ?????? ????? ??????.", "My leg is stuck under the bike, need help immediately.", "2026-09-07 10:15:22"),
        ("INC-2026-HYD-001", "Responder", "Help is on the way. Ambulance dispatched from Cyberabad Emergency Center.", "????? ?????? ????. ????????? ??????? ??????? ????? ?????????? ?????????.", "2026-09-07 10:16:05"),
        ("INC-2026-HYD-001", "Rider", "???? ????? ????????, ?????? ????.", "Bleeding heavily, please come fast.", "2026-09-07 10:16:40"),
        ("INC-2026-HYD-002", "System", "Emergency trigger: Unresponsive rider after 10-second safety prompt.", "?????????? ?????????: 10 ?????? ?????? ????????? ?????? ????? ????????????.", "2026-09-07 09:42:20"),
        ("INC-2026-HYD-002", "Responder", "Emergency team dispatched with GPS tracking to Banjara Hills location.", "???????????? ?????????? ??????? ???????????? ??????? ????? ?????????.", "2026-09-07 09:43:10")
    ]

    cursor.executemany("""
        INSERT INTO incident_messages (incident_id, sender, original_text, translated_text, timestamp)
        VALUES (%s, %s, %s, %s, %s)
    """, messages)

    conn.commit()


if __name__ == "__main__":
    print("Initializing PostgreSQL database...")
    init_db()
    records = get_all_incidents()
    print(f"Database ready! Loaded {len(records)} incidents.")
    for rec in records:
        print(f" - [{rec['status']}] {rec['incident_id']} ({rec['vehicle_type']}) - Confidence: {rec['confidence']}% - Status: {rec['rider_status']}")
