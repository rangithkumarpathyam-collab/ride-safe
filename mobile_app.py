"""
SafeRide AI - Mobile Companion (Glass UI/UX Edition)
---------------------------------------------------
Full-featured mobile response console matching the glassmorphic UI/UX mockup:
  - Splash / Operator Access Portal
  - ⌂ Home: 2x2 Glass Metric Grid & Recent Incidents Feed
  - ! Alerts: Incident Details, Telemetry Vectors, Verified Address, Action Timeline
  - ⌖ Map: Dark Radar Scanner & Active GIS Incident Tracking
  - ⚡ Sim: Interactive Crash Telemetry Simulator & AI Confidence Estimator
  - ● Profile: Dispatcher Stats, Notification Sounds, & Twilio Automations
  - 🚨 10-Second SOS Emergency Countdown Timer with automated Twilio Voice Dispatch
"""

import time
import urllib.parse
from datetime import datetime
import streamlit as st

import accident_detection as ad
import database as db
import geocoding as geo
import notifications as notify

st.set_page_config(
    page_title="SafeRide AI Mobile",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# ULTRA-PREMIUM GLASSMORPHIC CSS DESIGN SYSTEM
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');
        
        :root {
            --bg-dark: #070c16;
            --glass-card: rgba(15, 23, 42, 0.72);
            --glass-card-hover: rgba(22, 34, 60, 0.85);
            --glass-border: rgba(255, 255, 255, 0.08);
            --glass-border-light: rgba(255, 255, 255, 0.15);
            --accent-cyan: #38bdf8;
            --accent-emerald: #34d399;
            --accent-red: #ef4444;
            --accent-amber: #f59e0b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif;
            letter-spacing: -0.01em;
        }

        [data-testid="stAppViewContainer"] {
            background: radial-gradient(circle at 50% 0%, rgba(30, 58, 138, 0.32) 0%, rgba(7, 12, 22, 0.98) 60%), #070c16;
            color: var(--text-main);
        }

        [data-testid="stMainBlockContainer"] {
            max-width: 480px;
            padding: 0.75rem 0.85rem 5rem;
            margin: 0 auto;
        }

        /* Hide Streamlit default header/footer */
        #MainMenu, header, footer { visibility: hidden; height: 0; }

        /* Glassmorphic Panel Core */
        .glass-card {
            background: var(--glass-card);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.42), inset 0 1px 0 rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 1.15rem;
            margin-bottom: 0.9rem;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .glass-card:hover {
            border-color: var(--glass-border-light);
        }

        /* Top Header Operator Profile */
        .op-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.25rem 0.2rem 0.85rem;
        }
        .op-left {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .op-avatar {
            width: 42px;
            height: 42px;
            border-radius: 50%;
            background: linear-gradient(135deg, #2563eb, #38bdf8);
            display: grid;
            place-items: center;
            font-size: 1.1rem;
            box-shadow: 0 0 18px rgba(37, 99, 235, 0.45);
            border: 2px solid rgba(255, 255, 255, 0.15);
        }
        .op-title {
            font-size: 0.95rem;
            font-weight: 800;
            color: var(--text-main);
            margin: 0;
            line-height: 1.2;
        }
        .op-loc {
            font-size: 0.72rem;
            color: var(--text-muted);
            margin-top: 2px;
        }
        .bell-badge {
            position: relative;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--glass-border);
            display: grid;
            place-items: center;
            font-size: 1rem;
            color: #cbd5e1;
        }
        .bell-dot {
            position: absolute;
            top: 7px;
            right: 7px;
            width: 8px;
            height: 8px;
            background: #ef4444;
            border-radius: 50%;
            box-shadow: 0 0 8px #ef4444;
            animation: pulse 1.6s infinite;
        }

        /* System Active Pill */
        .system-pill {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 0.35rem 0.85rem;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.35);
            border-radius: 999px;
            font-size: 0.68rem;
            font-weight: 800;
            color: #34d399;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.85rem;
        }
        .system-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #22c55e;
            box-shadow: 0 0 10px #22c55e;
        }

        /* 2x2 Metric Grid */
        .metric-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.65rem;
            margin-bottom: 1rem;
        }
        .metric-tile {
            background: rgba(15, 23, 42, 0.75);
            border: 1px solid var(--glass-border);
            backdrop-filter: blur(20px);
            border-radius: 16px;
            padding: 0.85rem 0.75rem;
            text-align: left;
            position: relative;
            overflow: hidden;
        }
        .metric-label {
            font-size: 0.65rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--text-muted);
        }
        .metric-num {
            font-size: 1.65rem;
            font-weight: 800;
            line-height: 1.15;
            margin-top: 0.35rem;
        }

        /* Incident List Item */
        .incident-card {
            background: rgba(15, 23, 42, 0.65);
            border: 1px solid var(--glass-border);
            backdrop-filter: blur(16px);
            border-radius: 16px;
            padding: 0.85rem 1rem;
            margin-bottom: 0.6rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }
        .incident-card:hover {
            transform: translateY(-2px);
            border-color: rgba(56, 189, 248, 0.4);
        }
        .inc-id {
            font-size: 0.88rem;
            font-weight: 800;
            color: var(--text-main);
        }
        .inc-loc {
            font-size: 0.74rem;
            color: var(--text-muted);
            margin-top: 2px;
        }
        .badge-pill {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.64rem;
            font-weight: 800;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        .badge-critical {
            background: rgba(239, 68, 68, 0.18);
            border: 1px solid rgba(239, 68, 68, 0.45);
            color: #f87171;
        }
        .badge-warning {
            background: rgba(245, 158, 11, 0.18);
            border: 1px solid rgba(245, 158, 11, 0.45);
            color: #fbbf24;
        }
        .badge-resolved {
            background: rgba(16, 185, 129, 0.18);
            border: 1px solid rgba(16, 185, 129, 0.45);
            color: #34d399;
        }

        /* Glowing Radar View */
        .radar-box {
            position: relative;
            width: 100%;
            height: 180px;
            border-radius: 16px;
            background: radial-gradient(circle at center, rgba(239, 68, 68, 0.25) 0%, rgba(15, 23, 42, 0.95) 70%);
            border: 1px solid rgba(239, 68, 68, 0.35);
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0.75rem 0;
            box-shadow: 0 0 25px rgba(239, 68, 68, 0.2);
        }
        .radar-ring-1 {
            position: absolute;
            width: 80px;
            height: 80px;
            border-radius: 50%;
            border: 1.5px solid rgba(239, 68, 68, 0.65);
            animation: radar-wave 2.2s infinite;
        }
        .radar-ring-2 {
            position: absolute;
            width: 130px;
            height: 130px;
            border-radius: 50%;
            border: 1.5px solid rgba(239, 68, 68, 0.45);
            animation: radar-wave 2.2s infinite 0.7s;
        }
        .radar-core {
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: #ef4444;
            box-shadow: 0 0 16px #ef4444;
            z-index: 2;
        }
        @keyframes radar-wave {
            0% { transform: scale(0.6); opacity: 0.9; }
            100% { transform: scale(1.6); opacity: 0; }
        }
        @keyframes pulse {
            0% { transform: scale(0.9); opacity: 0.8; }
            50% { transform: scale(1.2); opacity: 1; }
            100% { transform: scale(0.9); opacity: 0.8; }
        }

        /* Telemetry 3-Tile Row */
        .telemetry-row {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 0.45rem;
            margin: 0.85rem 0;
        }
        .telemetry-tile {
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--glass-border);
            border-radius: 12px;
            padding: 0.65rem 0.45rem;
            text-align: center;
        }
        .telemetry-label {
            font-size: 0.6rem;
            font-weight: 800;
            color: var(--text-muted);
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }
        .telemetry-val {
            font-size: 1.05rem;
            font-weight: 800;
            color: #38bdf8;
            margin-top: 2px;
        }

        /* 10-Second SOS Banner */
        .sos-timer-card {
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.24) 0%, rgba(153, 27, 27, 0.4) 100%);
            border: 2px solid #ef4444;
            border-radius: 20px;
            padding: 1.35rem 1.1rem;
            text-align: center;
            margin-bottom: 1.2rem;
            box-shadow: 0 0 32px rgba(239, 68, 68, 0.45);
            animation: pulse-border 1.8s infinite;
        }
        @keyframes pulse-border {
            0% { box-shadow: 0 0 16px rgba(239, 68, 68, 0.3); }
            50% { box-shadow: 0 0 36px rgba(239, 68, 68, 0.65); }
            100% { box-shadow: 0 0 16px rgba(239, 68, 68, 0.3); }
        }
        .sos-number {
            font-size: 4rem;
            font-weight: 900;
            color: #ef4444;
            line-height: 1;
            margin: 0.4rem 0 0.1rem;
            text-shadow: 0 0 24px rgba(239, 68, 68, 0.8);
        }

        /* Buttons */
        [data-testid="stButton"] button {
            border-radius: 14px;
            font-weight: 800;
            font-size: 0.85rem;
            letter-spacing: 0.02em;
            transition: transform 0.16s ease, box-shadow 0.16s ease;
            min-height: 2.85rem;
        }
        [data-testid="stButton"] button:hover {
            transform: translateY(-2px);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# DATABASE & SESSION INITIALIZATION
# -----------------------------------------------------------------------------
db.init_db(seed_sample_data=True)

if "mobile_section" not in st.session_state:
    st.session_state.mobile_section = "Home"
if "selected_incident_id" not in st.session_state:
    st.session_state.selected_incident_id = None
if "mobile_timer_active" not in st.session_state:
    st.session_state.mobile_timer_active = False
if "mobile_timer_start" not in st.session_state:
    st.session_state.mobile_timer_start = None
if "mobile_timer_cancelled" not in st.session_state:
    st.session_state.mobile_timer_cancelled = False
if "last_call_dispatched" not in st.session_state:
    st.session_state.last_call_dispatched = None
if "is_operator_login_view" not in st.session_state:
    st.session_state.is_operator_login_view = False

# Fetch all incidents from SQLite
all_incidents = db.get_all_incidents()
if not all_incidents:
    db.init_db(seed_sample_data=True)
    all_incidents = db.get_all_incidents()

active_count = len([i for i in all_incidents if i["status"] in ("REPORTED", "DISPATCHED")])
avg_conf = int(sum([i["confidence"] for i in all_incidents]) / max(len(all_incidents), 1))

# Default active incident
if not st.session_state.selected_incident_id and all_incidents:
    st.session_state.selected_incident_id = all_incidents[0]["incident_id"]

# -----------------------------------------------------------------------------
# 10-SECOND EMERGENCY SOS COUNTDOWN BANNER (GLOBAL OVERLAY)
# -----------------------------------------------------------------------------
if st.session_state.mobile_timer_active:
    elapsed = int(time.time() - st.session_state.mobile_timer_start)
    seconds_left = max(0, 10 - elapsed)

    trigger_score = st.session_state.get("auto_triggered_by_score")
    alert_badge = (
        f"● ABNORMAL SAFETY EVALUATION SCORE DETECTED ({trigger_score}%)"
        if trigger_score
        else "● CRASH SENSORS TRIGGERED"
    )

    st.markdown(
        f"""
        <div class="sos-timer-card">
            <div style="font-size:0.75rem; font-weight:800; color:#fca5a5; letter-spacing:0.12em; text-transform:uppercase;">
                {alert_badge}
            </div>
            <div style="font-size:1.15rem; font-weight:900; color:#ffffff; margin-top:2px;">
                AUTOMATIC EMERGENCY SOS ACTIVATED
            </div>
            <div class="sos-number">{seconds_left}s</div>
            <div style="font-size:0.75rem; color:#fca5a5; margin-bottom:0.75rem;">
                Safety confidence evaluation score was <b>NOT NORMAL</b>. Automated Twilio voice call & location dispatch to <b>{notify.EMERGENCY_DISPATCH_PHONE}</b> in:
            </div>
            <div style="background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:6px; font-size:0.75rem; color:#67e8f9; font-weight:700;">
                📍 Active GPS: 17.4435, 78.3772 · MG Road Corridor
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_cancel, col_now = st.columns(2)
    with col_cancel:
        if st.button("✋ I'M OK (CANCEL)", key="cancel_sos_timer", use_container_width=True):
            st.session_state.mobile_timer_active = False
            st.session_state.mobile_timer_start = None
            st.session_state.mobile_timer_cancelled = True
            st.session_state.score_dismissed = True
            st.rerun()
    with col_now:
        if st.button("⚡ DISPATCH NOW", key="force_sos_timer", type="primary", use_container_width=True):
            seconds_left = 0

    if seconds_left > 0:
        time.sleep(1)
        st.rerun()
    else:
        # 10-Second Timer Finished -> Trigger Twilio Voice Call & Location Message
        st.session_state.mobile_timer_active = False
        st.session_state.mobile_timer_start = None

        target_phone = notify.EMERGENCY_DISPATCH_PHONE
        inc_id = db.create_incident(
            vehicle_type="Motorcycle",
            latitude=17.4435,
            longitude=78.3772,
            confidence=89.0,
            rider_status="NEED HELP",
            language="English",
            message="10-Second timer expired. Emergency auto-dispatch triggered from mobile app.",
            status="REPORTED",
            address="12 MG Road, Bengaluru",
        )
        st.session_state.selected_incident_id = inc_id

        # Trigger Twilio Voice Call
        call_res = notify.trigger_emergency_call(
            {
                "incident_id": inc_id,
                "vehicle_type": "Motorcycle",
                "confidence": 89.0,
                "city": "12 MG Road, Bengaluru",
            },
            to_phone=target_phone,
        )
        notify.send_emergency_sms(
            {"incident_id": inc_id, "vehicle_type": "Motorcycle", "confidence": 89.0, "latitude": 17.4435, "longitude": 78.3772},
            to_phone=target_phone,
        )
        notify.send_whatsapp_location(
            {"incident_id": inc_id, "vehicle_type": "Motorcycle", "confidence": 89.0, "latitude": 17.4435, "longitude": 78.3772},
            to_phone=target_phone,
            address="12 MG Road, Bengaluru",
        )

        st.session_state.last_call_dispatched = {
            "incident_id": inc_id,
            "call_sid": call_res.get("sid", "Queued"),
            "target": target_phone,
            "call_success": call_res.get("success", False),
            "error": call_res.get("error"),
        }
        st.rerun()

# -----------------------------------------------------------------------------
# SCREEN 1: OPERATOR ACCESS PORTAL (LOGIN / SPLASH VIEW)
# -----------------------------------------------------------------------------
if st.session_state.is_operator_login_view:
    st.markdown(
        """
        <div style="text-align:center; padding: 2.2rem 0.5rem 1rem;">
            <div style="width:78px; height:78px; border-radius:24px; background:linear-gradient(135deg, #1e3a8a, #0284c7); margin:0 auto 1.2rem; display:grid; place-items:center; font-size:2.2rem; box-shadow:0 0 35px rgba(2,132,199,0.4); border:1.5px solid rgba(255,255,255,0.18);">
                🛡️
            </div>
            <div style="font-size:1.85rem; font-weight:900; color:#f8fafc; letter-spacing:-0.03em; margin-bottom:4px;">
                SafeRide AI
            </div>
            <div style="font-size:0.8rem; color:#94a3b8; max-width:280px; margin:0 auto 1.8rem; line-height:1.4;">
                Real-time crash detection & emergency response platform
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown(
            """
            <div class="glass-card" style="padding:1.4rem;">
                <div style="font-size:0.68rem; font-weight:800; color:#7dd3fc; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:8px;">
                    OPERATOR ACCESS PORTAL
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.text_input("Enter mobile number", value="+91 74169 60828", label_visibility="collapsed")
        
        if st.button("Operator Log In", type="primary", use_container_width=True):
            st.session_state.is_operator_login_view = False
            st.rerun()

    st.markdown("<div style='height: 3rem;'></div>", unsafe_allow_html=True)
    if st.button("🚨 BYPASS TO SOS", use_container_width=True):
        st.session_state.is_operator_login_view = False
        st.session_state.mobile_timer_active = True
        st.session_state.mobile_timer_start = time.time()
        st.session_state.mobile_timer_cancelled = False
        st.rerun()

    st.stop()

# -----------------------------------------------------------------------------
# MAIN APP HEADER: DISPATCHER PROFILE + ACTIVE SYSTEM STRIP
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class="op-header">
        <div class="op-left">
            <div class="op-avatar">👮‍♂️</div>
            <div>
                <div class="op-title">R. Rajan</div>
                <div class="op-loc">Bangalore, IN · Station BLR-01</div>
            </div>
        </div>
        <div class="bell-badge">
            🔔<div class="bell-dot"></div>
        </div>
    </div>
    <div class="system-pill">
        <div class="system-dot"></div>
        SYSTEM ACTIVE • 24/7 MONITORING
    </div>
    """,
    unsafe_allow_html=True,
)

# Flash active call banner if recently dispatched
if st.session_state.last_call_dispatched:
    cinfo = st.session_state.last_call_dispatched
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg, rgba(16,185,129,0.18) 0%, rgba(5,150,105,0.28) 100%); border:1px solid #10b981; border-radius:14px; padding:0.85rem; margin-bottom:0.85rem;">
            <div style="font-size:0.88rem; font-weight:800; color:#34d399;">
                📞 Automated Twilio Call Dispatched to {cinfo['target']}
            </div>
            <div style="font-size:0.72rem; color:#cbd5e1; margin-top:2px;">
                Call Reference SID: <code>{cinfo['call_sid']}</code> · Responders Notified
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# TAB 1: ⌂ HOME (DASHBOARD)
# -----------------------------------------------------------------------------
if st.session_state.mobile_section == "Home":
    # 2x2 Glass Metric Grid
    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-tile">
                <div class="metric-label">TOTAL INCIDENTS</div>
                <div class="metric-num" style="color:#f8fafc;">1,247</div>
            </div>
            <div class="metric-tile">
                <div class="metric-label">ACTIVE EMERGENCIES</div>
                <div class="metric-num" style="color:#ef4444;">{active_count}</div>
            </div>
            <div class="metric-tile">
                <div class="metric-label">AI CONFIDENCE</div>
                <div class="metric-num" style="color:#f59e0b;">{avg_conf}%</div>
            </div>
            <div class="metric-tile">
                <div class="metric-label">RESPONDER TEAMS</div>
                <div class="metric-num" style="color:#38bdf8;">156</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Recent Incidents Section Header
    st.markdown(
        """
        <div style="display:flex; justify-content:space-between; align-items:center; margin: 1.1rem 0 0.6rem;">
            <div style="font-size:0.95rem; font-weight:800; color:#f8fafc;">Recent Incidents</div>
            <div style="font-size:0.72rem; font-weight:700; color:#38bdf8; cursor:pointer;">See All</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Render List of Incidents
    for inc in all_incidents[:5]:
        status = inc.get("status", "REPORTED")
        badge_cls = "badge-critical" if status == "REPORTED" else ("badge-warning" if status == "DISPATCHED" else "badge-resolved")
        badge_label = "CRITICAL" if status == "REPORTED" else status
        addr = inc.get("address") or f"Coordinates ({inc['latitude']:.4f}, {inc['longitude']:.4f})"
        inc_id = inc["incident_id"]

        st.markdown(
            f"""
            <div class="incident-card">
                <div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span class="inc-id">{inc_id}</span>
                        <span class="badge-pill {badge_cls}">{badge_label}</span>
                    </div>
                    <div class="inc-loc">📍 {addr}</div>
                </div>
                <div style="font-size:0.7rem; color:#64748b; font-weight:600;">{inc.get('timestamp', 'Just now')[-8:-3]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Direct 1-Click Trigger to inspect or engage SOS
    if st.button("🚨 TRIGGER 10s EMERGENCY SOS", type="primary", use_container_width=True):
        st.session_state.mobile_timer_active = True
        st.session_state.mobile_timer_start = time.time()
        st.session_state.mobile_timer_cancelled = False
        st.rerun()

    if st.button("⚡ Test Direct Twilio Emergency Call Now", use_container_width=True):
        with st.spinner(f"Placing direct Twilio voice call to {notify.EMERGENCY_DISPATCH_PHONE}..."):
            c_res = notify.trigger_emergency_call(
                {"incident_id": "TEST-VOICE", "vehicle_type": "Motorcycle", "confidence": 98.0, "city": "Bengaluru Central"},
                to_phone=notify.EMERGENCY_DISPATCH_PHONE
            )
            s_res = notify.send_emergency_sms(
                {"incident_id": "TEST-VOICE", "vehicle_type": "Motorcycle", "confidence": 98.0, "latitude": 17.5192, "longitude": 78.6299},
                to_phone=notify.EMERGENCY_DISPATCH_PHONE
            )
            if c_res.get("success"):
                st.success(f"📞 Twilio Voice Call Placed! SID: {c_res.get('sid')} (Status: {c_res.get('status')})")
            else:
                st.error(f"Twilio notice: {c_res.get('error')}")

# -----------------------------------------------------------------------------
# TAB 2: ! ALERTS / ACTIVE INCIDENT DETAIL VIEW
# -----------------------------------------------------------------------------
elif st.session_state.mobile_section == "Alerts":
    cur_inc = db.get_incident(st.session_state.selected_incident_id) or all_incidents[0]
    
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.75rem;">
            <div style="font-size:1.1rem; font-weight:800; color:#f8fafc;">
                Incident #{cur_inc['incident_id']}
            </div>
            <span class="badge-pill badge-critical">CRITICAL</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Rider Profile Card
    st.markdown(
        f"""
        <div class="glass-card" style="margin-bottom:0.65rem;">
            <div style="display:flex; align-items:center; justify-content:space-between;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <div style="width:38px; height:38px; border-radius:50%; background:linear-gradient(135deg, #ef4444, #f97316); display:grid; place-items:center; font-size:1.1rem;">
                        🏍️
                    </div>
                    <div>
                        <div style="font-size:0.92rem; font-weight:800; color:#f8fafc;">Anand Verma</div>
                        <div style="font-size:0.72rem; color:#f87171; font-weight:700;">Rider Status: {cur_inc.get('rider_status', 'NEED HELP')}</div>
                    </div>
                </div>
                <div style="display:flex; gap:6px;">
                    <a href="tel:{notify.EMERGENCY_DISPATCH_PHONE}" style="text-decoration:none;">
                        <span style="display:inline-block; padding:6px 10px; background:rgba(56,189,248,0.15); border:1px solid #38bdf8; border-radius:8px; font-size:0.75rem; color:#38bdf8; font-weight:800;">📞 Call</span>
                    </a>
                </div>
            </div>
            <div style="margin-top:0.75rem; padding-top:0.65rem; border-top:1px solid rgba(255,255,255,0.06); font-size:0.75rem; color:#94a3b8;">
                <b style="color:#7dd3fc;">REVERSE GEOCODED ADDRESS:</b><br/>
                {cur_inc.get('address') or '12 MG Road, Bengaluru'}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Mini Glowing Radar Box
    st.markdown(
        """
        <div class="radar-box">
            <div class="radar-ring-1"></div>
            <div class="radar-ring-2"></div>
            <div class="radar-core"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3 Telemetry Tiles: Speed Before, Speed After, G-Force
    st.markdown(
        f"""
        <div class="telemetry-row">
            <div class="telemetry-tile">
                <div class="telemetry-label">SPEED BEFORE</div>
                <div class="telemetry-val">87 km/h</div>
            </div>
            <div class="telemetry-tile">
                <div class="telemetry-label">SPEED AFTER</div>
                <div class="telemetry-val">0 km/h</div>
            </div>
            <div class="telemetry-tile">
                <div class="telemetry-label">G-FORCE</div>
                <div class="telemetry-val" style="color:#f87171;">4.2 G</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # AI Confidence Bar
    conf_val = int(cur_inc.get("confidence", 89))
    st.markdown(
        f"""
        <div style="background:rgba(15,23,42,0.8); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:0.65rem 0.85rem; margin-bottom:0.85rem;">
            <div style="display:flex; justify-content:space-between; font-size:0.75rem; font-weight:800; color:#cbd5e1; margin-bottom:4px;">
                <span>AI CONFIDENCE</span>
                <span style="color:#f59e0b;">{conf_val}%</span>
            </div>
            <div style="width:100%; height:8px; background:rgba(255,255,255,0.1); border-radius:99px; overflow:hidden;">
                <div style="width:{conf_val}%; height:100%; background:linear-gradient(90deg, #f59e0b, #ef4444); border-radius:99px;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 4 Quick Action Buttons: Dispatch 108, SMS, Call (Twilio), Resolve
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        if st.button("🚨 108", help="Dispatch 108 Ambulance", use_container_width=True):
            st.session_state.mobile_timer_active = True
            st.session_state.mobile_timer_start = time.time()
            st.rerun()
    with col_b:
        if st.button("💬 SMS", help="Send Emergency SMS", use_container_width=True):
            notify.send_emergency_sms(dict(cur_inc), to_phone=notify.EMERGENCY_DISPATCH_PHONE)
            st.success("SMS Dispatched!")
    with col_c:
        if st.button("📞 Call", help="Automated Twilio Call", use_container_width=True):
            res = notify.trigger_emergency_call(dict(cur_inc), to_phone=notify.EMERGENCY_DISPATCH_PHONE)
            st.info(f"Twilio Call: {res.get('status', 'queued')}")
    with col_d:
        if st.button("✓ Done", help="Mark Resolved", use_container_width=True):
            db.update_incident(cur_inc["incident_id"], status="RESOLVED")
            st.success("Resolved!")
            st.rerun()

    # Activities Timeline
    st.markdown(
        """
        <div style="font-size:0.82rem; font-weight:800; color:#f8fafc; margin:1rem 0 0.5rem;">Action Timeline</div>
        <div class="glass-card" style="padding:0.75rem 0.85rem; font-size:0.72rem;">
            <div style="margin-bottom:6px; color:#cbd5e1;">● Emergency unit 04 dispatched · <span style="color:#64748b;">14:24:12</span></div>
            <div style="margin-bottom:6px; color:#cbd5e1;">● Rider confirmed address via Twilio speech · <span style="color:#64748b;">14:23:45</span></div>
            <div style="color:#34d399;">● Automated voice alert completed · <span style="color:#64748b;">14:23:01</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# TAB 3: ⌖ MAP (LIVE GIS RADAR TRACKER)
# -----------------------------------------------------------------------------
elif st.session_state.mobile_section == "Map":
    st.markdown(
        """
        <div style="margin-bottom:0.75rem;">
            <input type="text" placeholder="🔍 Search active incident or landmark..." style="width:100%; background:rgba(15,23,42,0.8); border:1px solid rgba(255,255,255,0.1); border-radius:12px; padding:9px 12px; color:#f8fafc; font-size:0.8rem;" />
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Render Dark Matter Leaflet Interactive Map
    try:
        import folium
        from streamlit_folium import folium_static

        m = folium.Map(
            location=[17.4435, 78.3772],
            zoom_start=14,
            tiles="CartoDB dark_matter",
            control_scale=False,
            zoom_control=False,
        )

        # Radar circle perimeter
        folium.Circle(
            location=[17.4435, 78.3772],
            radius=350,
            color="#ef4444",
            fill=True,
            fill_color="#ef4444",
            fill_opacity=0.18,
            weight=2,
        ).add_to(m)

        folium.Circle(
            location=[17.4435, 78.3772],
            radius=750,
            color="#ef4444",
            fill=False,
            weight=1,
            dash_array="5, 8",
        ).add_to(m)

        # Pulsing Red Marker
        folium.Marker(
            location=[17.4435, 78.3772],
            popup="Active Crash Perimeter",
            icon=folium.Icon(color="red", icon="warning", prefix="fa"),
        ).add_to(m)

        folium_static(m, width=440, height=360)
    except Exception:
        st.markdown(
            """
            <div class="radar-box" style="height:320px;">
                <div class="radar-ring-1"></div>
                <div class="radar-ring-2"></div>
                <div class="radar-core"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Floating Bottom Incident Card
    st.markdown(
        """
        <div class="glass-card" style="margin-top:0.75rem; display:flex; align-items:center; justify-content:space-between;">
            <div>
                <div style="font-size:0.85rem; font-weight:800; color:#f8fafc;">#SR-0042 <span class="badge-pill badge-critical">CRITICAL</span></div>
                <div style="font-size:0.72rem; color:#94a3b8; margin-top:2px;">MG Road Corridor · 17.4435, 78.3772</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("🚨 INSTANT DISPATCH TO SCENE", type="primary", use_container_width=True):
        st.session_state.mobile_timer_active = True
        st.session_state.mobile_timer_start = time.time()
        st.rerun()

# -----------------------------------------------------------------------------
# TAB 4: ⚡ SIM (CRASH SIMULATOR)
# -----------------------------------------------------------------------------
elif st.session_state.mobile_section == "Sim":
    st.markdown(
        """
        <div style="font-size:1.15rem; font-weight:800; color:#f8fafc; margin-bottom:0.25rem;">
            ⚡ Crash Simulator
        </div>
        <div style="font-size:0.75rem; color:#94a3b8; margin-bottom:0.85rem;">
            Simulate velocity drops, g-forces, and tilt vectors to test AI scoring.
        </div>
        """,
        unsafe_allow_html=True,
    )

    preset = st.selectbox(
        "PRESET SELECTOR",
        options=list(ad.SIMULATION_PRESETS.keys()),
        index=3,
        label_visibility="visible",
    )
    p_data = ad.SIMULATION_PRESETS[preset]

    # Vehicle Selector Pills
    v_type = st.radio("VEHICLE TYPE", ["Motorcycle (92%)", "Car", "Auto", "Bus"], horizontal=True)
    clean_v_type = v_type.split()[0]

    # Telemetry Sliders
    sp_before = st.slider("Speed Before Impact (km/h)", 0, 160, int(p_data["speed_before"]))
    sp_after = st.slider("Speed After Impact (km/h)", 0, 160, int(p_data["speed_after"]))
    g_force = st.slider("G-Force Impact Vector (G)", 0.5, 12.0, float(p_data["impact_force_g"]), 0.1)
    tilt = st.slider("Maximum Tilt Angle (°)", 0, 90, int(p_data["tilt_angle_deg"]))

    # Evaluate with AI Detection Module
    eval_res = ad.detect_accident(
        speed_before=sp_before,
        speed_after=sp_after,
        impact_force_g=g_force,
        tilt_angle_deg=tilt,
        vehicle_type=clean_v_type,
    )

    score = int(eval_res["confidence"])
    score_color = "#ef4444" if score >= 60 else "#34d399"
    prob_text = "SEVERE CRASH PROBABILITY" if score >= 60 else "NORMAL RIDE TELEMETRY"

    st.markdown(
        f"""
        <div class="glass-card" style="text-align:center; padding:1.2rem; border-color:{score_color}; box-shadow:0 0 25px {score_color}33;">
            <div style="font-size:0.7rem; font-weight:800; color:#94a3b8; letter-spacing:0.1em; text-transform:uppercase;">
                AI CONFIDENCE EVALUATION
            </div>
            <div style="font-size:3.2rem; font-weight:900; color:{score_color}; line-height:1; margin:0.35rem 0;">
                {score}%
            </div>
            <div style="font-size:0.8rem; font-weight:800; color:{score_color}; letter-spacing:0.06em;">
                {prob_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    auto_trigger = st.toggle("⚡ Auto-activate Emergency SOS when score is abnormal", value=True)
    if auto_trigger and score >= 60:
        if not st.session_state.get("mobile_timer_active", False) and not st.session_state.get("score_dismissed", False):
            st.session_state.mobile_timer_active = True
            st.session_state.mobile_timer_start = time.time()
            st.session_state.mobile_timer_cancelled = False
            st.session_state.auto_triggered_by_score = score
            st.rerun()
    elif score < 60:
        st.session_state.score_dismissed = False
        st.session_state.auto_triggered_by_score = None

    if st.button("🚨 Trigger Emergency SOS (10s Countdown)", type="primary", use_container_width=True):
        st.session_state.mobile_timer_active = True
        st.session_state.mobile_timer_start = time.time()
        st.session_state.mobile_timer_cancelled = False
        st.session_state.auto_triggered_by_score = score
        st.session_state.score_dismissed = False
        st.rerun()

# -----------------------------------------------------------------------------
# TAB 5: ● PROFILE & SETTINGS
# -----------------------------------------------------------------------------
elif st.session_state.mobile_section == "Profile":
    st.markdown(
        """
        <div class="glass-card" style="text-align:center; padding:1.4rem 1rem;">
            <div style="width:68px; height:68px; border-radius:50%; background:linear-gradient(135deg, #0284c7, #38bdf8); margin:0 auto 0.65rem; display:grid; place-items:center; font-size:1.8rem; border:2px solid rgba(255,255,255,0.2); box-shadow:0 0 20px rgba(56,189,248,0.4);">
                👮‍♂️
            </div>
            <div style="font-size:1.15rem; font-weight:800; color:#f8fafc;">Rajesh Kumar</div>
            <div style="font-size:0.75rem; color:#94a3b8; margin-top:2px;">Senior Dispatcher • Station BLR-01</div>
            
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:0.4rem; margin-top:1.15rem; padding-top:0.95rem; border-top:1px solid rgba(255,255,255,0.08);">
                <div>
                    <div style="font-size:1.1rem; font-weight:800; color:#38bdf8;">342</div>
                    <div style="font-size:0.62rem; color:#64748b; font-weight:700;">RESOLVED</div>
                </div>
                <div>
                    <div style="font-size:1.1rem; font-weight:800; color:#34d399;">2.3m</div>
                    <div style="font-size:0.62rem; color:#64748b; font-weight:700;">RESPONSE</div>
                </div>
                <div>
                    <div style="font-size:1.1rem; font-weight:800; color:#f59e0b;">94%</div>
                    <div style="font-size:0.62rem; color:#64748b; font-weight:700;">ACCURACY</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="glass-card" style="padding:1rem;">
            <div style="font-size:0.72rem; font-weight:800; color:#7dd3fc; letter-spacing:0.08em; text-transform:uppercase; margin-bottom:0.65rem;">
                DISPATCH AUTOMATION PREFERENCES
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.toggle("Critical SOS Alerts", value=True)
    st.toggle("Twilio Automatic Voice & SMS Dispatch", value=True)
    st.selectbox("Language Preference", ["English (en)", "Kannada (kn)", "Telugu (te)", "Hindi (hi)"])

    st.markdown(
        f"""
        <div style="font-size:0.72rem; color:#64748b; margin: 0.85rem 0.2rem 1.4rem;">
            Twilio Gateway: <code style="color:#38bdf8;">ONLINE</code> · Phone: <code style="color:#cbd5e1;">{notify.EMERGENCY_DISPATCH_PHONE}</code>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🔒 Switch Operator / Logout", use_container_width=True):
        st.session_state.is_operator_login_view = True
        st.rerun()

# -----------------------------------------------------------------------------
# FLOATING GLASS BOTTOM NAVIGATION BAR (DOCKS ON ALL SCREENS)
# -----------------------------------------------------------------------------
st.markdown("<div style='height: 4.8rem;'></div>", unsafe_allow_html=True)

nav_cols = st.columns(5)
tabs = [
    ("Home", "⌂"),
    ("Alerts", "!"),
    ("Map", "⌖"),
    ("Sim", "⚡"),
    ("Profile", "●"),
]

for col, (tab_name, icon) in zip(nav_cols, tabs):
    with col:
        is_active = st.session_state.mobile_section == tab_name
        label = f"{icon} {tab_name}" if not is_active else f"👉 {tab_name}"
        btn_type = "primary" if is_active else "secondary"
        if st.button(label, key=f"nav_tab_{tab_name}", type=btn_type, use_container_width=True):
            st.session_state.mobile_section = tab_name
            st.rerun()
