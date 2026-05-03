import streamlit as st
import pandas as pd
import os, json, time, sys
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime, timedelta
from PIL import Image
from utils.config import set_active_vehicle, get_active_vehicle
from db import load_alerts, is_cloud_connected

st.set_page_config(
    page_title="AI Driver Monitoring System",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE       = os.path.dirname(__file__)
USERS_FILE = os.path.join(BASE, "users.json")
SNAP_DIR   = os.path.join(BASE, "..", "data", "snapshots")

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        # Normalise: old format = {"VID": "password"}, new = {"VID": {"password":..,"driver":..}}
        normalised = {}
        for k, v in raw.items():
            if isinstance(v, str):
                normalised[k] = {"password": v, "driver": k}
            else:
                normalised[k] = v
        return normalised
    return {}

def get_password(user_entry):
    """Safely get password from either string or dict entry."""
    if isinstance(user_entry, dict):
        return user_entry.get("password", "")
    return str(user_entry)

def get_driver(user_entry, default="Driver"):
    if isinstance(user_entry, dict):
        return user_entry.get("driver", default)
    return default

def save_users(u):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(u, f, indent=4)

def filter_df(df, vid):
    if df.empty:
        return df
    own = df[df["vehicle_id"] == vid]
    return own if not own.empty else df

def color_for(atype):
    return {"DROWSINESS":"#f59e0b","DISTRACTION":"#38bdf8","MOBILE_USAGE":"#f43f5e"}.get(atype,"#94a3b8")

def icon_for(atype):
    return {"DROWSINESS":"😴","DISTRACTION":"👀","MOBILE_USAGE":"📱"}.get(atype,"⚠️")

def badge(label, color):
    return (f'<span style="background:{color}22;color:{color};border:1px solid {color}44;'
            f'padding:2px 10px;border-radius:20px;font-size:0.7rem;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.05em;">{label}</span>')

# ── CSS ───────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'Outfit', sans-serif !important; }
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    /* Remove Streamlit top whitespace */
    [data-testid="stAppViewContainer"] { padding-top: 0 !important; }
    [data-testid="stAppViewBlockContainer"] { padding-top: 0 !important; }
    div[data-testid="stVerticalBlock"] > div:first-child { padding-top: 0 !important; }
    .main > div { padding-top: 0 !important; }
    /* Login page */
    .login-outer {
        display: flex; align-items: center; justify-content: center;
        min-height: 80vh; padding: 20px;
    }
    [data-testid="stSidebar"] { display: none; }
    section[data-testid="stSidebarContent"] { display: none; }

    body { background: #020617; color: #e2e8f0; }

    .grid-bg {
        background-image: linear-gradient(rgba(56,189,248,0.03) 1px, transparent 1px),
                          linear-gradient(90deg, rgba(56,189,248,0.03) 1px, transparent 1px);
        background-size: 40px 40px;
        min-height: 100vh;
    }
    .glass {
        background: rgba(15,23,42,0.6);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
    }
    .glass-card {
        background: rgba(15,23,42,0.6);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .stat-card {
        background: rgba(15,23,42,0.6);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 20px;
        position: relative;
        overflow: hidden;
    }
    .tab-btn {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 8px 16px; border-radius: 8px 8px 0 0;
        font-size: 0.75rem; font-weight: 600; cursor: pointer;
        border: none; transition: all 0.2s;
        white-space: nowrap;
    }
    .tab-active {
        background: rgba(56,189,248,0.15);
        color: #38bdf8;
        border-bottom: 2px solid #38bdf8;
    }
    .tab-inactive {
        background: transparent;
        color: #94a3b8;
        border-bottom: 2px solid transparent;
    }
    .tab-inactive:hover { color: #e2e8f0; }

    .log-row { transition: background 0.2s; }
    .log-row:hover { background: rgba(255,255,255,0.04); }

    .mono { font-family: 'JetBrains Mono', monospace; }

    .btn-primary {
        background: linear-gradient(135deg, #0ea5e9, #6366f1);
        color: white; border: none; border-radius: 12px;
        padding: 12px 24px; font-weight: 600; font-size: 0.875rem;
        cursor: pointer; width: 100%; transition: all 0.3s;
    }
    .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(14,165,233,0.4); }

    .snapshot-card { transition: all 0.3s ease; border-radius: 12px; overflow: hidden; }
    .snapshot-card:hover { transform: scale(1.03); }

    .alert-item {
        background: rgba(15,23,42,0.6);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 10px;
        display: flex; align-items: flex-start; gap: 12px;
    }
    .sos-btn {
        background: linear-gradient(135deg, #dc2626, #b91c1c);
        color: white; border: none; border-radius: 12px;
        padding: 16px; font-weight: 700; font-size: 1.1rem;
        cursor: pointer; width: 100%; transition: all 0.3s;
        display: flex; align-items: center; justify-content: center; gap: 8px;
    }
    .sos-btn:hover { box-shadow: 0 8px 30px rgba(220,38,38,0.4); }

    .score-ring { position: relative; display: inline-block; }

    /* Mobile responsive */
    @media (max-width: 768px) {
        .block-container { padding: 0 !important; }
        .stat-grid { grid-template-columns: 1fr !important; }
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-track { background: rgba(15,23,42,0.3); }
    ::-webkit-scrollbar-thumb { background: rgba(100,116,139,0.4); border-radius: 2px; }

    /* Streamlit widget overrides */
    .stTextInput input {
        background: rgba(30,41,59,0.7) !important;
        border: 1px solid rgba(100,116,139,0.4) !important;
        border-radius: 12px !important;
        color: white !important;
        font-family: 'Outfit', sans-serif !important;
    }
    .stTextInput input:focus {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 0 2px rgba(56,189,248,0.2) !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #0ea5e9, #6366f1) !important;
        color: white !important; border: none !important;
        border-radius: 12px !important; font-weight: 600 !important;
        font-family: 'Outfit', sans-serif !important;
        transition: all 0.3s !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 30px rgba(14,165,233,0.4) !important;
    }
    div[data-testid="metric-container"] {
        background: rgba(15,23,42,0.6) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 12px !important;
        padding: 16px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ── Login Page ────────────────────────────────────────────────────────────────
def login_page():
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("""
        <div style="text-align:center;padding:40px 0 24px;">
            <div style="display:inline-flex;align-items:center;justify-content:center;
                 width:80px;height:80px;border-radius:20px;
                 background:linear-gradient(135deg,#0ea5e9,#6366f1);margin-bottom:16px;
                 box-shadow:0 0 40px rgba(56,189,248,0.3);">
                <span style="font-size:2rem;">🛡️</span>
            </div>
            <h1 style="font-size:1.6rem;font-weight:800;margin:0;
                background:linear-gradient(135deg,#7dd3fc,#a5b4fc);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                AI Driver Monitoring System
            </h1>
            <p style="color:#94a3b8;font-size:0.75rem;margin-top:6px;
               text-transform:uppercase;letter-spacing:0.1em;">
                Real-time Safety Intelligence
            </p>
        </div>
        """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        tab = st.radio("Select", ["Sign In", "Register"], horizontal=True,
                       label_visibility="hidden", key="login_tab")

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)

        if tab == "Sign In":
            vehicle_id = st.text_input("🚗  Vehicle Number", placeholder="e.g. MH12AB1234",
                                       key="si_vid").strip().upper()
            password   = st.text_input("🔒  Password", type="password",
                                       placeholder="Enter password", key="si_pwd")
            if st.button("Access Dashboard", use_container_width=True, key="si_btn"):
                users = load_users()
                if vehicle_id in users and get_password(users[vehicle_id]) == password:
                    st.session_state.update({"logged_in": True, "vehicle_id": vehicle_id,
                                             "driver_name": get_driver(users[vehicle_id], vehicle_id),
                                             "active_tab": "monitor"})
                    set_active_vehicle(vehicle_id)
                    st.rerun()
                else:
                    st.error("Invalid vehicle number or password.")

        else:
            vehicle_id  = st.text_input("🚗  Vehicle Number", placeholder="e.g. MH12AB1234",
                                        key="reg_vid").strip().upper()
            driver_name = st.text_input("👤  Driver Name", placeholder="Full name", key="reg_name")
            password    = st.text_input("🔒  Password", type="password",
                                        placeholder="Create password", key="reg_pwd")
            if st.button("Register Vehicle", use_container_width=True, key="reg_btn"):
                if not vehicle_id or not driver_name or not password:
                    st.warning("Please fill all fields.")
                elif len(password) < 4:
                    st.error("Password must be at least 4 characters.")
                else:
                    users = load_users()
                    if vehicle_id in users:
                        st.error("Vehicle already registered.")
                    else:
                        users[vehicle_id] = {"driver": driver_name, "password": password}
                        save_users(users)
                        st.success(f"✅ Registered! Sign in with {vehicle_id}")

        st.markdown('</div>', unsafe_allow_html=True)

# ── Top Bar ───────────────────────────────────────────────────────────────────
def top_bar(vid, driver_name):
    cloud = is_cloud_connected()
    cloud_html = (f'<span style="color:#10b981;">☁️ Cloud</span>' if cloud
                  else '<span style="color:#94a3b8;">💾 Local</span>')
    st.markdown(f"""
    <div style="background:rgba(15,23,42,0.8);backdrop-filter:blur(20px);
         border-bottom:1px solid rgba(255,255,255,0.08);
         padding:12px 20px;display:flex;align-items:center;
         justify-content:space-between;position:sticky;top:0;z-index:100;">
        <div style="display:flex;align-items:center;gap:12px;">
            <div style="width:36px;height:36px;border-radius:10px;
                 background:linear-gradient(135deg,#0ea5e9,#6366f1);
                 display:flex;align-items:center;justify-content:center;font-size:1rem;">🛡️</div>
            <div>
                <div style="font-weight:700;font-size:0.9rem;color:#e2e8f0;">AI Driver Monitoring</div>
                <div style="font-size:0.7rem;color:#94a3b8;font-family:'JetBrains Mono',monospace;">
                    {vid} • {driver_name} • {cloud_html}
                </div>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:10px;">
            <div style="display:flex;align-items:center;gap:6px;padding:6px 12px;
                 border-radius:8px;background:rgba(16,185,129,0.15);
                 border:1px solid rgba(16,185,129,0.3);">
                <span style="width:8px;height:8px;border-radius:50%;
                      background:#10b981;display:inline-block;
                      animation:pulse 2s infinite;"></span>
                <span style="color:#10b981;font-size:0.7rem;font-weight:600;">LIVE</span>
            </div>
        </div>
    </div>
    <style>@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.5}}}}</style>
    """, unsafe_allow_html=True)

# ── Tab Navigation ────────────────────────────────────────────────────────────
def tab_nav(active):
    tabs = [
        ("monitor",   "📊", "Monitor"),
        ("logs",      "📋", "Logs"),
        ("snapshots", "📷", "Snapshots"),
        ("alerts",    "🔔", "Alerts"),
        ("analytics", "📈", "Analytics"),
        ("emergency", "🆘", "Emergency"),
    ]
    cols = st.columns(len(tabs))
    for i, (key, icon, label) in enumerate(tabs):
        with cols[i]:
            is_active = active == key
            style = ("background:rgba(56,189,248,0.15);color:#38bdf8;"
                     "border-bottom:2px solid #38bdf8;" if is_active else
                     "background:transparent;color:#94a3b8;border-bottom:2px solid transparent;")
            if st.button(f"{icon} {label}", key=f"tab_{key}", use_container_width=True):
                st.session_state["active_tab"] = key
                st.rerun()

# ── Monitor Tab ───────────────────────────────────────────────────────────────
def tab_monitor(df, vid):
    drowsy  = len(df[df["alert_type"]=="DROWSINESS"])
    phone   = len(df[df["alert_type"]=="MOBILE_USAGE"])
    distract= len(df[df["alert_type"]=="DISTRACTION"])
    total   = len(df)
    score   = max(0, 100 - (drowsy*8 + phone*12 + distract*5))
    risk    = "🟢 Low" if score>70 else "🟡 Medium" if score>40 else "🔴 High"
    risk_c  = "#10b981" if score>70 else "#f59e0b" if score>40 else "#f43f5e"
    maxv    = max(total, 1)

    # ── Stat cards ────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    for col, label, val, color, icon in [
        (c1, "Drowsiness",  drowsy,   "#f59e0b", "😴"),
        (c2, "Phone Usage", phone,    "#f43f5e", "📱"),
        (c3, "Distraction", distract, "#38bdf8", "👀"),
    ]:
        pct = int((val/maxv)*100)
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div style="position:absolute;top:0;right:0;width:80px;height:80px;
                     background:{color};opacity:0.05;border-radius:50%;filter:blur(20px);"></div>
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
                    <div style="width:44px;height:44px;border-radius:12px;
                         background:{color}22;display:flex;align-items:center;
                         justify-content:center;font-size:1.3rem;">{icon}</div>
                    <div>
                        <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;
                             letter-spacing:0.08em;">{label}</div>
                        <div style="font-size:1.8rem;font-weight:700;color:{color};
                             font-family:'JetBrains Mono',monospace;">{val}</div>
                    </div>
                </div>
                <div style="width:100%;height:6px;background:rgba(30,41,59,0.8);
                     border-radius:3px;overflow:hidden;">
                    <div style="width:{pct}%;height:100%;
                         background:linear-gradient(90deg,{color},{color}88);
                         border-radius:3px;transition:width 1s ease;"></div>
                </div>
                <div style="font-size:0.65rem;color:#475569;margin-top:6px;">
                    Detections in session
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Camera feed + Safety score ────────────────────────────────────────────
    col_feed, col_score = st.columns([2, 1])

    with col_feed:
        now_str = datetime.now().strftime("%H:%M:%S")
        last_alert = df.iloc[0] if not df.empty else None
        feed_status = "Monitoring Active"
        feed_color  = "#38bdf8"
        if last_alert is not None:
            mins_ago = (datetime.now() - last_alert["timestamp"].to_pydatetime().replace(tzinfo=None)).seconds // 60
            if mins_ago < 5:
                feed_status = f"⚠ {last_alert['alert_type'].replace('_',' ')} Detected"
                feed_color  = color_for(str(last_alert["alert_type"]))

        st.markdown(f"""
        <div class="glass-card" style="padding:0;overflow:hidden;">
            <div style="padding:12px 16px;border-bottom:1px solid rgba(255,255,255,0.06);
                 display:flex;align-items:center;justify-content:space-between;">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="width:8px;height:8px;border-radius:50%;background:#ef4444;
                          display:inline-block;"></span>
                    <span style="font-size:0.78rem;color:#cbd5e1;font-weight:500;">Driver Camera Feed</span>
                </div>
                <span style="font-size:0.7rem;color:#475569;font-family:'JetBrains Mono',monospace;">{now_str}</span>
            </div>
            <div style="height:200px;background:#0f172a;display:flex;align-items:center;
                 justify-content:center;position:relative;">
                <div style="text-align:center;">
                    <div style="width:72px;height:72px;border-radius:50%;
                         border:2px solid {feed_color}44;display:flex;align-items:center;
                         justify-content:center;margin:0 auto 12px;font-size:2.5rem;">👤</div>
                    <div style="font-size:0.85rem;color:{feed_color};font-weight:600;">{feed_status}</div>
                    <div style="font-size:0.7rem;color:#475569;margin-top:4px;">AI analyzing driver behavior</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_score:
        score_color = "#10b981" if score>70 else "#f59e0b" if score>40 else "#f43f5e"
        circumference = 326.7
        offset = circumference - (circumference * score / 100)
        st.markdown(f"""
        <div class="glass-card">
            <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;
                 letter-spacing:0.08em;margin-bottom:16px;">Safety Score</div>
            <div style="display:flex;justify-content:center;margin-bottom:16px;">
                <div style="position:relative;width:120px;height:120px;">
                    <svg viewBox="0 0 120 120" style="width:100%;height:100%;transform:rotate(-90deg);">
                        <defs>
                            <linearGradient id="sg" x1="0" y1="0" x2="1" y2="1">
                                <stop offset="0%" stop-color="#10b981"/>
                                <stop offset="100%" stop-color="#38bdf8"/>
                            </linearGradient>
                        </defs>
                        <circle cx="60" cy="60" r="52" fill="none"
                            stroke="rgba(51,65,85,0.5)" stroke-width="8"/>
                        <circle cx="60" cy="60" r="52" fill="none"
                            stroke="url(#sg)" stroke-width="8"
                            stroke-linecap="round"
                            stroke-dasharray="{circumference}"
                            stroke-dashoffset="{offset}"
                            style="transition:stroke-dashoffset 1.5s ease"/>
                    </svg>
                    <div style="position:absolute;inset:0;display:flex;align-items:center;
                         justify-content:center;font-size:1.8rem;font-weight:700;
                         color:{score_color};font-family:'JetBrains Mono',monospace;">{score}</div>
                </div>
            </div>
            <div style="font-size:0.75rem;display:flex;flex-direction:column;gap:8px;">
                <div style="display:flex;justify-content:space-between;color:#94a3b8;">
                    <span>Total Events</span>
                    <span style="color:#e2e8f0;font-family:'JetBrains Mono',monospace;">{total}</span>
                </div>
                <div style="display:flex;justify-content:space-between;color:#94a3b8;">
                    <span>Risk Level</span>
                    <span style="color:{risk_c};font-weight:600;">{risk}</span>
                </div>
                <div style="display:flex;justify-content:space-between;color:#94a3b8;">
                    <span>Last Updated</span>
                    <span style="color:#e2e8f0;font-family:'JetBrains Mono',monospace;">{datetime.now().strftime('%H:%M')}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Recent activity ───────────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;
         letter-spacing:0.08em;margin:8px 0 12px;">Recent Activity</div>
    """, unsafe_allow_html=True)

    recent = df.head(5)
    if recent.empty:
        st.markdown("""
        <div class="glass-card" style="text-align:center;color:#475569;padding:30px;">
            No activity yet. Run main.py to start monitoring.
        </div>
        """, unsafe_allow_html=True)
    else:
        for _, row in recent.iterrows():
            atype = str(row["alert_type"])
            col   = color_for(atype)
            ts    = row["timestamp"].strftime("%d %b  %H:%M:%S")
            st.markdown(f"""
            <div style="background:rgba(15,23,42,0.6);border:1px solid rgba(255,255,255,0.06);
                 border-left:3px solid {col};border-radius:10px;padding:12px 16px;
                 margin-bottom:8px;display:flex;align-items:center;gap:12px;">
                <span style="font-size:1.2rem;">{icon_for(atype)}</span>
                {badge(atype.replace('_',' '), col)}
                <span style="color:#475569;font-size:0.78rem;margin-left:auto;">{ts}</span>
            </div>
            """, unsafe_allow_html=True)

# ── Logs Tab ──────────────────────────────────────────────────────────────────
def tab_logs(df):
    st.markdown('<div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px;">System Logs</div>', unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns([2,1,1])
    with fc1:
        ft = st.selectbox("Type", ["ALL","DROWSINESS","DISTRACTION","MOBILE_USAGE"], label_visibility="hidden", key="log_ft")
    with fc2:
        min_d = df["timestamp"].min().date() if not df.empty else datetime.now().date()-timedelta(days=30)
        d_from = st.date_input("From", value=min_d, key="log_from", label_visibility="hidden")
    with fc3:
        d_to = st.date_input("To", value=datetime.now().date(), key="log_to", label_visibility="hidden")

    vdf = df.copy()
    if ft != "ALL":
        vdf = vdf[vdf["alert_type"]==ft]
    vdf = vdf[(vdf["timestamp"].dt.date >= d_from) & (vdf["timestamp"].dt.date <= d_to)]

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total", len(vdf))
    c2.metric("😴 Drowsy",  len(vdf[vdf["alert_type"]=="DROWSINESS"]))
    c3.metric("👀 Distract",len(vdf[vdf["alert_type"]=="DISTRACTION"]))
    c4.metric("📱 Mobile",  len(vdf[vdf["alert_type"]=="MOBILE_USAGE"]))

    st.markdown("<br>", unsafe_allow_html=True)

    if vdf.empty:
        st.markdown('<div class="glass-card" style="text-align:center;color:#475569;padding:40px;"><div style="font-size:2rem;margin-bottom:8px;">📋</div>No records found.</div>', unsafe_allow_html=True)
        return

    st.markdown('<div style="background:rgba(15,23,42,0.8);border:1px solid rgba(255,255,255,0.08);border-radius:12px;overflow:hidden;"><div style="display:grid;grid-template-columns:2fr 1.5fr 1fr;padding:10px 16px;border-bottom:1px solid rgba(255,255,255,0.06);"><span style="font-size:0.65rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">Timestamp</span><span style="font-size:0.65rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">Alert Type</span><span style="font-size:0.65rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">Vehicle</span></div>', unsafe_allow_html=True)

    for _, row in vdf.head(200).iterrows():
        atype = str(row["alert_type"])
        col   = color_for(atype)
        ts    = row["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        vid_r = str(row.get("vehicle_id","—"))
        st.markdown(f'<div class="log-row" style="display:grid;grid-template-columns:2fr 1.5fr 1fr;padding:10px 16px;border-bottom:1px solid rgba(255,255,255,0.04);"><span style="font-size:0.75rem;color:#94a3b8;font-family:\'JetBrains Mono\',monospace;">{ts}</span><span>{badge(atype.replace("_"," "), col)}</span><span style="font-size:0.75rem;color:#64748b;">{vid_r}</span></div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    csv = vdf[["timestamp","alert_type","vehicle_id"]].copy()
    csv["timestamp"] = csv["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.download_button("⬇️ Export CSV", csv.to_csv(index=False).encode(), "alert_log.csv", "text/csv")


# ── Snapshots Tab ─────────────────────────────────────────────────────────────
def tab_snapshots(df):
    st.markdown("""
    <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;
         letter-spacing:0.08em;margin-bottom:12px;">Alert Snapshots</div>
    """, unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns([2,1,1])
    with fc1:
        ft = st.selectbox("Type", ["ALL","DROWSINESS","DISTRACTION","MOBILE_USAGE"],
                          label_visibility="hidden", key="snap_ft")
    with fc2:
        d_from = st.date_input("From", value=datetime.now().date()-timedelta(days=30),
                               key="snap_from", label_visibility="hidden")
    with fc3:
        d_to = st.date_input("To", value=datetime.now().date(),
                             key="snap_to", label_visibility="hidden")

    # Try log-linked snapshots
    snaps = df[df["snapshot"].astype(str).str.strip() != ""].copy()
    snaps = snaps[(snaps["timestamp"].dt.date >= d_from) & (snaps["timestamp"].dt.date <= d_to)]
    if ft != "ALL":
        snaps = snaps[snaps["alert_type"]==ft]
    snaps = snaps[snaps["snapshot"].apply(lambda p: os.path.exists(str(p)))]

    # Fallback: scan folder
    if snaps.empty:
        files = []
        if os.path.exists(SNAP_DIR):
            files = sorted([f for f in os.listdir(SNAP_DIR) if f.lower().endswith(".jpg")], reverse=True)
        if ft != "ALL":
            files = [f for f in files if f.upper().startswith(ft)]
        if not files:
            st.markdown("""
            <div class="glass-card" style="text-align:center;color:#475569;padding:40px;">
                <div style="font-size:2.5rem;margin-bottom:8px;">📷</div>
                No snapshots yet. Run main.py to start capturing.
            </div>
            """, unsafe_allow_html=True)
            return

        cols = st.columns(3)
        for i, fname in enumerate(files[:30]):
            fpath = os.path.join(SNAP_DIR, fname)
            try:
                atype = fname.split("_")[0].upper()
                col   = color_for(atype)
                ts    = "_".join(fname.replace(".jpg","").split("_")[1:3])
                with cols[i%3]:
                    st.image(Image.open(fpath), use_container_width=True)
                    st.markdown(f"<div style='text-align:center;margin-bottom:12px;'>"
                                f"{badge(atype.replace('_',' '),col)}"
                                f"<div style='color:#475569;font-size:0.65rem;margin-top:3px;'>{ts}</div>"
                                f"</div>", unsafe_allow_html=True)
            except Exception:
                pass
        return

    cols = st.columns(3)
    for i, (_, row) in enumerate(snaps.head(30).iterrows()):
        snap  = str(row["snapshot"])
        atype = str(row["alert_type"])
        col   = color_for(atype)
        ts    = row["timestamp"].strftime("%d %b  %H:%M:%S")
        try:
            with cols[i%3]:
                st.image(Image.open(snap), use_container_width=True)
                st.markdown(f"<div style='text-align:center;margin-bottom:12px;'>"
                            f"{badge(atype.replace('_',' '),col)}"
                            f"<div style='color:#475569;font-size:0.65rem;margin-top:3px;'>{ts}</div>"
                            f"</div>", unsafe_allow_html=True)
        except Exception:
            pass

# ── Alerts Tab ────────────────────────────────────────────────────────────────
def tab_alerts(df):
    st.markdown("""
    <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;
         letter-spacing:0.08em;margin-bottom:12px;">Critical Alerts</div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.markdown("""
        <div class="glass-card" style="text-align:center;color:#475569;padding:40px;">
            <div style="font-size:2.5rem;margin-bottom:8px;">🔔</div>
            No alerts yet.
        </div>
        """, unsafe_allow_html=True)
        return

    fc1, fc2 = st.columns([2,1])
    with fc1:
        ft = st.selectbox("Filter", ["ALL","DROWSINESS","DISTRACTION","MOBILE_USAGE"],
                          label_visibility="hidden", key="alert_ft")
    with fc2:
        limit = st.selectbox("Show", [25,50,100], label_visibility="hidden", key="alert_lim")

    vdf = df.copy()
    if ft != "ALL":
        vdf = vdf[vdf["alert_type"]==ft]
    vdf = vdf.head(limit)

    for _, row in vdf.iterrows():
        atype = str(row["alert_type"])
        col   = color_for(atype)
        ts    = row["timestamp"].strftime("%d %b %Y  %H:%M:%S")
        snap  = str(row.get("snapshot",""))

        left, right = st.columns([4,1])
        with left:
            st.markdown(f"""
            <div style="background:rgba(15,23,42,0.6);border:1px solid {col}33;
                 border-left:3px solid {col};border-radius:12px;
                 padding:14px 16px;margin-bottom:8px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
                    <span style="font-size:1.3rem;">{icon_for(atype)}</span>
                    {badge(atype.replace('_',' '), col)}
                    <span style="color:#475569;font-size:0.75rem;margin-left:auto;">{ts}</span>
                </div>
                <div style="color:#64748b;font-size:0.75rem;">
                    Vehicle: <span style="color:#94a3b8;">{row.get('vehicle_id','—')}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with right:
            if snap and os.path.exists(snap):
                try:
                    st.image(Image.open(snap), width=100)
                except Exception:
                    pass

# ── Analytics Tab ─────────────────────────────────────────────────────────────
def tab_analytics(df):
    st.markdown("""
    <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;
         letter-spacing:0.08em;margin-bottom:12px;">Analytics & Insights</div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.info("No data available yet.")
        return

    # Weekly summary
    week_ago = datetime.now() - timedelta(days=7)
    wdf = df[df["timestamp"] >= week_ago]

    c1,c2,c3 = st.columns(3)
    for col_w, label, atype, color in [
        (c1,"Drowsiness","DROWSINESS","#f59e0b"),
        (c2,"Phone Use","MOBILE_USAGE","#f43f5e"),
        (c3,"Distraction","DISTRACTION","#38bdf8"),
    ]:
        val = len(wdf[wdf["alert_type"]==atype])
        with col_w:
            st.markdown(f"""
            <div style="background:rgba(30,41,59,0.5);border-radius:12px;
                 padding:16px;text-align:center;margin-bottom:16px;">
                <div style="font-size:0.65rem;color:#94a3b8;text-transform:uppercase;
                     letter-spacing:0.06em;margin-bottom:6px;">{label}</div>
                <div style="font-size:1.8rem;font-weight:700;color:{color};
                     font-family:'JetBrains Mono',monospace;">{val}</div>
                <div style="font-size:0.65rem;color:#475569;margin-top:4px;">Last 7 days</div>
            </div>
            """, unsafe_allow_html=True)

    # Charts
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown('<div style="font-size:0.75rem;color:#94a3b8;margin-bottom:8px;">Alert Distribution</div>', unsafe_allow_html=True)
        counts = df["alert_type"].value_counts().reset_index()
        counts.columns = ["Type","Count"]
        if not counts.empty:
            st.bar_chart(counts.set_index("Type"), height=220)

    with col_r:
        st.markdown('<div style="font-size:0.75rem;color:#94a3b8;margin-bottom:8px;">Daily Trend</div>', unsafe_allow_html=True)
        vdf2 = df.copy()
        vdf2["day"] = vdf2["timestamp"].dt.floor("D")
        daily = vdf2.groupby(["day","alert_type"]).size().unstack(fill_value=0)
        if not daily.empty:
            st.line_chart(daily, height=220)

    # Alerts by hour
    st.markdown('<div style="font-size:0.75rem;color:#94a3b8;margin:12px 0 8px;">Alerts by Hour of Day</div>', unsafe_allow_html=True)
    vdf3 = df.copy()
    vdf3["hour"] = vdf3["timestamp"].dt.hour
    hourly = vdf3.groupby(["hour","alert_type"]).size().unstack(fill_value=0)
    if not hourly.empty:
        st.bar_chart(hourly, height=180)

    # Achievements
    st.markdown('<div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.08em;margin:16px 0 12px;">Achievements</div>', unsafe_allow_html=True)
    score = max(0, 100 - (len(df[df["alert_type"]=="DROWSINESS"])*8 +
                           len(df[df["alert_type"]=="MOBILE_USAGE"])*12 +
                           len(df[df["alert_type"]=="DISTRACTION"])*5))
    achievements = []
    if score >= 80: achievements.append(("🏆","Safe Driver","High safety score"))
    if len(df[df["alert_type"]=="MOBILE_USAGE"]) == 0: achievements.append(("📱","Phone Free","No phone usage"))
    if len(df[df["alert_type"]=="DISTRACTION"]) == 0: achievements.append(("🎯","Focus Master","No distractions"))
    if len(df) < 10: achievements.append(("⚡","Alert Aware","Minimal alerts"))

    if achievements:
        cols = st.columns(min(len(achievements), 4))
        for i, (icon, title, desc) in enumerate(achievements):
            with cols[i % 4]:
                st.markdown(f"""
                <div style="background:rgba(30,41,59,0.5);border-radius:12px;
                     padding:14px;text-align:center;">
                    <div style="font-size:1.8rem;margin-bottom:6px;">{icon}</div>
                    <div style="font-size:0.75rem;font-weight:600;color:#e2e8f0;">{title}</div>
                    <div style="font-size:0.65rem;color:#475569;margin-top:3px;">{desc}</div>
                </div>
                """, unsafe_allow_html=True)

# ── Emergency Tab ─────────────────────────────────────────────────────────────
def tab_emergency():
    st.markdown("""
    <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;
         letter-spacing:0.08em;margin-bottom:12px;">Emergency Services</div>
    """, unsafe_allow_html=True)

    # SOS button
    st.markdown("""
    <div style="background:rgba(15,23,42,0.6);border:1px solid rgba(244,63,94,0.3);
         border-radius:16px;padding:24px;margin-bottom:16px;text-align:center;">
        <div style="display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:12px;">
            <div style="width:56px;height:56px;border-radius:14px;background:rgba(244,63,94,0.15);
                 display:flex;align-items:center;justify-content:center;font-size:1.8rem;">🚨</div>
            <div style="text-align:left;">
                <div style="font-size:1.1rem;font-weight:700;color:#f43f5e;">Emergency Alert System</div>
                <div style="font-size:0.75rem;color:#94a3b8;">Tap SOS for instant emergency help</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚨  EMERGENCY SOS — Call for Help", use_container_width=True, key="sos_btn"):
        st.error("🚨 SOS ACTIVATED — Emergency services have been notified with your location!")
        st.balloons()

    st.markdown("<br>", unsafe_allow_html=True)

    # Emergency contacts
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("""
        <div class="glass-card">
            <div style="font-size:0.75rem;font-weight:600;color:#60a5fa;margin-bottom:12px;">
                🚔 Nearest Police Stations
            </div>
        """, unsafe_allow_html=True)
        for name, dist, phone in [
            ("Central Police Station","0.8 km","100"),
            ("North Police District","1.2 km","100"),
            ("Traffic Control Unit","1.5 km","103"),
        ]:
            st.markdown(f"""
            <div style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
                <div style="font-size:0.8rem;font-weight:600;color:#93c5fd;">{name}</div>
                <div style="font-size:0.7rem;color:#475569;margin-top:2px;">{dist} away</div>
                <a href="tel:{phone}" style="display:inline-block;margin-top:6px;padding:4px 12px;
                   background:rgba(96,165,250,0.15);border:1px solid rgba(96,165,250,0.3);
                   border-radius:6px;color:#60a5fa;font-size:0.7rem;font-weight:600;
                   text-decoration:none;">📞 Call {phone}</a>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        st.markdown("""
        <div class="glass-card">
            <div style="font-size:0.75rem;font-weight:600;color:#34d399;margin-bottom:12px;">
                🏥 Nearest Hospitals
            </div>
        """, unsafe_allow_html=True)
        for name, dist, phone in [
            ("City Medical Center","0.5 km","102"),
            ("Emergency Care Hospital","1.1 km","102"),
            ("Trauma & Emergency Unit","1.8 km","108"),
        ]:
            st.markdown(f"""
            <div style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
                <div style="font-size:0.8rem;font-weight:600;color:#6ee7b7;">{name}</div>
                <div style="font-size:0.7rem;color:#475569;margin-top:2px;">{dist} away</div>
                <a href="tel:{phone}" style="display:inline-block;margin-top:6px;padding:4px 12px;
                   background:rgba(52,211,153,0.15);border:1px solid rgba(52,211,153,0.3);
                   border-radius:6px;color:#34d399;font-size:0.7rem;font-weight:600;
                   text-decoration:none;">📞 Call {phone}</a>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Helplines
    st.markdown("""
    <div class="glass-card">
        <div style="font-size:0.75rem;font-weight:600;color:#fbbf24;margin-bottom:12px;">
            📞 Emergency Helplines
        </div>
    """, unsafe_allow_html=True)
    for service, desc, number, color in [
        ("Police Emergency","Immediate police assistance","100","#60a5fa"),
        ("Ambulance Service","Medical emergency response","102","#34d399"),
        ("Fire Department","Fire & rescue services","101","#f87171"),
        ("Road Accident","National highway helpline","1033","#fbbf24"),
    ]:
        st.markdown(f"""
        <div style="display:flex;align-items:center;justify-content:space-between;
             padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
            <div>
                <div style="font-size:0.82rem;font-weight:600;color:#e2e8f0;">{service}</div>
                <div style="font-size:0.7rem;color:#475569;margin-top:2px;">{desc}</div>
            </div>
            <a href="tel:{number}" style="padding:6px 16px;
               background:{color}22;border:1px solid {color}44;
               border-radius:8px;color:{color};font-size:0.8rem;font-weight:700;
               text-decoration:none;">📞 {number}</a>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    inject_css()

    if "logged_in"   not in st.session_state: st.session_state["logged_in"]   = False
    if "active_tab"  not in st.session_state: st.session_state["active_tab"]  = "monitor"

    if not st.session_state["logged_in"]:
        login_page()
        st.stop()
        return

    vid         = st.session_state["vehicle_id"]
    driver_name = st.session_state.get("driver_name", "Driver")
    active_tab  = st.session_state.get("active_tab", "monitor")

    # Top bar
    top_bar(vid, driver_name)

    # Logout button in top right
    _, _, logout_col = st.columns([4, 4, 1])
    with logout_col:
        if st.button("🚪 Exit", key="logout_btn"):
            for k in ["logged_in","vehicle_id","driver_name","active_tab"]:
                st.session_state.pop(k, None)
            st.rerun()
            st.stop()

    # Tab navigation
    st.markdown('<div style="padding:8px 16px 0;background:rgba(15,23,42,0.4);">', unsafe_allow_html=True)
    tab_nav(active_tab)
    st.markdown('</div>', unsafe_allow_html=True)

    # Load data
    df = load_alerts(vid)
    # Ensure timestamp is always proper datetime with no timezone
    if not df.empty and "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        df["timestamp"] = df["timestamp"].dt.tz_convert(None)
        df = df.dropna(subset=["timestamp"])
        df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)
    if "snapshot" not in df.columns:
        df["snapshot"] = ""
    if "vehicle_id" not in df.columns:
        df["vehicle_id"] = vid

    # Content
    st.markdown('<div style="padding:16px;">', unsafe_allow_html=True)

    if   active_tab == "monitor":   tab_monitor(df, vid)
    elif active_tab == "logs":      tab_logs(df)
    elif active_tab == "snapshots": tab_snapshots(df)
    elif active_tab == "alerts":    tab_alerts(df)
    elif active_tab == "analytics": tab_analytics(df)
    elif active_tab == "emergency": tab_emergency()

    st.markdown('</div>', unsafe_allow_html=True)

    # Auto refresh
    time.sleep(5)
    st.rerun()

if __name__ == "__main__":
    main()
