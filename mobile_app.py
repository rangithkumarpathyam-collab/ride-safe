"""SafeRide rider companion: a mobile-first Streamlit safety screen."""

import streamlit as st

import accident_detection as ad
import database as db


st.set_page_config(
    page_title="SafeRide Rider",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
        :root { --ink: #f8fafc; --muted: #9aa9bf; --panel: #111b2d; --line: rgba(148,163,184,.2); }
        html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
        [data-testid="stAppViewContainer"] {
            background: radial-gradient(circle at 50% -10%, rgba(37,99,235,.24), transparent 28rem), #070c15;
        }
        [data-testid="stMainBlockContainer"] { max-width: 560px; padding: 1rem .85rem 3rem; }
        .rider-header { display:flex; justify-content:space-between; align-items:center; gap:1rem; margin-bottom:1.2rem; }
        .brand { color:var(--ink); font-size:1.35rem; font-weight:800; letter-spacing:-.03em; }
        .brand small { display:block; color:var(--muted); font-size:.75rem; font-weight:500; letter-spacing:0; margin-top:.2rem; }
        .shield { display:grid; place-items:center; width:3rem; height:3rem; border-radius:14px; background:linear-gradient(145deg,#2563eb,#38bdf8); font-size:1.45rem; box-shadow:0 10px 28px rgba(37,99,235,.28); }
        .status-card, .sensor-card, .help-card { background:rgba(17,27,45,.86); border:1px solid var(--line); border-radius:18px; padding:1rem; margin-bottom:.85rem; }
        .status-card { display:flex; align-items:center; gap:.75rem; }
        .status-dot { width:10px; height:10px; background:#22c55e; border-radius:50%; box-shadow:0 0 14px #22c55e; }
        .status-title { color:var(--ink); font-size:.9rem; font-weight:700; }
        .status-copy { color:var(--muted); font-size:.75rem; margin-top:.15rem; }
        .section-label { color:#7dd3fc; font-size:.72rem; text-transform:uppercase; letter-spacing:.12em; font-weight:800; margin:1.3rem 0 .65rem; }
        .score { text-align:center; padding:1rem .5rem 1.15rem; }
        .score-number { color:#f8fafc; font-size:3.7rem; line-height:1; font-weight:800; letter-spacing:-.07em; }
        .score-caption { color:var(--muted); font-size:.76rem; margin-top:.45rem; }
        [data-testid="stButton"] button { min-height:3.1rem; border-radius:12px; font-weight:800; }
        .help-card { border-color:rgba(239,68,68,.5); background:linear-gradient(145deg,rgba(127,29,29,.35),rgba(17,27,45,.9)); }
        .mobile-stats { display:grid; grid-template-columns:repeat(3, 1fr); gap:.5rem; margin-bottom:.85rem; }
        .mobile-stat { background:#172438; border:1px solid rgba(148,163,184,.16); border-radius:12px; padding:.7rem .3rem; text-align:center; }
        .mobile-stat-label { color:#91a2bb; font-size:.62rem; font-weight:800; letter-spacing:.08em; }
        .mobile-stat-value { color:#38bdf8; font-size:1rem; font-weight:800; margin-top:.22rem; }
        .bottom-nav { display:grid; grid-template-columns:repeat(5, 1fr); gap:.25rem; border-top:1px solid var(--line); margin-top:1.3rem; padding-top:.85rem; text-align:center; }
        .bottom-nav-item { color:#71819a; font-size:.63rem; font-weight:700; }
        .bottom-nav-item.active { color:#38bdf8; }
        @media (max-width: 420px) { .brand { font-size:1.15rem; } .score-number { font-size:3.2rem; } }
    </style>
    """,
    unsafe_allow_html=True,
)

db.init_db()
if "mobile_result" not in st.session_state:
    st.session_state.mobile_result = None
if "mobile_incident_id" not in st.session_state:
    st.session_state.mobile_incident_id = None
if "mobile_section" not in st.session_state:
    st.session_state.mobile_section = "Home"

st.markdown(
    """
    <div class="rider-header">
        <div class="brand">SafeRide Rider<small>Personal safety monitor</small></div>
        <div class="shield">🛡️</div>
    </div>
    <div class="status-card">
        <div class="status-dot"></div>
        <div><div class="status-title">Safety monitoring ready</div><div class="status-copy">Check your ride telemetry before sending an alert.</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="section-label">Current ride</div>', unsafe_allow_html=True)
vehicle_type = st.selectbox("Vehicle", ["Motorcycle", "Scooter", "Electric Bike", "Car"], label_visibility="collapsed")

st.markdown(
    """
    <div class="mobile-stats">
        <div class="mobile-stat"><div class="mobile-stat-label">TRIPS</div><div class="mobile-stat-value">12</div></div>
        <div class="mobile-stat"><div class="mobile-stat-label">SAFE DAYS</div><div class="mobile-stat-value">28</div></div>
        <div class="mobile-stat"><div class="mobile-stat-label">STATUS</div><div class="mobile-stat-value" style="color:#4ade80;">READY</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

sensor_col1, sensor_col2 = st.columns(2)
with sensor_col1:
    speed_before = st.number_input("Speed before impact (km/h)", min_value=0.0, max_value=240.0, value=45.0, step=1.0)
    impact_force = st.number_input("Impact force (G)", min_value=0.0, max_value=20.0, value=1.2, step=0.1)
with sensor_col2:
    speed_after = st.number_input("Speed after impact (km/h)", min_value=0.0, max_value=240.0, value=40.0, step=1.0)
    tilt_angle = st.number_input("Tilt angle (degrees)", min_value=0.0, max_value=180.0, value=10.0, step=1.0)

try:
    sample = {
        "speed_before": speed_before,
        "speed_after": speed_after,
        "impact_force_g": impact_force,
        "tilt_angle_deg": tilt_angle,
    }
    preview = ad.detect_accident_window([sample, sample], vehicle_type=vehicle_type)
except ValueError as error:
    preview = None
    st.error(str(error))

if preview:
    score_color = "#f87171" if preview["accident_detected"] else "#4ade80"
    st.markdown(
        f"""
        <div class="sensor-card score">
            <div class="score-number" style="color:{score_color};">{preview['confidence']}%</div>
            <div class="score-caption">{preview['severity']} · {preview['confirmation_reason']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="section-label">Your location</div>', unsafe_allow_html=True)
location_col1, location_col2 = st.columns(2)
with location_col1:
    latitude = st.number_input("Latitude", value=17.4435, format="%.5f")
with location_col2:
    longitude = st.number_input("Longitude", value=78.3772, format="%.5f")

st.markdown('<div class="section-label">Emergency action</div>', unsafe_allow_html=True)
if preview and preview["accident_detected"]:
    st.markdown(
        '<div class="help-card"><div class="status-title">Possible crash detected</div><div class="status-copy">Stay calm. Send your location to the response team if you need help.</div></div>',
        unsafe_allow_html=True,
    )

if st.button("I NEED HELP NOW", type="primary", use_container_width=True):
    message = "Possible crash detected. Please send help to my location."
    incident_id = db.create_incident(
        vehicle_type=vehicle_type,
        latitude=latitude,
        longitude=longitude,
        confidence=preview["confidence"] if preview else 0.0,
        rider_status="NEED HELP",
        language="English",
        message=message,
        status="REPORTED",
    )
    st.session_state.mobile_incident_id = incident_id
    st.success(f"Help request sent: {incident_id}")

if st.button("I'm OK", use_container_width=True):
    st.session_state.mobile_result = None
    st.info("No alert was sent. Ride safely.")

if st.session_state.mobile_incident_id:
    st.caption(f"Active request: {st.session_state.mobile_incident_id}")

section_columns = st.columns(5)
for column, section_name, icon in zip(
    section_columns,
    ["Home", "Alerts", "Map", "Settings", "Profile"],
    ["⌂", "!", "⌖", "⚙", "●"],
):
    with column:
        if st.button(f"{icon}\n{section_name}", key=f"mobile_nav_{section_name}", use_container_width=True):
            st.session_state.mobile_section = section_name
            st.rerun()

if st.session_state.mobile_section == "Alerts":
    if st.session_state.mobile_incident_id:
        st.warning(f"Active emergency request: {st.session_state.mobile_incident_id}")
    else:
        st.info("No active alerts. SafeRide monitoring is ready.")
elif st.session_state.mobile_section == "Map":
    st.markdown(
        f"**Current position**  \n`{latitude:.5f}, {longitude:.5f}`"
    )
    st.link_button("Open navigation", f"https://maps.google.com/?q={latitude},{longitude}", use_container_width=True)
elif st.session_state.mobile_section == "Settings":
    st.checkbox("Continuous monitoring", value=True, disabled=True)
    st.checkbox("Location sharing during an alert", value=True, disabled=True)
elif st.session_state.mobile_section == "Profile":
    st.info("Rider profile\n\nMonitoring status: Ready\nVehicle: " + vehicle_type)

st.markdown(
    """
    <div style="height:.25rem"></div>
    """,
    unsafe_allow_html=True,
)
