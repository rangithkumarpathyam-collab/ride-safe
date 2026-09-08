"""
SafeRide AI - Multimodal Emergency Command Center (app.py)
-----------------------------------------------------------
Central emergency dispatch dashboard uniting:
  - Module 1: Telemetry Accident Detection Engine (accident_detection.py)
  - Module 2: SQLite Incident & Telemetry Store (database.py)
  - Module 3: Reverse Geocoding & Address Resolution (geocoding.py)
  - Module 4: Bidirectional English <-> Telugu Translation (translation.py)
  - Module 5: Responder Command Dashboard UI (app.py)
  - Module 6: Twilio Emergency SMS & Voice Calling Backbone (notifications.py)
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime
import time
import urllib.parse
from dotenv import load_dotenv

# Load active environment variables
load_dotenv()

# SafeRide AI Internal Engine Modules
import database as db
import accident_detection as ad
import geocoding as geo
import translation as tr
import notifications as notify

# Configure Streamlit App
st.set_page_config(
    page_title="SafeRide AI - Multimodal Emergency Response System",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Styling for Emergency Command Center
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Top Brand Header */
    .brand-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.55rem 0.2rem 1.05rem;
        background: transparent;
        border: 0;
        border-radius: 0;
        margin-bottom: 0.35rem;
        box-shadow: none;
    }
    .brand-title {
        font-size: 1.45rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #f8fafc;
        margin: 0;
    }
    .brand-subtitle {
        font-size: 0.76rem;
        color: #94a3b8;
        margin-top: 3px;
    }
    .operator-meta {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        color: #9aa9bf;
        font-size: 0.68rem;
        font-weight: 700;
    }
    .operator-avatar {
        display: grid;
        place-items: center;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: linear-gradient(145deg, #38bdf8, #2563eb);
        color: #fff;
        font-size: 0.75rem;
    }
    .live-pulse {
        display: inline-block;
        width: 10px;
        height: 10px;
        background-color: #ef4444;
        border-radius: 50%;
        margin-right: 6px;
        box-shadow: 0 0 12px #ef4444;
        animation: pulse 1.6s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(0.95); opacity: 0.85; }
        50% { transform: scale(1.2); opacity: 1; }
        100% { transform: scale(0.95); opacity: 0.85; }
    }
    
    /* 10-Second SOS Emergency Countdown Banner */
    .sos-banner {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.18) 0%, rgba(185, 28, 28, 0.28) 100%);
        border: 2px solid #ef4444;
        border-radius: 14px;
        padding: 1.2rem 1.6rem;
        margin-bottom: 1.4rem;
        box-shadow: 0 0 25px rgba(239, 68, 68, 0.35);
        animation: sos-pulse 1.8s infinite;
    }
    @keyframes sos-pulse {
        0% { box-shadow: 0 0 15px rgba(239, 68, 68, 0.25); border-color: #ef4444; }
        50% { box-shadow: 0 0 35px rgba(239, 68, 68, 0.6); border-color: #f87171; }
        100% { box-shadow: 0 0 15px rgba(239, 68, 68, 0.25); border-color: #ef4444; }
    }
    .sos-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: #fecaca;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .sos-timer-number {
        font-size: 3.2rem;
        font-weight: 900;
        color: #ef4444;
        text-shadow: 0 0 20px rgba(239, 68, 68, 0.7);
        font-family: 'Inter', monospace;
        letter-spacing: -1px;
    }
    
    /* API Status Badges Bar */
    .api-status-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        padding: 0.7rem 1rem;
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid #1e293b;
        border-radius: 10px;
        margin-bottom: 1.2rem;
    }
    .api-pill {
        display: inline-flex;
        align-items: center;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 20px;
        background: #1e293b;
        color: #cbd5e1;
        border: 1px solid #334155;
    }
    .api-pill-online {
        border-color: rgba(16, 185, 129, 0.4);
        background: rgba(16, 185, 129, 0.1);
        color: #34d399;
    }
    .api-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        margin-right: 6px;
        display: inline-block;
    }
    .api-dot-green { background: #10b981; box-shadow: 0 0 8px #10b981; }
    .api-dot-yellow { background: #f59e0b; box-shadow: 0 0 8px #f59e0b; }

    /* Quiet operational status strip */
    .ops-strip {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
        margin: 0 0 1.2rem;
    }
    .ops-item {
        display: flex;
        align-items: center;
        gap: 9px;
        min-height: 48px;
        padding: 0.65rem 0.85rem;
        background: rgba(30, 41, 59, 0.72);
        border: 1px solid rgba(100, 116, 139, 0.28);
        border-radius: 10px;
    }
    .ops-item strong { display: block; color: #e2e8f0; font-size: 0.8rem; }
    .ops-item span { display: block; color: #94a3b8; font-size: 0.72rem; margin-top: 2px; }
    .ops-icon {
        display: grid;
        place-items: center;
        width: 28px;
        height: 28px;
        border-radius: 8px;
        background: rgba(56, 189, 248, 0.12);
        color: #7dd3fc;
        font-size: 0.95rem;
    }
    @media (max-width: 760px) {
        .ops-strip { grid-template-columns: 1fr; }
        .brand-header { padding: 1rem; }
        .brand-title { font-size: 1.25rem; }
    }
    
    /* Stat Metric Cards */
    .metric-card {
        background: linear-gradient(145deg, #172438, #111b2b);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 11px;
        padding: 0.85rem 1rem;
        text-align: center;
        box-shadow: 0 8px 18px rgba(0, 0, 0, 0.16);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 4px;
    }
    .service-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin: 0 0 1.1rem;
    }
    .service-chip {
        border: 1px solid rgba(16, 185, 129, 0.7);
        border-radius: 999px;
        padding: 0.25rem 0.65rem;
        color: #9fe8c4;
        background: rgba(16, 185, 129, 0.07);
        font-size: 0.68rem;
        font-weight: 700;
    }
    .service-chip::before { content: "●"; color: #22c55e; margin-right: 0.35rem; }
    .incident-shell {
        background: linear-gradient(145deg, rgba(24, 36, 58, 0.96), rgba(17, 27, 43, 0.96));
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.85rem;
    }
    .incident-shell-title { color: #f8fafc; font-size: 1.05rem; font-weight: 800; }
    .incident-shell-meta { color: #7d8da5; font-size: 0.7rem; float: right; }
    .verified-address {
        border: 1px solid #1da6e0;
        background: rgba(29, 166, 224, 0.12);
        border-radius: 9px;
        padding: 0.7rem 0.85rem;
        margin: 0.7rem 0;
        color: #d8f4ff;
        font-size: 0.82rem;
        font-weight: 700;
    }
    .recent-log-card {
        background: linear-gradient(145deg, #172438, #111b2b);
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-radius: 11px;
        padding: 0.8rem 0.85rem;
        margin-bottom: 0.55rem;
    }
    .recent-log-id { color: #e2e8f0; font-weight: 800; font-size: 0.78rem; }
    .recent-log-time { color: #71819a; float: right; font-size: 0.68rem; }
    .recent-log-copy { color: #8fa0b7; font-size: 0.72rem; margin-top: 0.42rem; line-height: 1.35; }
    .recent-log-badge { float: right; border-radius: 4px; padding: 0.17rem 0.4rem; font-size: 0.6rem; font-weight: 800; }
    .badge-critical { background: rgba(239, 68, 68, 0.18); color: #f87171; }
    .badge-warning { background: rgba(245, 158, 11, 0.18); color: #fbbf24; }
    .badge-resolved { background: rgba(16, 185, 129, 0.18); color: #34d399; }
    .section-kicker {
        color: #71819a;
        font-size: 0.65rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }
    .metric-card .metric-value { line-height: 1; }
    .metric-card .metric-label { font-size: 0.68rem; }
    [data-testid="stSidebar"] h1 { font-size: 1.05rem; }
    [data-testid="stSidebar"] h3 { font-size: 0.8rem; color: #d7e1ef; text-transform: uppercase; letter-spacing: 0.08em; }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #71819a; font-size: 0.68rem; }
    
    /* Incident Badges */
    .badge {
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-need-help {
        background-color: rgba(239, 68, 68, 0.2);
        color: #f87171;
        border: 1px solid #ef4444;
    }
    .badge-no-response {
        background-color: rgba(245, 158, 11, 0.2);
        color: #fbbf24;
        border: 1px solid #f59e0b;
    }
    .badge-ok {
        background-color: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border: 1px solid #10b981;
    }
    .badge-dispatched {
        background-color: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
        border: 1px solid #3b82f6;
    }
    
    /* Address Container */
    .address-card {
        background: #0f172a;
        border-left: 4px solid #38bdf8;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.75rem;
    }
    
    /* Chat Box Styling */
    .chat-bubble-rider {
        background: #1e293b;
        border-left: 4px solid #ef4444;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.75rem;
    }
    .chat-bubble-responder {
        background: #0f172a;
        border-right: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.75rem;
        text-align: right;
    }
    .chat-sender {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 3px;
    }
    .chat-original {
        font-size: 0.95rem;
        font-weight: 600;
        color: #f1f5f9;
    }
    .chat-translated {
        font-size: 0.85rem;
        color: #94a3b8;
        font-style: italic;
        margin-top: 3px;
    }
    .chat-timestamp {
        font-size: 0.7rem;
        color: #64748b;
        margin-top: 4px;
    }

    /* Live Location Tracker Panel */
    .location-tracker-card {
        background: linear-gradient(135deg, #0c1a2e 0%, #0f2942 100%);
        border: 1.5px solid #1d4ed8;
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 0 30px rgba(29, 78, 216, 0.2);
    }
    .location-tracker-title {
        font-size: 1.05rem;
        font-weight: 800;
        color: #93c5fd;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .gps-coord-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(29, 78, 216, 0.2);
        border: 1px solid rgba(59, 130, 246, 0.4);
        border-radius: 8px;
        padding: 6px 12px;
        font-size: 0.85rem;
        font-weight: 700;
        color: #93c5fd;
        font-family: 'Courier New', monospace;
        margin-right: 8px;
        margin-bottom: 8px;
    }
    .whatsapp-btn-container {
        background: linear-gradient(135deg, rgba(37, 211, 102, 0.15) 0%, rgba(18, 140, 126, 0.15) 100%);
        border: 1.5px solid rgba(37, 211, 102, 0.5);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-top: 1rem;
    }
    .whatsapp-btn-title {
        font-size: 0.9rem;
        font-weight: 700;
        color: #4ade80;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .whatsapp-direct-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: #ffffff !important;
        text-decoration: none !important;
        font-weight: 800;
        font-size: 0.92rem;
        padding: 10px 18px;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(37, 211, 102, 0.4);
        transition: all 0.2s ease;
        border: none;
        cursor: pointer;
        width: 100%;
        text-align: center;
        margin-top: 6px;
        margin-bottom: 6px;
    }
    .whatsapp-direct-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(37, 211, 102, 0.6);
        background: linear-gradient(135deg, #2ae06d 0%, #179e8e 100%);
    }
    .wa-success-banner {
        background: rgba(37, 211, 102, 0.12);
        border: 1.5px solid rgba(37, 211, 102, 0.5);
        border-radius: 10px;
        padding: 0.8rem 1rem;
        margin-top: 0.8rem;
        color: #4ade80;
        font-size: 0.88rem;
        font-weight: 600;
    }
    .static-map-overlay {
        border-radius: 12px;
        overflow: hidden;
        border: 2px solid #1d4ed8;
        box-shadow: 0 0 20px rgba(29, 78, 216, 0.3);
        margin-top: 0.8rem;
    }
    .crash-marker-pulse {
        display: inline-block;
        width: 12px;
        height: 12px;
        background: #ef4444;
        border-radius: 50%;
        box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
        animation: crash-ping 1.4s ease-in-out infinite;
    }
    @keyframes crash-ping {
        0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }

    /* Responsive command-center layout */
    :root {
        --surface-0: #080d16;
        --surface-1: #111a2a;
        --surface-2: #18243a;
        --line: rgba(148, 163, 184, 0.2);
        --muted: #91a2bb;
        --text: #f7fafc;
        --accent: #63b3ed;
    }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 85% 0%, rgba(37, 99, 235, 0.13), transparent 30rem),
            var(--surface-0);
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stMainBlockContainer"] {
        max-width: 1480px;
        padding: 2.5rem clamp(1rem, 3vw, 3.5rem) 4rem;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #151d2d 0%, #101622 100%);
        border-right: 1px solid var(--line);
    }
    [data-testid="stSidebar"] > div:first-child { padding: 1.25rem 1rem 2rem; }
    h1, h2, h3 { color: var(--text); letter-spacing: -0.02em; }
    h2, h3 { margin-top: 0.35rem; }
    [data-testid="stHorizontalBlock"] {
        gap: clamp(0.75rem, 1.5vw, 1.25rem);
        align-items: stretch;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--line);
        border-radius: 14px;
        background: rgba(17, 26, 42, 0.72);
    }
    [data-testid="stButton"] button,
    [data-testid="stFormSubmitButton"] button {
        min-height: 2.65rem;
        border-radius: 9px;
        border: 1px solid rgba(148, 163, 184, 0.28);
        font-weight: 700;
        transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
    }
    [data-testid="stButton"] button:hover,
    [data-testid="stFormSubmitButton"] button:hover {
        transform: translateY(-1px);
        border-color: rgba(99, 179, 237, 0.7);
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.22);
    }
    [data-testid="stSelectbox"] > div,
    [data-testid="stTextInput"] > div { border-radius: 9px; }
    [data-testid="stProgressBar"] > div > div { background: linear-gradient(90deg, #ef4444, #f59e0b); }
    .metric-card { min-height: 88px; display: flex; flex-direction: column; justify-content: center; }
    .location-tracker-card { min-height: 132px; }

    @media (max-width: 900px) {
        [data-testid="stMainBlockContainer"] { padding: 1.25rem 1rem 3rem; }
        [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            min-width: calc(50% - 0.5rem) !important;
            flex: 1 1 calc(50% - 0.5rem) !important;
        }
        .brand-header { padding: 1rem 1.1rem; }
        .brand-title { font-size: 1.35rem; line-height: 1.25; }
        .sos-banner { padding: 1rem; }
        .sos-title { font-size: 1.05rem; }
        .location-tracker-card { padding: 1rem; }
    }
    @media (max-width: 560px) {
        [data-testid="stMainBlockContainer"] { padding: 0.85rem 0.75rem 2.5rem; }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }
        .brand-header { align-items: flex-start; gap: 0.8rem; }
        .brand-title { font-size: 1.08rem; }
        .brand-subtitle { font-size: 0.75rem; }
        .live-pulse { width: 8px; height: 8px; }
        .sos-title { align-items: flex-start; line-height: 1.35; }
        .sos-timer-number { font-size: 2.6rem; }
        .gps-coord-chip { width: 100%; margin-right: 0; }
        .location-tracker-title { font-size: 0.92rem; }
        .whatsapp-btn-container { padding: 0.85rem; }
        .metric-card { min-height: 76px; }
        .service-chips { margin-bottom: 0.75rem; }
        iframe[title="streamlit_components.html"] { width: 100% !important; }
    }
</style>
""", unsafe_allow_html=True)


