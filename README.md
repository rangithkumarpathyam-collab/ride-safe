# 🛡️ SafeRide AI — Multimodal Emergency Response System

**SafeRide AI** is an intelligent, automated accident detection and emergency dispatch platform designed to reduce emergency response times and save lives during two-wheeler and vehicular accidents.

---

## 🚀 Key Features

### 1. 🚨 Telemetry Accident Detection Engine (`accident_detection.py`)
- Real-time accident detection and severity classification based on velocity drops, g-force impact vectors, and tilt angle changes.
- Confidence scoring with dynamic severity tiers (**CRITICAL**, **HIGH**, **MEDIUM**, **LOW**).

### 2. ⏱️ Automated 10-Second Emergency Dispatch Timer (`app.py`)
- Automatically triggers a 10-second countdown upon crash detection.
- Dispatches emergency location alerts, GPS telematics, and automated voice calls to emergency numbers (`108` and emergency contacts) via **Twilio** if not cancelled by the rider.

### 3. 🗺️ Live GIS Mapping & Geocoding (`geocoding.py` & `app.py`)
- **OpenStreetMap (OSM) + Leaflet.js**: 100% Free, open-source live interactive map with emergency crash perimeter highlights and sirens.
- **Geoapify Reverse Geocoding**: Automatically converts raw GPS coordinates (`latitude`, `longitude`) into human-readable physical street addresses and landmarks.

### 4. 📲 WhatsApp & SMS Emergency Dispatch (`notifications.py`)
- **1-Click WhatsApp Instant Send**: Direct link to open WhatsApp with pre-formatted emergency crash coordinates, severity, and turn-by-turn Google Maps navigation routes.
- **Automated Twilio SMS & Voice Calling**: Automated speech synthesis call placing and SMS alert dispatch.

### 5. 💬 Multilingual Emergency Chat Hub (`translation.py`)
- Neural bidirectional translation supporting **Telugu ↔ English** for communication between regional riders and emergency responders.

### 6. 🗄️ SQLite Telemetry & Incident Audit Trail (`database.py`)
- Persistent SQLite database logging all telemetry events, incident statuses (`REPORTED`, `DISPATCHED`, `RESOLVED`), and chat threads.

---

## 🛠️ Technology Stack
- **Frontend / Dashboard**: Streamlit, Custom HTML5/CSS3, Leaflet.js, OpenStreetMap
- **Backend / Engine**: Python 3.10+, SQLite3
- **Telecommunications**: Twilio Programmable Voice, Twilio SMS, WhatsApp Web / API
- **GIS & Mapping**: OpenStreetMap (OSM), Geoapify Geocoding API, Leaflet.js
- **Translation**: Deep Translator (Telugu <-> English)

---

## 📦 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rangithkumarpathyam-collab/ride-safe.git
   cd ride-safe
   ```

2. **Create a virtual environment & install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Fill in your API credentials (Twilio, Geoapify, etc.).

4. **Run the application:**
   ```bash
   streamlit run app.py
   ```
   Open `http://localhost:8502` in your browser.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
