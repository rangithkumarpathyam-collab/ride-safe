"""
SafeRide AI - Module 2: Backend Database Layer (database.py)
-----------------------------------------------------------
SQLite relational database storage for emergency incident records,
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

import sqlite3
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saferide.db")


def get_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    """Returns a SQLite connection with row factory configured."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_FILE, seed_sample_data: bool = True) -> None:
    """Creates required tables and indices if they do not exist."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Create incidents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            confidence REAL NOT NULL,
            rider_status TEXT NOT NULL DEFAULT 'PENDING_CHECK',
            language TEXT NOT NULL DEFAULT 'Telugu',
            message TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'REPORTED',
            address TEXT DEFAULT ''
        )
    """)

    # Ensure address column exists for existing databases
    cursor.execute("PRAGMA table_info(incidents)")
    cols = [col[1] for col in cursor.fetchall()]
    if "address" not in cols:
        cursor.execute("ALTER TABLE incidents ADD COLUMN address TEXT DEFAULT ''")

    # Create incident_messages table for live chat
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incident_messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            original_text TEXT NOT NULL,
            translated_text TEXT DEFAULT '',
            timestamp TEXT NOT NULL,
            FOREIGN KEY (incident_id) REFERENCES incidents (incident_id) ON DELETE CASCADE
        )
    """)

    conn.commit()

    # Seed initial demo data if database is newly initialized
    if seed_sample_data:
        cursor.execute("SELECT COUNT(*) FROM incidents")
        count = cursor.fetchone()[0]
        if count == 0:
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        incident_id, timestamp, vehicle_type, latitude, longitude,
        confidence, rider_status, language, message, status, address
    ))

    # Add initial incident message if provided
    if message:
        cursor.execute("""
            INSERT INTO incident_messages (incident_id, sender, original_text, translated_text, timestamp)
            VALUES (?, 'Rider', ?, '', ?)
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
            fields.append(f"{k} = ?")
            values.append(v)

    if not fields:
        return False

    values.append(incident_id)
    query = f"UPDATE incidents SET {', '.join(fields)} WHERE incident_id = ?"

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
    cursor.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_incidents(limit: int = 50, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """Retrieves all incidents sorted by most recent first."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents ORDER BY timestamp DESC LIMIT ?", (limit,))
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
        VALUES (?, ?, ?, ?, ?)
    """, (incident_id, sender, original_text, translated_text, ts))

    # Also update the latest message on the parent incident record
    cursor.execute("""
        UPDATE incidents SET message = ? WHERE incident_id = ?
    """, (original_text, incident_id))

    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    return msg_id


def get_incident_messages(incident_id: str, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """Retrieves all messages for an incident ordered chronologically."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM incident_messages
        WHERE incident_id = ?
        ORDER BY message_id ASC
    """, (incident_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def seed_initial_data(conn: sqlite3.Connection) -> None:
    """Pre-populates realistic incident records for immediate demo readiness."""
    cursor = conn.cursor()

    demo_incidents = [
        (
            "INC-2026-HYD-001",
            "2026-09-07 10:15:20",
            "Motorcycle",
            17.4435,
            78.3772,  # Hitec City, Hyderabad
            94.5,
            "NEED HELP",
            "Telugu",
            "నా కాలు బైక్ కింద ఇరుక్కుపోయింది, వెంటనే సహాయం కావాలి.",
            "REPORTED"
        ),
        (
            "INC-2026-HYD-002",
            "2026-09-07 09:42:10",
            "Scooter",
            17.4156,
            78.4350,  # Banjara Hills, Hyderabad
            72.8,
            "NO RESPONSE",
            "Telugu",
            "క్రాష్ హెచ్చరిక: 10 సెకన్ల పాటు రైడర్ నుండి సమాధానం రాలేదు.",
            "DISPATCHED"
        ),
        (
            "INC-2026-HYD-003",
            "2026-09-07 08:30:45",
            "Electric Bike",
            17.4239,
            78.3374,  # Gachibowli, Hyderabad
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, demo_incidents)

    # Prepopulate message threads for the active incident
    messages = [
        ("INC-2026-HYD-001", "Rider", "నా కాలు బైక్ కింద ఇరుక్కుపోయింది, వెంటనే సహాయం కావాలి.", "My leg is stuck under the bike, need help immediately.", "2026-09-07 10:15:22"),
        ("INC-2026-HYD-001", "Responder", "Help is on the way. Ambulance dispatched from Cyberabad Emergency Center.", "సహాయం దారిలో ఉంది. సైబరాబాద్ అత్యవసర కేంద్రం నుండి అంబులెన్స్ పంపబడింది.", "2026-09-07 10:16:05"),
        ("INC-2026-HYD-001", "Rider", "చాలా రక్తం వస్తోంది, త్వరగా రండి.", "Bleeding heavily, please come fast.", "2026-09-07 10:16:40"),
        ("INC-2026-HYD-002", "System", "Emergency trigger: Unresponsive rider after 10-second safety prompt.", "ఎమర్జెన్సీ ట్రిగ్గర్: 10 సెకన్ల భద్రతా ప్రాంప్ట్ తర్వాత రైడర్ స్పందించలేదు.", "2026-09-07 09:42:20"),
        ("INC-2026-HYD-002", "Responder", "Emergency team dispatched with GPS tracking to Banjara Hills location.", "బంజారాహిల్స్ లొకేషన్‌కు జీపీఎస్ ట్రాకింగ్‌తో అత్యవసర బృందం పంపబడింది.", "2026-09-07 09:43:10")
    ]

    cursor.executemany("""
        INSERT INTO incident_messages (incident_id, sender, original_text, translated_text, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, messages)

    conn.commit()


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    records = get_all_incidents()
    print(f"Database ready! Loaded {len(records)} incidents.")
    for rec in records:
        print(f" - [{rec['status']}] {rec['incident_id']} ({rec['vehicle_type']}) - Confidence: {rec['confidence']}% - Status: {rec['rider_status']}")