# Initialize SQLite Database on startup
db.init_db()

# Initialize Streamlit Session State for Emergency 10s SOS Timer
if "sos_timer_active" not in st.session_state:
    st.session_state["sos_timer_active"] = False
if "sos_incident_id" not in st.session_state:
    st.session_state["sos_incident_id"] = None
if "sos_call_result" not in st.session_state:
    st.session_state["sos_call_result"] = None
if "sos_cancelled" not in st.session_state:
    st.session_state["sos_cancelled"] = False
if "wa_location_result" not in st.session_state:
    st.session_state["wa_location_result"] = None


# --- TOP BRAND HEADER ---
st.markdown("""
<div class="brand-header">
    <div>
        <div class="brand-title">🛡️ SafeRide AI <span style="font-size:0.62rem; vertical-align:middle; background:#27364c; color:#9fb0c7; border-radius:4px; padding:3px 6px; letter-spacing:0;">v2.4-OPS</span></div>
        <div class="brand-subtitle">Emergency response command center</div>
    </div>
    <div>
        <div class="operator-meta"><span class="operator-avatar">RK</span><span><span class="live-pulse"></span><strong style="color:#ef4444; font-size:0.72rem; letter-spacing:0.5px;">LIVE DISPATCH</strong><br>Operator console</span></div>
    </div>
</div>
<div class="service-chips">
    <span class="service-chip">Emergency alerts</span>
    <span class="service-chip">Location tracking</span>
    <span class="service-chip">Rider translation</span>
</div>
""", unsafe_allow_html=True)

# --- FETCH INCIDENTS ---
incidents = db.get_all_incidents()

if not incidents:
    st.warning("No incidents found in database. Initializing sample data...")
    db.init_db(seed_sample_data=True)
    incidents = db.get_all_incidents()


# --- SIDEBAR: SIMULATOR & SELECTION ---
with st.sidebar:
    st.title("🎛️ Command & Sim")
    st.caption("Responder operations console")
    
    # Filter Status
    status_filter = st.selectbox(
        "Filter Incidents By Status",
        options=["All", "REPORTED", "DISPATCHED", "RESOLVED"],
        index=0
    )
    
    filtered_incidents = incidents
    if status_filter != "All":
        filtered_incidents = [inc for inc in incidents if inc["status"] == status_filter]
        if not filtered_incidents:
            filtered_incidents = incidents  # Fallback to all if none match

    # Incident Selection Dropdown
    incident_options = {
        f"{inc['incident_id']} ({inc['vehicle_type']} - {inc['confidence']}%)": inc['incident_id']
        for inc in filtered_incidents
    }
    
    selected_label = st.selectbox(
        "Active Emergency Incident:",
        options=list(incident_options.keys()),
        index=0
    )
    selected_id = incident_options[selected_label]
    current_incident = db.get_incident(selected_id)

    st.markdown("---")
    
    # --- MODULE 1: INTERACTIVE ACCIDENT DETECTION SIMULATOR ---
    st.subheader("⚡ Module 1: Crash Simulator")
    st.caption("Simulate real-world vehicle telematics to test the rule-based detection engine.")
    
    preset_choice = st.selectbox(
        "Load Telemetry Preset:",
        options=list(ad.SIMULATION_PRESETS.keys()),
        index=3  # Default to High-Speed Collision
    )
    preset_data = ad.SIMULATION_PRESETS[preset_choice]

    sim_vehicle = st.selectbox("Vehicle Type:", ["Motorcycle", "Scooter", "Electric Bike", "Car"], index=0)
    sim_speed_before = st.slider("Speed Before Impact (km/h)", 0.0, 120.0, float(preset_data["speed_before"]), 1.0)
    sim_speed_after = st.slider("Speed After Impact (km/h)", 0.0, 120.0, float(preset_data["speed_after"]), 1.0)
    sim_impact_g = st.slider("Impact Force (G-force)", 0.5, 10.0, float(preset_data["impact_force_g"]), 0.1)
    sim_tilt_deg = st.slider("Tilt Angle Deviation (°)", 0.0, 90.0, float(preset_data["tilt_angle_deg"]), 1.0)

    # Real-time evaluation preview
    sim_result = ad.detect_accident(
        speed_before=sim_speed_before,
        speed_after=sim_speed_after,
        impact_force_g=sim_impact_g,
        tilt_angle_deg=sim_tilt_deg,
        vehicle_type=sim_vehicle
    )

    score_color = "#ef4444" if sim_result["confidence"] >= 60 else "#10b981"
    st.markdown(f"""
        <div style="background:#111827; border:1px solid #374151; padding:10px; border-radius:8px; margin: 8px 0;">
            <div style="font-size:0.8rem; color:#9ca3af;">Simulated Confidence Score:</div>
            <div style="font-size:1.4rem; font-weight:700; color:{score_color};">{sim_result['confidence']}%</div>
            <div style="font-size:0.8rem; color:#cbd5e1;">Severity: <b>{sim_result['severity']}</b></div>
            <div style="font-size:0.75rem; color:#94a3b8; margin-top:4px;">
                Speed: {sim_result['scores']['speed_drop_score']} | Impact: {sim_result['scores']['impact_score']} | Tilt: {sim_result['scores']['tilt_score']}
            </div>
        </div>
    """, unsafe_allow_html=True)

    auto_timer_checkbox = st.checkbox("⏱️ Auto-engage 10s Emergency Location Message & Call on Crash", value=True)

    if st.button("🚨 Trigger New Incident to Database", use_container_width=True):
        # Hyderabad coordinate jitter for realistic simulation
        import random
        sim_lat = round(17.4400 + random.uniform(-0.04, 0.04), 5)
        sim_lng = round(78.3800 + random.uniform(-0.04, 0.04), 5)
        
        # Geocode the newly generated coordinates
        sim_geo = geo.reverse_geocode(sim_lat, sim_lng)
        sim_address = sim_geo.get("formatted_address", f"Cyberabad Area ({sim_lat}, {sim_lng})")

        sim_status = "NEED HELP" if sim_result["accident_detected"] else "I'M OK"
        sim_message = "బైక్ పడిపోయింది, దయచేసి అంబులెన్స్ పంపండి." if sim_result["accident_detected"] else "రైడ్ క్షేమంగా ఉంది."

        new_inc_id = db.create_incident(
            vehicle_type=sim_vehicle,
            latitude=sim_lat,
            longitude=sim_lng,
            confidence=sim_result["confidence"],
            rider_status=sim_status,
            language="Telugu",
            message=sim_message,
            status="REPORTED" if sim_result["accident_detected"] else "RESOLVED",
            address=sim_address
        )

        # If crash detected and auto-timer checked, engage the 10-second timer immediately!
        if sim_result["accident_detected"] and auto_timer_checkbox:
            st.session_state["sos_timer_active"] = True
            st.session_state["sos_incident_id"] = new_inc_id
            st.session_state["sos_cancelled"] = False
            st.session_state["sos_call_result"] = None
            st.session_state["wa_location_result"] = None

        st.success(f"Incident {new_inc_id} logged!")
        st.rerun()


# --- EMERGENCY 10-SECOND AUTO-DISPATCH COUNTDOWN BANNER (WHEN ACTIVE) ---
if st.session_state.get("sos_call_result") or st.session_state.get("wa_location_result"):
    call_info = st.session_state.get("sos_call_result")
    loc_info = st.session_state.get("wa_location_result")

    # Unified Dispatch Summary Banner
    st.markdown("""
    <div style="background:linear-gradient(135deg, #0c2340 0%, #102a45 100%); border:1.5px solid #3b82f6; border-radius:12px; padding:1.2rem; margin-bottom:1rem; box-shadow:0 8px 30px rgba(0,0,0,0.4);">
        <div style="font-size:1.1rem; font-weight:800; color:#93c5fd; display:flex; align-items:center; gap:8px; margin-bottom:0.6rem;">
            🚨 AUTOMATED 10-SECOND EMERGENCY DISPATCH REPORT
        </div>
    """, unsafe_allow_html=True)

    r_col1, r_col2 = st.columns(2)
    with r_col1:
        if call_info and call_info.get("success"):
            st.success(f"""
                📞 **Emergency Voice Call Dispatched!**
                - **Target:** `{call_info.get('to', notify.EMERGENCY_DISPATCH_PHONE)}`
                - **Status:** `{call_info.get('status', 'queued')}`
            """)
        elif call_info:
            st.error(f"""
                📞 **Voice Call Notice:** The emergency call could not be completed. Please use the manual contact option.
            """)

    with r_col2:
        if loc_info:
            loc_maps = loc_info.get('maps_link', '')
            loc_to = loc_info.get('to', notify.EMERGENCY_DISPATCH_PHONE)
            st.success(f"""
                📍 **Emergency Location Message Dispatched!**
                - **Recipient:** `{loc_to}`
                - **GPS Route:** [{loc_maps}]({loc_maps})
            """)
            if loc_info.get('wa_direct_url'):
                st.markdown(f"""
                <a href="{loc_info['wa_direct_url']}" target="_blank" class="whatsapp-direct-btn" style="margin-top:2px;">
                    💬 Open in WhatsApp (1-Click Instant View)
                </a>
                """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    if st.button("✕ Dismiss Dispatch Report", key="dismiss_sos_combined_alert"):
        st.session_state["sos_call_result"] = None
        st.session_state["wa_location_result"] = None
        st.rerun()

if st.session_state.get("sos_cancelled"):
    st.info("✋ **Emergency 10s Auto-Dispatch was cancelled by rider/responder (False Alarm).** Status marked as RESOLVED.")
    if st.button("Dismiss", key="dismiss_sos_cancel"):
        st.session_state["sos_cancelled"] = False
        st.rerun()

if st.session_state.get("sos_timer_active"):
    # Retrieve incident details for the active SOS timer
    sos_inc_id = st.session_state.get("sos_incident_id")
    sos_inc = db.get_incident(sos_inc_id) if sos_inc_id else current_incident
    if not sos_inc:
        sos_inc = current_incident
    
    sos_geo = geo.reverse_geocode(sos_inc["latitude"], sos_inc["longitude"])
    sos_addr = sos_inc.get("address") or sos_geo.get("formatted_address", "Cyberabad Incident Site")
    dest_phone = notify.EMERGENCY_DISPATCH_PHONE or "+917416960828"

    # Prominent Emergency SOS Header Box
    st.markdown(f"""
    <div class="sos-banner">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
            <div class="sos-title">
                <span class="live-pulse"></span> 🚨 CRASH DETECTED: 10-SECOND AUTOMATED LOCATION & VOICE DISPATCH
            </div>
            <div style="font-size:0.85rem; color:#fca5a5; font-weight:700; background:rgba(0,0,0,0.3); padding:4px 10px; border-radius:6px;">
                TARGET NUMBER: {dest_phone}
            </div>
        </div>
        <div style="font-size:0.92rem; color:#fecaca; margin-top:8px;">
            Accident Record: <b>{sos_inc['incident_id']}</b> ({sos_inc['vehicle_type']} • Confidence: <b>{sos_inc['confidence']}%</b>)
            <br>📍 Location: <b>{sos_addr}</b> (GPS: <code>{sos_inc['latitude']}, {sos_inc['longitude']}</code>)
            <br><span style="color:#ffffff; font-weight:600;">In 10 seconds, SafeRide AI will automatically send the exact GPS crash location and initiate an emergency voice call to {dest_phone}.</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Cancel and Instant Dispatch Action Controls
    col_ctrl1, col_ctrl2 = st.columns(2)
    with col_ctrl1:
        if st.button("✋ I'M OK / CANCEL DISPATCH (False Alarm)", key="btn_cancel_sos_active", type="secondary", use_container_width=True):
            st.session_state["sos_timer_active"] = False
            st.session_state["sos_cancelled"] = True
            st.session_state["sos_call_result"] = None
            st.session_state["wa_location_result"] = None
            db.update_incident(sos_inc["incident_id"], status="RESOLVED", rider_status="I'M OK")
            db.add_incident_message(
                sos_inc["incident_id"],
                "Rider",
                "I am OK. False alarm, emergency dispatch aborted.",
                "నేను బాగానే ఉన్నాను. తప్పుడు హెచ్చరిక, అత్యవసర డిస్పాచ్ రద్దు చేయబడింది."
            )
            st.rerun()

    with col_ctrl2:
        if st.button("⚡ SEND LOCATION & CALL NOW (Skip Timer)", key="btn_instant_sos_active", type="primary", use_container_width=True):
            with st.spinner("Dispatching emergency location message and voice call..."):
                call_res = notify.trigger_emergency_call(sos_inc, to_phone=dest_phone)
                sms_res = notify.send_emergency_sms(sos_inc, to_phone=dest_phone)
                wa_loc_res = notify.send_whatsapp_location(sos_inc, to_phone=dest_phone, address=sos_addr)
                
                db.update_incident(sos_inc["incident_id"], status="DISPATCHED")
                maps_link = wa_loc_res.get('maps_link', f"https://maps.google.com/?q={sos_inc['latitude']},{sos_inc['longitude']}")
                
                db.add_incident_message(
                    sos_inc["incident_id"],
                    "System",
                    f"⚡ Manual Emergency Dispatch: Location message and voice call sent to {dest_phone}. "
                    f"GPS: ({sos_inc['latitude']}, {sos_inc['longitude']}) | Map: {maps_link}"
                )
                st.session_state["sos_timer_active"] = False
                st.session_state["sos_call_result"] = call_res
                st.session_state["wa_location_result"] = wa_loc_res
                st.rerun()

    # Active Live Countdown Ticker
    timer_display = st.empty()
    bar_display = st.progress(1.0)

    for sec_left in range(10, 0, -1):
        timer_display.markdown(f"""
            <div style="background:#1e1b2e; border:2px solid #ef4444; border-radius:12px; padding:1.2rem; text-align:center; margin: 10px 0;">
                <div style="font-size:0.85rem; font-weight:700; color:#9ca3af; text-transform:uppercase; letter-spacing:1px;">
                    Automated Emergency Location & Call In:
                </div>
                <div class="sos-timer-number">{sec_left}s</div>
                <div style="font-size:0.85rem; color:#f87171;">
                    Dispatching GPS location message & voice call to <b>{dest_phone}</b>... Click Cancel if rider is safe.
                </div>
            </div>
        """, unsafe_allow_html=True)
        bar_display.progress(sec_left / 10.0)
        time.sleep(1)

    # 10 Seconds Completed -> Fire Automated Emergency Location & Call
    timer_display.markdown(f"""
        <div style="background:#1e1b2e; border:2px solid #10b981; border-radius:12px; padding:1.2rem; text-align:center; margin: 10px 0;">
            <div style="font-size:1.6rem; font-weight:800; color:#34d399;">🚨 10 SECONDS EXPIRED — SENDING LOCATION & EMERGENCY CALL!</div>
            <div style="font-size:0.9rem; color:#cbd5e1; margin-top:4px;">
                Dispatching GPS coordinates, Google Maps route, and automated voice call to {dest_phone}...
            </div>
        </div>
    """, unsafe_allow_html=True)
    bar_display.progress(0.0)

    # Execute automated location message, voice call, and SMS
    call_res = notify.trigger_emergency_call(sos_inc, to_phone=dest_phone)
    sms_res = notify.send_emergency_sms(sos_inc, to_phone=dest_phone)
    wa_loc_res = notify.send_whatsapp_location(sos_inc, to_phone=dest_phone, address=sos_addr)
    
    db.update_incident(sos_inc["incident_id"], status="DISPATCHED")
    maps_link = wa_loc_res.get('maps_link', f"https://maps.google.com/?q={sos_inc['latitude']},{sos_inc['longitude']}")
    
    db.add_incident_message(
        sos_inc["incident_id"],
        "System",
        f"🚨 10-Second Auto-Timer Expired: Emergency Location Message & Voice Call placed to {dest_phone}. "
        f"GPS: ({sos_inc['latitude']}, {sos_inc['longitude']}) | Map: {maps_link}"
    )
    st.session_state["sos_timer_active"] = False
    st.session_state["sos_call_result"] = call_res
    st.session_state["wa_location_result"] = wa_loc_res
    time.sleep(1.2)
    st.rerun()


# --- TOP KPI METRICS ROW ---
total_incidents = len(incidents)
active_emergencies = len([i for i in incidents if i["status"] in ["REPORTED", "DISPATCHED"] and i["rider_status"] in ["NEED HELP", "NO RESPONSE"]])
high_conf_count = len([i for i in incidents if i["confidence"] >= 70.0])
dispatched_count = len([i for i in incidents if i["status"] == "DISPATCHED"])

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_incidents}</div>
            <div class="metric-label">Total Incidents</div>
        </div>
    """, unsafe_allow_html=True)

with col_m2:
    st.markdown(f"""
        <div class="metric-card" style="border-color: #ef4444;">
            <div class="metric-value" style="color: #ef4444;">{active_emergencies}</div>
            <div class="metric-label">Active Emergencies</div>
        </div>
    """, unsafe_allow_html=True)

with col_m3:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #f59e0b;">{high_conf_count}</div>
            <div class="metric-label">High Confidence (>70%)</div>
        </div>
    """, unsafe_allow_html=True)

with col_m4:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #3b82f6;">{dispatched_count}</div>
            <div class="metric-label">Dispatched Teams</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 1.2rem;'></div>", unsafe_allow_html=True)


# --- MAIN 2-COLUMN LAYOUT: INCIDENT DOSSIER & MAP | COMMUNICATION HUB ---
left_col, right_col = st.columns([1.1, 0.9])

# Dynamic Reverse Geocoding for current incident
current_geo = geo.reverse_geocode(current_incident['latitude'], current_incident['longitude'])
resolved_address = current_incident.get('address') or current_geo.get('formatted_address', 'Address resolving...')

with left_col:
    st.markdown(f"""
        <div class="incident-shell">
            <span class="incident-shell-title">Incident Details {current_incident['incident_id']}</span>
            <span class="incident-shell-meta">Detected recently</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Status badges
    rider_status_class = "badge-need-help" if current_incident['rider_status'] == "NEED HELP" else (
        "badge-no-response" if current_incident['rider_status'] == "NO RESPONSE" else "badge-ok"
    )
    
    st.markdown(f"""
        <div style="display:flex; gap:10px; margin-bottom:12px; flex-wrap:wrap;">
            <span class="badge {rider_status_class}">Rider Status: {current_incident['rider_status']}</span>
            <span class="badge badge-dispatched">Workflow Status: {current_incident['status']}</span>
            <span class="badge" style="background:#374151; color:#e5e7eb;">Language: {current_incident['language']}</span>
        </div>
    """, unsafe_allow_html=True)

    # Resolved Physical Address Box
    st.markdown(f"""
        <div class="verified-address">
            <div style="font-size:0.75rem; font-weight:700; color:#38bdf8; text-transform:uppercase;">📍 Resolved Street Location:</div>
            <div style="font-size:0.95rem; font-weight:600; color:#f8fafc; margin-top:2px;">{resolved_address}</div>
        </div>
    """, unsafe_allow_html=True)

    # Details grid
    det_c1, det_c2, det_c3 = st.columns(3)
    with det_c1:
        st.write("**Vehicle Type:**")
        st.write(f"🛵 {current_incident['vehicle_type']}")
    with det_c2:
        st.write("**Detection Confidence:**")
        conf_val = current_incident['confidence']
        st.write(f"**{conf_val}%** ({ad.determine_severity(conf_val)})")
        st.progress(min(1.0, conf_val / 100.0))
    with det_c3:
        st.write("**Timestamp:**")
        st.write(f"⏱️ {current_incident['timestamp']}")

    st.markdown("---")
    
    # Status Triage Actions
    st.write("**🚨 Rapid Responder Actions:**")
    st_b1, st_b2, st_b3, st_b4 = st.columns(4)
    with st_b1:
        if st.button("🚨 Dispatch 108", use_container_width=True):
            db.update_incident(current_incident["incident_id"], status="DISPATCHED", address=resolved_address)
            
            # Send the emergency text alert to the dispatch phone
            sms_payload = {
                "incident_id": current_incident["incident_id"],
                "vehicle_type": current_incident["vehicle_type"],
                "confidence": current_incident["confidence"],
                "latitude": current_incident["latitude"],
                "longitude": current_incident["longitude"],
                "formatted_address": resolved_address,
                "rider_status": current_incident["rider_status"]
            }
            sms_result = notify.send_emergency_sms(sms_payload)
            
            # Add confirmation to live chat
            dispatch_text = "Help is on the way. Ambulance dispatched."
            dispatch_tel = tr.translate_to_telugu(dispatch_text)
            db.add_incident_message(
                current_incident["incident_id"],
                "Responder",
                dispatch_text,
                dispatch_tel
            )
            
            if sms_result.get("success"):
                st.success("Ambulance dispatched and emergency alert sent.")
            else:
                st.warning("Ambulance dispatched. The emergency alert could not be delivered.")
            st.rerun()

    with st_b2:
        if st.button("📞 Voice Call", use_container_width=True):
            call_payload = {
                "incident_id": current_incident["incident_id"],
                "vehicle_type": current_incident["vehicle_type"],
                "confidence": current_incident["confidence"],
                "city": current_geo.get("city", "Cyberabad Zone")
            }
            with st.spinner("Initiating emergency voice call..."):
                call_result = notify.trigger_emergency_call(call_payload)
            if call_result.get("success"):
                db.update_incident(current_incident["incident_id"], status="DISPATCHED")
                db.add_incident_message(
                    current_incident["incident_id"],
                    "System",
                    f"📞 Emergency voice call placed to {call_result.get('to', notify.EMERGENCY_DISPATCH_PHONE)}."
                )
            st.session_state["sos_call_result"] = call_result
            st.rerun()

    with st_b3:
        if st.button("⏱️ 10s Location SOS", use_container_width=True, help="Arm 10-second automatic emergency location message & voice call timer for this incident"):
            st.session_state["sos_timer_active"] = True
            st.session_state["sos_incident_id"] = current_incident["incident_id"]
            st.session_state["sos_cancelled"] = False
            st.session_state["sos_call_result"] = None
            st.session_state["wa_location_result"] = None
            st.rerun()

    with st_b4:
        if st.button("✅ Resolved", use_container_width=True):
            db.update_incident(current_incident["incident_id"], status="RESOLVED", rider_status="I'M OK")
            st.success("Incident marked resolved.")
            st.rerun()

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────
    # 🛰️ LIVE LOCATION TRACKER
    # ─────────────────────────────────────────────────────────────────────
    lat_c = current_incident['latitude']
    lon_c = current_incident['longitude']
    maps_link_c = f"https://maps.google.com/?q={lat_c},{lon_c}"

    st.markdown(f"""
    <div class="location-tracker-card">
        <div class="location-tracker-title">
            <span class="crash-marker-pulse"></span>
            🛰️ LIVE LOCATION TRACKER — Crash Site
        </div>
        <div style="display:flex; flex-wrap:wrap; gap:0; margin-bottom:0.6rem;">
            <span class="gps-coord-chip">📍 LAT: {lat_c}</span>
            <span class="gps-coord-chip">📍 LON: {lon_c}</span>
            <span class="gps-coord-chip" style="background:rgba(239,68,68,0.15); border-color:rgba(239,68,68,0.4); color:#fca5a5;">
                🚨 {current_geo.get('city', 'Incident Zone')} • {current_geo.get('state', 'Telangana')}
            </span>
        </div>
        <div style="font-size:0.85rem; color:#94a3b8; margin-bottom:0.5rem;">
            📮 <b style="color:#e2e8f0;">{resolved_address}</b>
        </div>
        <a href="{maps_link_c}" target="_blank"
           style="display:inline-flex; align-items:center; gap:6px; background:rgba(29,78,216,0.25);
                  border:1px solid rgba(59,130,246,0.5); color:#93c5fd; text-decoration:none;
                  padding:5px 12px; border-radius:8px; font-size:0.82rem; font-weight:700; margin-top:4px;">
            🔗 Open Live Google Maps Navigation
        </a>
    </div>
    """, unsafe_allow_html=True)

    # ─── Interactive location map ─────────────────────────────────────────
    st.markdown("""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:1rem; margin-bottom:0.5rem;">
        <span style="font-size:0.95rem; font-weight:700; color:#93c5fd; display:flex; align-items:center; gap:6px;">
            🗺️ Live Crash Location
        </span>
    </div>
    """, unsafe_allow_html=True)

    safe_address_js = (
        resolved_address
        .replace('\\', '\\\\')
        .replace("'", "\\'")
        .replace('"', '\\"')
        .replace('\n', ' ')
    )
    inc_id = current_incident.get('incident_id', 'INC-UNKNOWN')
    v_type = current_incident.get('vehicle_type', 'Unknown')
    conf = current_incident.get('confidence', 0)

    leaflet_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <!-- Map styles and scripts -->
        <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
        <style>
            html, body {{
                margin: 0;
                padding: 0;
                height: 100%;
                background: #0f172a;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }}
            #map {{
                width: 100%;
                height: 480px;
                border-radius: 12px;
                border: 1px solid rgba(59, 130, 246, 0.4);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
            }}
            .leaflet-popup-content-wrapper {{
                background: #0f172a;
                color: #f8fafc;
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 10px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.6);
            }}
            .leaflet-popup-tip {{
                background: #0f172a;
            }}
            .custom-crash-pin {{
                background: #ef4444;
                width: 36px;
                height: 36px;
                border-radius: 50%;
                border: 3px solid #ffffff;
                box-shadow: 0 0 20px rgba(239, 68, 68, 0.9), 0 0 40px rgba(239, 68, 68, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
                cursor: pointer;
            }}
        </style>
    </head>
    <body>
        <!-- 2. Create the container div -->
        <div id="map"></div>

        <!-- Initialize the map -->
        <script>
            // Center coordinates (latitude, longitude) and zoom level
            const map = L.map('map').setView([{lat_c}, {lon_c}], 15);

            // Add the map tile layer
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                maxZoom: 19,
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors'
            }}).addTo(map);

            // Crash perimeter buffer zone
            L.circle([{lat_c}, {lon_c}], {{
                color: '#ef4444',
                fillColor: '#ef4444',
                fillOpacity: 0.22,
                radius: 180
            }}).addTo(map);

            // Add custom crash marker
            const crashIcon = L.divIcon({{
                className: '',
                html: '<div class="custom-crash-pin">🚨</div>',
                iconSize: [36, 36],
                iconAnchor: [18, 18],
                popupAnchor: [0, -20]
            }});

            const marker = L.marker([{lat_c}, {lon_c}], {{ icon: crashIcon }}).addTo(map);

            // Bind detailed emergency popup
            const popupContent = `
                <div style="font-size: 13px; line-height: 1.4; padding: 2px;">
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:6px;">
                        <span style="font-size:16px;">🚨</span>
                        <strong style="color:#f87171; font-size:14px;">SafeRide Crash Site</strong>
                    </div>
                    <div style="color:#cbd5e1; font-size:12px; margin-bottom:3px;">
                        <b>Incident:</b> <span style="color:#93c5fd;">{inc_id}</span>
                    </div>
                    <div style="color:#cbd5e1; font-size:12px; margin-bottom:3px;">
                        <b>Vehicle:</b> {v_type} | <b>Confidence:</b> {conf}%
                    </div>
                    <div style="color:#94a3b8; font-size:11px; margin-top:5px; margin-bottom:8px; border-top:1px solid rgba(255,255,255,0.1); padding-top:4px;">
                        📮 {safe_address_js}
                    </div>
                    <a href="{maps_link_c}" target="_blank" 
                       style="display:inline-block; background:#2563eb; color:white; padding:5px 12px; border-radius:6px; text-decoration:none; font-weight:600; font-size:11px;">
                        📍 Open Google Maps Navigation
                    </a>
                </div>
            `;
            marker.bindPopup(popupContent).openPopup();
        </script>
    </body>
    </html>
    """

    components.html(leaflet_html, height=510)

    # ─── WhatsApp / SMS Location Alert Section ────────────────────────────
    st.markdown("""
    <div class="whatsapp-btn-container">
        <div class="whatsapp-btn-title">
            📲 Send Emergency Location to Ambulance / Responder via WhatsApp
        </div>
        <div style="font-size:0.8rem; color:#86efac; margin-bottom:0.4rem;">
            Dispatches exact GPS coordinates + Google Maps link + street address directly to the emergency responder or ambulance driver via WhatsApp.
        </div>
    </div>
    """, unsafe_allow_html=True)

    wa_phone_key = f"wa_phone_{current_incident['incident_id']}"
    wa_target_override = st.text_input(
        "📱 Emergency Contact Number (WhatsApp / Mobile):",
        value="",
        placeholder=f"Default: {notify.EMERGENCY_DISPATCH_PHONE}",
        key=wa_phone_key
    )

    active_target_phone = (wa_target_override.strip() or notify.EMERGENCY_DISPATCH_PHONE).strip()
    clean_target_digits = "".join(filter(str.isdigit, active_target_phone))
    if not clean_target_digits.startswith("91") and len(clean_target_digits) == 10:
        clean_target_digits = "91" + clean_target_digits

    # Pre-compose full emergency message for 1-Click WhatsApp Direct URL
    wa_direct_msg = (
        f"🚨 *SAFERIDE AI — EMERGENCY CRASH ALERT* 🚨\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 *Incident ID:* `{current_incident['incident_id']}`\n"
        f"🛵 *Vehicle:* {current_incident['vehicle_type']} | *Confidence:* {current_incident['confidence']}%\n"
        f"⚠️ *Rider Status:* {current_incident.get('rider_status', 'NEED HELP')}\n"
        f"📍 *Zone:* {current_geo.get('city', 'Incident Zone')}\n\n"
        f"🗺️ *GPS Coordinates:*\n"
        f"   Latitude: `{lat_c}`\n"
        f"   Longitude: `{lon_c}`\n\n"
        f"📮 *Crash Address:*\n{resolved_address}\n\n"
        f"🔗 *Live Navigation Map:*\n{maps_link_c}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚑 *Immediate 108 ambulance dispatch required.*\n"
        f"Please click the live navigation link above for turn-by-turn routing.\n\n"
        f"_— SafeRide AI Automated Emergency System_"
    )
    wa_direct_url = f"https://wa.me/{clean_target_digits}?text={urllib.parse.quote(wa_direct_msg)}"

    # Primary: 1-Click direct WhatsApp action
    st.markdown(f"""
    <a href="{wa_direct_url}" target="_blank" class="whatsapp-direct-btn">
        💬 Open & Send in WhatsApp (1-Click Instant Send)
    </a>
    """, unsafe_allow_html=True)

    # Secondary: Automated background dispatch
    if st.button("🤖 Send Alert Automatically", use_container_width=True,
                 key=f"btn_wa_loc_{current_incident['incident_id']}"):
        wa_payload = {
            "incident_id": current_incident["incident_id"],
            "vehicle_type": current_incident["vehicle_type"],
            "confidence": current_incident["confidence"],
            "latitude": lat_c,
            "longitude": lon_c,
            "rider_status": current_incident.get("rider_status", "NEED HELP"),
            "city": current_geo.get("city", "Incident Zone")
        }
        with st.spinner("📲 Dispatching location alert..."):
            wa_result = notify.send_whatsapp_location(
                wa_payload,
                to_phone=active_target_phone,
                address=resolved_address
            )
        if wa_result.get("success"):
            channel = wa_result.get("channel", "whatsapp")
            db.add_incident_message(
                current_incident["incident_id"],
                "System",
                f"📲 Location Alert dispatched via {channel.upper()} to {wa_result.get('to', active_target_phone)} "
                f"with GPS ({lat_c}, {lon_c}) and Google Maps link."
            )
        st.session_state["wa_location_result"] = wa_result
        st.rerun()

    # WhatsApp Result Banner
    if st.session_state.get("wa_location_result"):
        wa_res = st.session_state["wa_location_result"]
        channel = wa_res.get("channel", "whatsapp")

        if channel == "whatsapp":
            st.success(f"""
                💬 **Emergency alert sent via WhatsApp!**
                - **Sent To:** `{wa_res.get("to", active_target_phone)}`
                - **Status:** `{wa_res.get("status", "queued")}`
                - **GPS Link:** [{wa_res.get("maps_link", "")}]({wa_res.get("maps_link", "")})
            """)
        elif channel == "sms_fallback":
            st.warning(f"""
                📱 **WhatsApp Blocked — Sent via SMS Fallback!**
                - **Sent To:** `{wa_res.get("to", active_target_phone)}`
                - **Status:** Dispatched via verified SMS.
                - **GPS Link:** [{wa_res.get("maps_link", "")}]({wa_res.get("maps_link", "")})
            """)
        elif channel == "direct_whatsapp":
            st.info(f"""
                💬 **1-Click WhatsApp Alert Ready for Dispatch:**
                - **Target:** `{wa_res.get("to", active_target_phone)}`
                - **Note:** Click below to dispatch via WhatsApp Web or mobile app.
            """)
            st.markdown(f"""
            <a href="{wa_res.get('wa_direct_url', wa_direct_url)}" target="_blank" class="whatsapp-direct-btn">
                🚀 Click Here to Open & Send Emergency Alert in WhatsApp
            </a>
            """, unsafe_allow_html=True)
        elif not wa_res.get("success"):
            st.error(f"""
                ❌ **Automated Dispatch Notice:** Unable to send the alert automatically.
            """)
            st.markdown(f"""
            <a href="{wa_direct_url}" target="_blank" class="whatsapp-direct-btn">
                👉 Send Manually via WhatsApp (1-Click)
            </a>
            """, unsafe_allow_html=True)

        if st.button("✕ Dismiss", key=f"dismiss_wa_{current_incident['incident_id']}"):
            st.session_state["wa_location_result"] = None
            st.rerun()


with right_col:
    st.markdown("<div class='incident-shell-title' style='margin-bottom:0.7rem;'>Recent Incident Log <span style='float:right; color:#38bdf8; font-size:0.72rem;'>View history</span></div>", unsafe_allow_html=True)
    recent_incidents = [inc for inc in incidents if inc["incident_id"] != current_incident["incident_id"]][:4]
    for recent in recent_incidents:
        recent_status = recent.get("status", "REPORTED")
        badge_class = "badge-resolved" if recent_status == "RESOLVED" else (
            "badge-warning" if recent_status == "REPORTED" else "badge-critical"
        )
        recent_copy = "Emergency incident requires responder attention." if recent_status != "RESOLVED" else "Incident closed after responder review."
        st.markdown(f"""
            <div class="recent-log-card">
                <div class="recent-log-id">{recent['incident_id']}
                    <span class="recent-log-badge {badge_class}">{recent_status}</span>
                </div>
                <div class="recent-log-time">{recent.get('timestamp', '')[-8:]}</div>
                <div class="recent-log-copy">{recent_copy}</div>
            </div>
        """, unsafe_allow_html=True)

    st.subheader("💬 Multilingual Emergency Chat Hub")
    st.caption("Bidirectional Telugu ↔ English neural translation stream between Rider and Responder.")

    # Fetch message thread
    messages = db.get_incident_messages(current_incident["incident_id"])

    # Scrollable chat display area
    chat_container = st.container(height=380)
    with chat_container:
        if not messages:
            st.info("No messages in thread yet.")
        else:
            for msg in messages:
                sender = msg["sender"]
                trans_display = msg.get("translated_text")
                # If translation was empty, translate dynamically on demand
                if not trans_display:
                    if sender == "Rider":
                        trans_display = tr.translate_to_english(msg['original_text'])
                    else:
                        trans_display = tr.translate_to_telugu(msg['original_text'])

                if sender == "Rider":
                    st.markdown(f"""
                        <div class="chat-bubble-rider">
                            <div class="chat-sender" style="color:#f87171;">👤 Rider (Telugu)</div>
                            <div class="chat-original">{msg['original_text']}</div>
                            <div class="chat-translated">🌐 Translation: {trans_display}</div>
                            <div class="chat-timestamp">{msg['timestamp']}</div>
                        </div>
                    """, unsafe_allow_html=True)
                elif sender == "Responder":
                    st.markdown(f"""
                        <div class="chat-bubble-responder">
                            <div class="chat-sender" style="color:#60a5fa;">🏥 Responder (English)</div>
                            <div class="chat-original">{msg['original_text']}</div>
                            <div class="chat-translated">🌐 Telugu Translation: {trans_display}</div>
                            <div class="chat-timestamp">{msg['timestamp']}</div>
                        </div>
                    """, unsafe_allow_html=True)
                else:  # System
                    system_text = msg['original_text']
                    if any(detail in system_text for detail in ("Twilio", "API", "SID:")):
                        system_text = "Emergency dispatch event recorded."
                    st.markdown(f"""
                        <div style="background:#182234; border:1px dashed #475569; border-radius:8px; padding:8px; margin-bottom:8px; text-align:center;">
                            <div style="font-size:0.75rem; color:#94a3b8;">⚙️ SYSTEM EVENT</div>
                            <div style="font-size:0.85rem; color:#e2e8f0;">{system_text}</div>
                            <div style="font-size:0.7rem; color:#64748b;">{msg['timestamp']}</div>
                        </div>
                    """, unsafe_allow_html=True)

    # Quick Reply Presets
    st.write("**Quick Responder Phrases (Neural Auto-Translation to Telugu):**")
    preset_col1, preset_col2 = st.columns(2)
    with preset_col1:
        if st.button("🚑 Ambulance 3 mins away", use_container_width=True):
            eng_text = "Ambulance is 3 minutes away from your location."
            tel_text = tr.translate_to_telugu(eng_text)
            db.add_incident_message(current_incident["incident_id"], "Responder", eng_text, tel_text)
            st.rerun()
    with preset_col2:
        if st.button("🧘 Stay calm, keep helmet on", use_container_width=True):
            eng_text = "Please stay calm and do not remove your helmet."
            tel_text = tr.translate_to_telugu(eng_text)
            db.add_incident_message(current_incident["incident_id"], "Responder", eng_text, tel_text)
            st.rerun()

    # Custom Responder Reply Input with Dynamic Translation
    with st.form(key=f"reply_form_{current_incident['incident_id']}", clear_on_submit=True):
        custom_reply = st.text_input("Type responder message (English):", placeholder="e.g. Can you move your arms? Medical team is near.")
        submit_btn = st.form_submit_button("Send Response to Rider", use_container_width=True)
        
        if submit_btn and custom_reply.strip():
            with st.spinner("Translating to Telugu..."):
                trans_tel = tr.translate_to_telugu(custom_reply.strip())
                db.add_incident_message(
                    current_incident["incident_id"],
                    "Responder",
                    custom_reply.strip(),
                    trans_tel
                )
            st.success("Message sent and dynamically translated to rider in Telugu!")
            st.rerun()
