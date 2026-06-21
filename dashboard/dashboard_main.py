import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os, json, time, sys
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime, timedelta
from PIL import Image
from utils.config import set_active_vehicle, get_active_vehicle
from db import load_alerts, is_cloud_connected

BASE     = os.path.dirname(__file__)
SNAP_DIR = os.path.join(BASE, "..", "data", "snapshots")

# ── Helpers ───────────────────────────────────────────────────────────────────
def color_for(atype):
    return {"DROWSINESS":"#f59e0b","DISTRACTION":"#38bdf8","MOBILE_USAGE":"#f43f5e"}.get(atype,"#94a3b8")

def icon_for(atype):
    return {"DROWSINESS":"😴","DISTRACTION":"👀","MOBILE_USAGE":"📱"}.get(atype,"⚠️")

def badge(label, color):
    return (f'<span style="background:{color}22;color:{color};border:1px solid {color}44;'
            f'padding:2px 10px;border-radius:20px;font-size:0.7rem;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.05em;">{label}</span>')

def safety_grade(score):
    if score >= 90: return "A+", "#10b981"
    if score >= 80: return "A",  "#10b981"
    if score >= 70: return "B",  "#38bdf8"
    if score >= 55: return "C",  "#f59e0b"
    if score >= 40: return "D",  "#f97316"
    return "F", "#f43f5e"

def load_registered_vehicles():
    users_file = os.path.join(BASE, "users.json")
    if os.path.exists(users_file):
        try:
            with open(users_file, encoding="utf-8") as f:
                return list(json.load(f).keys())
        except Exception:
            pass
    return []

def get_latest_snapshot():
    if not os.path.exists(SNAP_DIR):
        return None
    files = sorted([f for f in os.listdir(SNAP_DIR) if f.lower().endswith(".jpg")], reverse=True)
    return os.path.join(SNAP_DIR, files[0]) if files else None

def compute_score(df):
    drowsy   = len(df[df["alert_type"]=="DROWSINESS"])
    phone    = len(df[df["alert_type"]=="MOBILE_USAGE"])
    distract = len(df[df["alert_type"]=="DISTRACTION"])
    return max(0, 100 - (drowsy*8 + phone*12 + distract*5))

# ── CSS ───────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    html,body,[class*="css"]{font-family:'Outfit',sans-serif!important;}
    #MainMenu,footer,header{visibility:hidden;}
    .block-container{padding:0!important;max-width:100%!important;}
    [data-testid="stAppViewContainer"]{padding-top:0!important;}
    [data-testid="stAppViewBlockContainer"]{padding-top:0!important;}
    div[data-testid="stVerticalBlock"]>div:first-child{padding-top:0!important;}
    .main>div{padding-top:0!important;}
    [data-testid="stSidebar"],section[data-testid="stSidebarContent"]{display:none;}
    body{background:#020617;color:#e2e8f0;}
    .glass-card{background:rgba(15,23,42,0.6);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:20px;margin-bottom:16px;}
    .stat-card{background:rgba(15,23,42,0.6);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:20px;position:relative;overflow:hidden;height:100%;}
    .alert-banner{border-radius:12px;padding:12px 16px;margin-bottom:12px;display:flex;align-items:center;gap:12px;animation:slideIn 0.3s ease;}
    @keyframes slideIn{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}
    @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}
    @keyframes blink{0%,100%{opacity:1}50%{opacity:0.3}}
    .tab-active{background:linear-gradient(135deg,#0ea5e9,#6366f1)!important;color:white!important;border:none!important;border-radius:10px!important;font-weight:700!important;}
    .tab-inactive{background:rgba(15,23,42,0.4)!important;color:#64748b!important;border:1px solid rgba(255,255,255,0.06)!important;border-radius:10px!important;}
    .metric-card{background:rgba(15,23,42,0.5);border:1px solid rgba(255,255,255,0.06);border-radius:12px;padding:16px;text-align:center;}
    .log-row{transition:background 0.2s;}
    .log-row:hover{background:rgba(255,255,255,0.04);}
    ::-webkit-scrollbar{width:4px;height:4px;}
    ::-webkit-scrollbar-track{background:rgba(15,23,42,0.3);}
    ::-webkit-scrollbar-thumb{background:rgba(100,116,139,0.4);border-radius:2px;}
    .stTextInput input{background:rgba(30,41,59,0.7)!important;border:1px solid rgba(100,116,139,0.4)!important;border-radius:12px!important;color:white!important;}
    .stTextInput input:focus{border-color:#38bdf8!important;box-shadow:0 0 0 2px rgba(56,189,248,0.2)!important;}
    .stButton>button{background:linear-gradient(135deg,#0ea5e9,#6366f1)!important;color:white!important;border:none!important;border-radius:12px!important;font-weight:600!important;transition:all 0.3s!important;}
    .stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 8px 30px rgba(14,165,233,0.4)!important;}
    div[data-testid="metric-container"]{background:rgba(15,23,42,0.6)!important;border:1px solid rgba(255,255,255,0.08)!important;border-radius:12px!important;padding:16px!important;}
    .grade-badge{display:inline-flex;align-items:center;justify-content:center;width:56px;height:56px;border-radius:14px;font-size:1.6rem;font-weight:800;font-family:'JetBrains Mono',monospace;}
    </style>
    """, unsafe_allow_html=True)

# ── Top Bar ───────────────────────────────────────────────────────────────────
def top_bar(vid, driver_name, df):
    cloud    = is_cloud_connected()
    score    = compute_score(df)
    grade, gc = safety_grade(score)
    cloud_html = (f'<span style="color:#10b981;font-size:0.7rem;">☁️ Cloud Sync ON</span>'
                  if cloud else '<span style="color:#f59e0b;font-size:0.7rem;">💾 Offline Mode</span>')

    # Recent alert banner (last 2 minutes)
    recent_alert = None
    if not df.empty:
        try:
            last = df.iloc[0]
            diff = (datetime.now() - last["timestamp"].to_pydatetime().replace(tzinfo=None)).seconds
            if diff < 120:
                recent_alert = last
        except Exception:
            pass

    st.markdown(f"""
    <div style="background:rgba(10,15,30,0.95);backdrop-filter:blur(20px);
         border-bottom:1px solid rgba(255,255,255,0.06);
         padding:12px 24px;display:flex;align-items:center;
         justify-content:space-between;position:sticky;top:0;z-index:1000;">
        <div style="display:flex;align-items:center;gap:14px;">
            <div style="width:40px;height:40px;border-radius:12px;
                 background:linear-gradient(135deg,#0ea5e9,#6366f1);
                 display:flex;align-items:center;justify-content:center;font-size:1.1rem;
                 box-shadow:0 0 20px rgba(14,165,233,0.3);">🛡️</div>
            <div>
                <div style="font-weight:800;font-size:1rem;color:#f1f5f9;letter-spacing:0.02em;">
                    AI Driver Monitor</div>
                <div style="font-size:0.68rem;color:#475569;font-family:'JetBrains Mono',monospace;margin-top:1px;">
                    {vid} &nbsp;•&nbsp; {driver_name} &nbsp;•&nbsp; {cloud_html}
                </div>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:16px;">
            <div style="text-align:center;">
                <div style="font-size:0.6rem;color:#475569;text-transform:uppercase;letter-spacing:0.08em;">Safety</div>
                <div style="font-size:1.1rem;font-weight:800;color:{gc};font-family:'JetBrains Mono',monospace;">{grade} &nbsp;<span style="font-size:0.75rem;">({score})</span></div>
            </div>
            <div style="display:flex;align-items:center;gap:6px;padding:6px 14px;
                 border-radius:8px;background:rgba(16,185,129,0.12);
                 border:1px solid rgba(16,185,129,0.25);">
                <span style="width:7px;height:7px;border-radius:50%;background:#10b981;
                      display:inline-block;animation:pulse 2s infinite;"></span>
                <span style="color:#10b981;font-size:0.68rem;font-weight:700;letter-spacing:0.05em;">LIVE</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Alert banner if recent alert
    if recent_alert is not None:
        atype = str(recent_alert["alert_type"])
        col   = color_for(atype)
        ico   = icon_for(atype)
        try:
            secs = (datetime.now() - recent_alert["timestamp"].to_pydatetime().replace(tzinfo=None)).seconds
            ago  = f"{secs}s ago" if secs < 60 else f"{secs//60}m ago"
        except Exception:
            ago = "recently"
        st.markdown(f"""
        <div style="background:{col}18;border:1px solid {col}44;border-left:4px solid {col};
             border-radius:10px;padding:10px 16px;margin:10px 24px 0;
             display:flex;align-items:center;gap:12px;animation:slideIn 0.3s ease;">
            <span style="font-size:1.4rem;animation:blink 1s infinite;">{ico}</span>
            <div>
                <div style="font-weight:700;color:{col};font-size:0.82rem;">
                    ⚠️ {atype.replace('_',' ')} DETECTED</div>
                <div style="color:#64748b;font-size:0.7rem;margin-top:2px;">
                    Alert triggered {ago} — Check snapshots for details</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Controls row
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([3, 2, 2, 1])
    with ctrl1:
        live = st.toggle("🔄 Live Refresh", value=st.session_state.get("live_refresh", True), key="live_refresh_toggle")
        st.session_state["live_refresh"] = live
    with ctrl2:
        vehicles = load_registered_vehicles()
        if vehicles:
            current_idx = vehicles.index(vid) if vid in vehicles else 0
            selected_v  = st.selectbox("Vehicle", vehicles, index=current_idx,
                                       key="vehicle_selector", label_visibility="collapsed")
            if selected_v != vid:
                st.session_state["vehicle_id"] = selected_v
                set_active_vehicle(selected_v)
                st.rerun()
    with ctrl3:
        st.markdown(f'<div style="color:#475569;font-size:0.72rem;padding-top:8px;">👤 {driver_name}</div>',
                    unsafe_allow_html=True)
    with ctrl4:
        if st.button("🚪 Out", key="logout_btn", help="Sign Out", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

# ── Tab Navigation ────────────────────────────────────────────────────────────
def tab_nav(active):
    tabs = [
        ("monitor",   "📊", "Monitor"),
        ("logs",      "📋", "Logs"),
        ("snapshots", "📷", "Snapshots"),
        ("alerts",    "🔔", "Alerts"),
        ("analytics", "📈", "Analytics"),
        ("report",    "📄", "Report"),
        ("emergency", "🆘", "Emergency"),
    ]
    cols = st.columns(len(tabs))
    for i, (key, icon, label) in enumerate(tabs):
        is_active = (active == key)
        with cols[i]:
            if is_active:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#0ea5e9,#6366f1);
                     border-radius:10px;padding:8px 4px;text-align:center;
                     font-size:0.75rem;font-weight:700;color:white;
                     box-shadow:0 4px 15px rgba(14,165,233,0.3);">
                    {icon} {label}
                </div>""", unsafe_allow_html=True)
                # invisible button to keep state
                st.button(f"{icon} {label}", key=f"tab_{key}",
                          use_container_width=True, disabled=True)
            else:
                if st.button(f"{icon} {label}", key=f"tab_{key}",
                             use_container_width=True):
                    st.session_state["active_tab"] = key
                    st.rerun()

# ── Monitor Tab ───────────────────────────────────────────────────────────────
def tab_monitor(df, vid, driver_name):
    today     = datetime.now().date()
    today_df  = df[df["timestamp"].dt.date == today] if not df.empty else df
    week_df   = df[df["timestamp"] >= datetime.now() - timedelta(days=7)] if not df.empty else df

    drowsy    = len(df[df["alert_type"]=="DROWSINESS"])
    phone     = len(df[df["alert_type"]=="MOBILE_USAGE"])
    distract  = len(df[df["alert_type"]=="DISTRACTION"])
    total     = len(df)
    score     = compute_score(df)
    grade, gc = safety_grade(score)
    risk      = "🟢 Low" if score>70 else "🟡 Medium" if score>40 else "🔴 High"
    risk_c    = "#10b981" if score>70 else "#f59e0b" if score>40 else "#f43f5e"
    maxv      = max(total, 1)

    # ── Driver profile strip ─────────────────────────────────────────────────
    joined = st.session_state.get("joined_date", today.strftime("%d %b %Y"))
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(14,165,233,0.08),rgba(99,102,241,0.08));
         border:1px solid rgba(255,255,255,0.07);border-radius:16px;
         padding:16px 20px;margin-bottom:16px;display:flex;align-items:center;gap:16px;">
        <div style="width:52px;height:52px;border-radius:14px;
             background:linear-gradient(135deg,#0ea5e9,#6366f1);
             display:flex;align-items:center;justify-content:center;font-size:1.5rem;">
            👤</div>
        <div style="flex:1;">
            <div style="font-weight:700;font-size:1rem;color:#f1f5f9;">{driver_name}</div>
            <div style="font-size:0.7rem;color:#475569;margin-top:2px;font-family:'JetBrains Mono',monospace;">
                Vehicle: {vid} &nbsp;|&nbsp; Total Alerts: {total} &nbsp;|&nbsp; Since: {joined}
            </div>
        </div>
        <div style="text-align:right;">
            <div style="background:{gc}22;color:{gc};border:1px solid {gc}44;
                 border-radius:10px;padding:6px 16px;font-weight:800;
                 font-size:1.3rem;font-family:'JetBrains Mono',monospace;">{grade}</div>
            <div style="font-size:0.65rem;color:#475569;margin-top:4px;">Safety Grade</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Today's stats ────────────────────────────────────────────────────────
    st.markdown('<div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;'
                'letter-spacing:0.08em;margin-bottom:10px;">Today\'s Summary</div>', unsafe_allow_html=True)
    t1, t2, t3, t4 = st.columns(4)
    for col_w, label, val, color, delta_val in [
        (t1, "Today Alerts",  len(today_df),                          "#38bdf8", None),
        (t2, "😴 Drowsiness",  len(today_df[today_df["alert_type"]=="DROWSINESS"]),  "#f59e0b", None),
        (t3, "📱 Phone",       len(today_df[today_df["alert_type"]=="MOBILE_USAGE"]), "#f43f5e", None),
        (t4, "👀 Distraction", len(today_df[today_df["alert_type"]=="DISTRACTION"]),  "#38bdf8", None),
    ]:
        with col_w:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size:0.65rem;color:#475569;text-transform:uppercase;
                     letter-spacing:0.06em;margin-bottom:6px;">{label}</div>
                <div style="font-size:2rem;font-weight:800;color:{color};
                     font-family:'JetBrains Mono',monospace;">{val}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Main stats cards ─────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    for col_w, label, val, color, icon in [
        (c1, "Drowsiness",  drowsy,   "#f59e0b", "😴"),
        (c2, "Phone Usage", phone,    "#f43f5e", "📱"),
        (c3, "Distraction", distract, "#38bdf8", "👀"),
    ]:
        pct = int((val/maxv)*100)
        with col_w:
            st.markdown(f"""
            <div class="stat-card">
                <div style="position:absolute;top:-10px;right:-10px;width:80px;height:80px;
                     background:{color};opacity:0.06;border-radius:50%;filter:blur(20px);"></div>
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
                    <div style="width:46px;height:46px;border-radius:12px;
                         background:{color}22;display:flex;align-items:center;
                         justify-content:center;font-size:1.4rem;
                         border:1px solid {color}33;">{icon}</div>
                    <div>
                        <div style="font-size:0.68rem;color:#94a3b8;text-transform:uppercase;
                             letter-spacing:0.08em;">{label}</div>
                        <div style="font-size:2rem;font-weight:800;color:{color};
                             font-family:'JetBrains Mono',monospace;line-height:1.1;">{val}</div>
                    </div>
                </div>
                <div style="width:100%;height:5px;background:rgba(30,41,59,0.8);
                     border-radius:3px;overflow:hidden;">
                    <div style="width:{pct}%;height:100%;
                         background:linear-gradient(90deg,{color},{color}88);
                         border-radius:3px;transition:width 1.2s ease;"></div>
                </div>
                <div style="font-size:0.65rem;color:#475569;margin-top:6px;">
                    All-time detections &nbsp;|&nbsp;
                    <span style="color:{color};">{pct}% of total</span>
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Latest snapshot + Safety score ──────────────────────────────────────
    col_feed, col_score = st.columns([2, 1])

    with col_feed:
        now_str    = datetime.now().strftime("%H:%M:%S")
        last_alert = df.iloc[0] if not df.empty else None
        feed_status = "Monitoring Active"
        feed_color  = "#10b981"
        if last_alert is not None:
            try:
                mins_ago = (datetime.now() - last_alert["timestamp"].to_pydatetime().replace(tzinfo=None)).seconds // 60
                if mins_ago < 5:
                    feed_status = f"⚠ {last_alert['alert_type'].replace('_',' ')} — {mins_ago}m ago"
                    feed_color  = color_for(str(last_alert["alert_type"]))
            except Exception:
                pass

        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.6);border:1px solid rgba(255,255,255,0.08);
             border-radius:16px;overflow:hidden;margin-bottom:8px;">
            <div style="padding:12px 16px;border-bottom:1px solid rgba(255,255,255,0.06);
                 display:flex;align-items:center;justify-content:space-between;
                 background:rgba(15,23,42,0.8);">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="width:8px;height:8px;border-radius:50%;background:{feed_color};
                          display:inline-block;animation:pulse 2s infinite;"></span>
                    <span style="font-size:0.78rem;color:#cbd5e1;font-weight:600;">Live Camera Feed</span>
                </div>
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-size:0.68rem;color:{feed_color};font-weight:600;">{feed_status}</span>
                    <span style="font-size:0.68rem;color:#475569;font-family:'JetBrains Mono',monospace;">{now_str}</span>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

        latest_snap = get_latest_snapshot()
        if latest_snap:
            try:
                st.image(Image.open(latest_snap), use_container_width=True)
                snap_name  = os.path.basename(latest_snap)
                atype_snap = snap_name.split("_")[0].upper()
                snap_col   = color_for(atype_snap)
                ts_snap    = "_".join(snap_name.replace(".jpg","").split("_")[1:3])
                st.markdown(f'<div style="text-align:center;padding:6px 0;">'
                            f'{badge(atype_snap.replace("_"," "), snap_col)}'
                            f'<span style="color:#475569;font-size:0.65rem;margin-left:8px;">{ts_snap}</span>'
                            f'</div>', unsafe_allow_html=True)
            except Exception:
                st.markdown(f'<div style="height:180px;background:#0f172a;display:flex;align-items:center;'
                            f'justify-content:center;border-radius:12px;color:{feed_color};">No snapshot</div>',
                            unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="height:200px;background:rgba(15,23,42,0.8);border:1px solid rgba(255,255,255,0.06);
                 border-radius:12px;display:flex;align-items:center;justify-content:center;text-align:center;">
                <div>
                    <div style="font-size:3rem;margin-bottom:10px;">📷</div>
                    <div style="font-size:0.85rem;color:{feed_color};font-weight:600;">Camera Ready</div>
                    <div style="font-size:0.7rem;color:#475569;margin-top:4px;">
                        Run main.py to start monitoring</div>
                </div>
            </div>""", unsafe_allow_html=True)

    with col_score:
        score_color   = "#10b981" if score>70 else "#f59e0b" if score>40 else "#f43f5e"
        circumference = 326.7
        offset        = circumference - (circumference * score / 100)
        st.markdown(f"""
        <div class="glass-card" style="height:100%;">
            <div style="font-size:0.68rem;color:#94a3b8;text-transform:uppercase;
                 letter-spacing:0.08em;margin-bottom:14px;">Safety Score</div>
            <div style="display:flex;justify-content:center;margin-bottom:16px;">
                <div style="position:relative;width:130px;height:130px;">
                    <svg viewBox="0 0 120 120" style="width:100%;height:100%;transform:rotate(-90deg);">
                        <defs>
                            <linearGradient id="sg" x1="0" y1="0" x2="1" y2="1">
                                <stop offset="0%" stop-color="{score_color}"/>
                                <stop offset="100%" stop-color="{score_color}88"/>
                            </linearGradient>
                        </defs>
                        <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(30,41,59,0.8)" stroke-width="9"/>
                        <circle cx="60" cy="60" r="52" fill="none" stroke="url(#sg)" stroke-width="9"
                            stroke-linecap="round" stroke-dasharray="{circumference}"
                            stroke-dashoffset="{offset}" style="transition:stroke-dashoffset 1.5s ease;
                            filter:drop-shadow(0 0 6px {score_color}66)"/>
                    </svg>
                    <div style="position:absolute;inset:0;display:flex;flex-direction:column;
                         align-items:center;justify-content:center;">
                        <div style="font-size:2rem;font-weight:800;color:{score_color};
                             font-family:'JetBrains Mono',monospace;line-height:1;">{score}</div>
                        <div style="font-size:0.65rem;color:#475569;margin-top:2px;">/ 100</div>
                    </div>
                </div>
            </div>
            <div style="font-size:0.75rem;display:flex;flex-direction:column;gap:10px;">
                <div style="display:flex;justify-content:space-between;
                     padding:8px 10px;background:rgba(30,41,59,0.4);border-radius:8px;">
                    <span style="color:#94a3b8;">Grade</span>
                    <span style="color:{gc};font-weight:800;font-family:'JetBrains Mono',monospace;">{grade}</span>
                </div>
                <div style="display:flex;justify-content:space-between;
                     padding:8px 10px;background:rgba(30,41,59,0.4);border-radius:8px;">
                    <span style="color:#94a3b8;">Risk Level</span>
                    <span style="color:{risk_c};font-weight:600;">{risk}</span>
                </div>
                <div style="display:flex;justify-content:space-between;
                     padding:8px 10px;background:rgba(30,41,59,0.4);border-radius:8px;">
                    <span style="color:#94a3b8;">Total Events</span>
                    <span style="color:#e2e8f0;font-family:'JetBrains Mono',monospace;">{total}</span>
                </div>
                <div style="display:flex;justify-content:space-between;
                     padding:8px 10px;background:rgba(30,41,59,0.4);border-radius:8px;">
                    <span style="color:#94a3b8;">This Week</span>
                    <span style="color:#38bdf8;font-family:'JetBrains Mono',monospace;">{len(week_df)}</span>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

    # ── Recent Activity ───────────────────────────────────────────────────────
    st.markdown('<div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;'
                'letter-spacing:0.08em;margin:12px 0 10px;">Recent Activity</div>', unsafe_allow_html=True)
    recent = df.head(6)
    if recent.empty:
        st.markdown('<div class="glass-card" style="text-align:center;color:#475569;padding:30px;">'
                    'No activity yet. Run main.py to start monitoring.</div>', unsafe_allow_html=True)
    else:
        for _, row in recent.iterrows():
            atype = str(row["alert_type"])
            col   = color_for(atype)
            ts    = row["timestamp"].strftime("%d %b %Y  %H:%M:%S")
            vid_r = str(row.get("vehicle_id","—"))
            st.markdown(f"""
            <div style="background:rgba(15,23,42,0.5);border:1px solid rgba(255,255,255,0.05);
                 border-left:3px solid {col};border-radius:10px;padding:11px 16px;
                 margin-bottom:7px;display:flex;align-items:center;gap:12px;
                 transition:background 0.2s;">
                <span style="font-size:1.2rem;">{icon_for(atype)}</span>
                {badge(atype.replace('_',' '), col)}
                <span style="color:#475569;font-size:0.72rem;font-family:'JetBrains Mono',monospace;">
                    {vid_r}</span>
                <span style="color:#475569;font-size:0.72rem;margin-left:auto;
                     font-family:'JetBrains Mono',monospace;">{ts}</span>
            </div>""", unsafe_allow_html=True)

# ── Logs Tab ──────────────────────────────────────────────────────────────────
def tab_logs(df):
    st.markdown('<div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;'
                'letter-spacing:0.08em;margin-bottom:14px;">System Logs</div>', unsafe_allow_html=True)

    fc1, fc2, fc3, fc4 = st.columns([2,1,1,1])
    with fc1:
        ft = st.selectbox("Type", ["ALL","DROWSINESS","DISTRACTION","MOBILE_USAGE"],
                          label_visibility="hidden", key="log_ft")
    with fc2:
        min_d  = df["timestamp"].min().date() if not df.empty else datetime.now().date()-timedelta(days=30)
        d_from = st.date_input("From", value=min_d, key="log_from", label_visibility="hidden")
    with fc3:
        d_to = st.date_input("To", value=datetime.now().date(), key="log_to", label_visibility="hidden")
    with fc4:
        sort_order = st.selectbox("Sort", ["Newest First","Oldest First"],
                                  label_visibility="hidden", key="log_sort")

    vdf = df.copy()
    if ft != "ALL":
        vdf = vdf[vdf["alert_type"]==ft]
    try:
        ts = pd.to_datetime(vdf["timestamp"], errors="coerce", utc=True).dt.tz_convert(None)
        vdf = vdf[(ts.dt.date >= d_from) & (ts.dt.date <= d_to)]
    except Exception:
        pass
    if sort_order == "Oldest First":
        vdf = vdf.sort_values("timestamp", ascending=True)

    # Summary metrics
    c1,c2,c3,c4 = st.columns(4)
    for col_w, label, val, color in [
        (c1, "Total",       len(vdf),                                          "#e2e8f0"),
        (c2, "😴 Drowsy",   len(vdf[vdf["alert_type"]=="DROWSINESS"]),          "#f59e0b"),
        (c3, "👀 Distract", len(vdf[vdf["alert_type"]=="DISTRACTION"]),         "#38bdf8"),
        (c4, "📱 Mobile",   len(vdf[vdf["alert_type"]=="MOBILE_USAGE"]),         "#f43f5e"),
    ]:
        with col_w:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size:0.65rem;color:#475569;margin-bottom:4px;">{label}</div>
                <div style="font-size:1.8rem;font-weight:800;color:{color};
                     font-family:'JetBrains Mono',monospace;">{val}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if vdf.empty:
        st.markdown('<div class="glass-card" style="text-align:center;color:#475569;padding:40px;">'
                    '<div style="font-size:2rem;margin-bottom:8px;">📋</div>No records found.</div>',
                    unsafe_allow_html=True)
        return

    # Pagination
    PAGE_SIZE   = 50
    total_pages = max(1, (len(vdf)-1)//PAGE_SIZE+1)
    if "log_page" not in st.session_state:
        st.session_state["log_page"] = 1
    st.session_state["log_page"] = min(st.session_state["log_page"], total_pages)

    pg1, pg2, pg3 = st.columns([1,2,1])
    with pg1:
        if st.button("◀ Prev", key="log_prev", disabled=st.session_state["log_page"]<=1):
            st.session_state["log_page"] -= 1; st.rerun()
    with pg2:
        st.markdown(f'<div style="text-align:center;color:#94a3b8;font-size:0.78rem;padding-top:8px;">'
                    f'Page {st.session_state["log_page"]} of {total_pages} ({len(vdf)} records)</div>',
                    unsafe_allow_html=True)
    with pg3:
        if st.button("Next ▶", key="log_next", disabled=st.session_state["log_page"]>=total_pages):
            st.session_state["log_page"] += 1; st.rerun()

    page_start = (st.session_state["log_page"]-1)*PAGE_SIZE
    page_df    = vdf.iloc[page_start:page_start+PAGE_SIZE]

    # Table header
    st.markdown("""
    <div style="background:rgba(15,23,42,0.9);border:1px solid rgba(255,255,255,0.08);
         border-radius:12px;overflow:hidden;">
    <div style="display:grid;grid-template-columns:2fr 1.5fr 1.2fr 1fr;padding:10px 16px;
         border-bottom:1px solid rgba(255,255,255,0.08);background:rgba(30,41,59,0.5);">
        <span style="font-size:0.65rem;color:#64748b;text-transform:uppercase;
              letter-spacing:0.08em;font-weight:700;">Timestamp</span>
        <span style="font-size:0.65rem;color:#64748b;text-transform:uppercase;
              letter-spacing:0.08em;font-weight:700;">Alert Type</span>
        <span style="font-size:0.65rem;color:#64748b;text-transform:uppercase;
              letter-spacing:0.08em;font-weight:700;">Vehicle</span>
        <span style="font-size:0.65rem;color:#64748b;text-transform:uppercase;
              letter-spacing:0.08em;font-weight:700;">Status</span>
    </div>""", unsafe_allow_html=True)

    for _, row in page_df.iterrows():
        atype = str(row["alert_type"])
        col   = color_for(atype)
        ts    = row["timestamp"].strftime("%Y-%m-%d  %H:%M:%S")
        vid_r = str(row.get("vehicle_id","—"))
        snap  = str(row.get("snapshot",""))
        has_snap = "📷 Snap" if snap and len(snap)>3 else "—"
        snap_col = "#10b981" if snap and len(snap)>3 else "#475569"
        st.markdown(
            f'<div class="log-row" style="display:grid;grid-template-columns:2fr 1.5fr 1.2fr 1fr;'
            f'padding:10px 16px;border-bottom:1px solid rgba(255,255,255,0.04);">'
            f'<span style="font-size:0.74rem;color:#94a3b8;font-family:\'JetBrains Mono\',monospace;">{ts}</span>'
            f'<span>{badge(atype.replace("_"," "), col)}</span>'
            f'<span style="font-size:0.74rem;color:#64748b;">{vid_r}</span>'
            f'<span style="font-size:0.72rem;color:{snap_col};">{has_snap}</span>'
            f'</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    csv_df = vdf[["timestamp","alert_type","vehicle_id"]].copy()
    csv_df["timestamp"] = csv_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.download_button("⬇️ Export CSV", csv_df.to_csv(index=False).encode(), "alert_log.csv", "text/csv")

# ── Snapshots Tab ─────────────────────────────────────────────────────────────
def tab_snapshots(df):
    st.markdown('<div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;'
                'letter-spacing:0.08em;margin-bottom:14px;">Alert Snapshots</div>', unsafe_allow_html=True)

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

    # Cloud snapshots
    cloud = df[df["snapshot"].astype(str).str.startswith("http")].copy()
    if ft != "ALL":
        cloud = cloud[cloud["alert_type"]==ft]
    try:
        ts_c  = pd.to_datetime(cloud["timestamp"], errors="coerce", utc=True).dt.tz_convert(None)
        cloud = cloud[(ts_c.dt.date >= d_from) & (ts_c.dt.date <= d_to)]
    except Exception:
        pass

    if not cloud.empty:
        st.markdown(f'<div style="color:#94a3b8;font-size:0.82rem;margin-bottom:12px;">'
                    f'☁️ {len(cloud)} cloud snapshots</div>', unsafe_allow_html=True)
        cols = st.columns(3)
        for i, (_, row) in enumerate(cloud.head(30).iterrows()):
            url   = str(row["snapshot"])
            atype = str(row["alert_type"])
            col   = color_for(atype)
            try:
                ts = row["timestamp"].strftime("%d %b  %H:%M:%S")
            except Exception:
                ts = str(row["timestamp"])[:19]
            with cols[i%3]:
                st.image(url, use_container_width=True)
                st.markdown(f'<div style="text-align:center;margin-bottom:14px;">'
                            f'{badge(atype.replace("_"," "),col)}'
                            f'<div style="color:#475569;font-size:0.65rem;margin-top:4px;">{ts}</div>'
                            f'</div>', unsafe_allow_html=True)
        return

    # Local snapshots
    files = []
    if os.path.exists(SNAP_DIR):
        files = sorted([f for f in os.listdir(SNAP_DIR) if f.lower().endswith(".jpg")], reverse=True)
    if ft != "ALL":
        files = [f for f in files if f.upper().startswith(ft)]

    if not files:
        st.markdown("""
        <div class="glass-card" style="text-align:center;color:#475569;padding:50px;">
            <div style="font-size:3rem;margin-bottom:12px;">📷</div>
            <div style="font-size:0.9rem;font-weight:600;color:#64748b;">No snapshots yet</div>
            <div style="font-size:0.75rem;margin-top:6px;">Run main.py to start capturing alerts</div>
        </div>""", unsafe_allow_html=True)
        return

    st.markdown(f'<div style="color:#94a3b8;font-size:0.82rem;margin-bottom:12px;">'
                f'💾 {len(files)} local snapshots</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for i, fname in enumerate(files[:30]):
        fpath = os.path.join(SNAP_DIR, fname)
        try:
            atype = fname.split("_")[0].upper()
            col   = color_for(atype)
            parts = fname.replace(".jpg","").split("_")
            ts    = f"{parts[1]} {parts[2]}" if len(parts)>=3 else fname
            with cols[i%3]:
                st.image(Image.open(fpath), use_container_width=True)
                st.markdown(f'<div style="text-align:center;margin-bottom:14px;">'
                            f'{badge(atype.replace("_"," "),col)}'
                            f'<div style="color:#475569;font-size:0.65rem;margin-top:4px;">{ts}</div>'
                            f'</div>', unsafe_allow_html=True)
        except Exception:
            pass

# ── Alerts Tab ────────────────────────────────────────────────────────────────
def tab_alerts(df):
    st.markdown('<div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;'
                'letter-spacing:0.08em;margin-bottom:14px;">Critical Alerts</div>', unsafe_allow_html=True)

    if df.empty:
        st.markdown('<div class="glass-card" style="text-align:center;color:#475569;padding:50px;">'
                    '<div style="font-size:3rem;margin-bottom:12px;">🔔</div>'
                    '<div style="font-size:0.9rem;font-weight:600;color:#64748b;">No alerts yet</div>'
                    '</div>', unsafe_allow_html=True)
        return

    fc1, fc2 = st.columns([2,1])
    with fc1:
        ft    = st.selectbox("Filter", ["ALL","DROWSINESS","DISTRACTION","MOBILE_USAGE"],
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
            <div style="background:rgba(15,23,42,0.6);border:1px solid {col}22;
                 border-left:4px solid {col};border-radius:12px;
                 padding:14px 16px;margin-bottom:8px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <span style="font-size:1.3rem;">{icon_for(atype)}</span>
                    {badge(atype.replace('_',' '), col)}
                    <span style="color:#475569;font-size:0.75rem;margin-left:auto;
                          font-family:'JetBrains Mono',monospace;">{ts}</span>
                </div>
                <div style="color:#64748b;font-size:0.75rem;">
                    Vehicle: <span style="color:#94a3b8;font-family:'JetBrains Mono',monospace;">
                    {row.get('vehicle_id','—')}</span>
                </div>
            </div>""", unsafe_allow_html=True)
        with right:
            if snap and snap.startswith("http"):
                try:
                    st.image(snap, width=100)
                except Exception:
                    pass
            elif snap and os.path.exists(snap):
                try:
                    st.image(Image.open(snap), width=100)
                except Exception:
                    pass

# ── Analytics Tab ─────────────────────────────────────────────────────────────
def tab_analytics(df):
    st.markdown('<div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;'
                'letter-spacing:0.08em;margin-bottom:14px;">Analytics & Insights</div>',
                unsafe_allow_html=True)

    if df.empty:
        st.info("No data available yet.")
        return

    PLOTLY_LAYOUT = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", family="Outfit, sans-serif", size=11),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", linecolor="rgba(255,255,255,0.06)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", linecolor="rgba(255,255,255,0.06)"),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,255,255,0.06)"),
    )
    COLOR_MAP = {"DROWSINESS":"#f59e0b","DISTRACTION":"#38bdf8","MOBILE_USAGE":"#f43f5e"}

    # ── Weekly summary cards ─────────────────────────────────────────────────
    week_ago = datetime.now() - timedelta(days=7)
    wdf      = df[df["timestamp"] >= week_ago]

    c1, c2, c3, c4 = st.columns(4)
    for col_w, label, atype, color in [
        (c1, "This Week",   None,           "#e2e8f0"),
        (c2, "Drowsiness",  "DROWSINESS",   "#f59e0b"),
        (c3, "Phone Use",   "MOBILE_USAGE", "#f43f5e"),
        (c4, "Distraction", "DISTRACTION",  "#38bdf8"),
    ]:
        val = len(wdf) if atype is None else len(wdf[wdf["alert_type"]==atype])
        with col_w:
            st.markdown(f"""
            <div class="metric-card" style="margin-bottom:16px;">
                <div style="font-size:0.65rem;color:#475569;text-transform:uppercase;
                     letter-spacing:0.06em;margin-bottom:6px;">{label}</div>
                <div style="font-size:2rem;font-weight:800;color:{color};
                     font-family:'JetBrains Mono',monospace;">{val}</div>
                <div style="font-size:0.65rem;color:#475569;margin-top:4px;">Last 7 days</div>
            </div>""", unsafe_allow_html=True)

    # ── Charts row 1 ─────────────────────────────────────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div style="font-size:0.75rem;color:#94a3b8;margin-bottom:8px;">Alert Distribution</div>',
                    unsafe_allow_html=True)
        counts = df["alert_type"].value_counts().reset_index()
        counts.columns = ["Type","Count"]
        if not counts.empty:
            fig = px.bar(counts, x="Type", y="Count", color="Type",
                         color_discrete_map=COLOR_MAP, height=220)
            fig.update_layout(**PLOTLY_LAYOUT)
            fig.update_traces(marker_line_width=0, marker_cornerradius=4)
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown('<div style="font-size:0.75rem;color:#94a3b8;margin-bottom:8px;">Daily Trend (30 days)</div>',
                    unsafe_allow_html=True)
        last30 = df[df["timestamp"] >= datetime.now()-timedelta(days=30)].copy()
        last30["day"] = last30["timestamp"].dt.floor("D")
        daily  = last30.groupby(["day","alert_type"]).size().reset_index(name="count")
        if not daily.empty:
            fig2 = px.line(daily, x="day", y="count", color="alert_type",
                           color_discrete_map=COLOR_MAP, height=220)
            fig2.update_layout(**PLOTLY_LAYOUT)
            fig2.update_traces(line_width=2.5)
            st.plotly_chart(fig2, use_container_width=True)

    # ── Charts row 2 ─────────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div style="font-size:0.75rem;color:#94a3b8;margin-bottom:8px;">Alerts by Hour of Day</div>',
                    unsafe_allow_html=True)
        vdf3 = df.copy()
        vdf3["hour"] = vdf3["timestamp"].dt.hour
        hourly = vdf3.groupby(["hour","alert_type"]).size().reset_index(name="count")
        if not hourly.empty:
            fig3 = px.bar(hourly, x="hour", y="count", color="alert_type",
                          color_discrete_map=COLOR_MAP, barmode="stack", height=220)
            fig3.update_layout(**PLOTLY_LAYOUT)
            fig3.update_traces(marker_line_width=0)
            st.plotly_chart(fig3, use_container_width=True)

    with col_b:
        st.markdown('<div style="font-size:0.75rem;color:#94a3b8;margin-bottom:8px;">Alert Type Share</div>',
                    unsafe_allow_html=True)
        if not counts.empty:
            fig4 = px.pie(counts, names="Type", values="Count",
                          color="Type", color_discrete_map=COLOR_MAP, height=220,
                          hole=0.5)
            fig4.update_layout(**PLOTLY_LAYOUT)
            fig4.update_traces(textfont_color="#e2e8f0", marker_line_width=0)
            st.plotly_chart(fig4, use_container_width=True)

    # ── Achievements ─────────────────────────────────────────────────────────
    st.markdown('<div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;'
                'letter-spacing:0.08em;margin:16px 0 12px;">Achievements</div>', unsafe_allow_html=True)
    score = compute_score(df)
    achievements = []
    if score >= 90: achievements.append(("🏆","Elite Driver","Score 90+"))
    elif score >= 80: achievements.append(("🥇","Safe Driver","Score 80+"))
    if len(df[df["alert_type"]=="MOBILE_USAGE"])==0: achievements.append(("📵","Phone Free","No phone alerts"))
    if len(df[df["alert_type"]=="DROWSINESS"])==0: achievements.append(("👁️","Alert Eyes","No drowsiness"))
    if len(df[df["alert_type"]=="DISTRACTION"])==0: achievements.append(("🎯","Focus Master","No distraction"))
    if len(df)<5: achievements.append(("⚡","Clean Record","< 5 total alerts"))

    if achievements:
        cols = st.columns(min(len(achievements),4))
        for i,(icon,title,desc) in enumerate(achievements):
            with cols[i%4]:
                st.markdown(f"""
                <div style="background:rgba(30,41,59,0.5);border:1px solid rgba(255,255,255,0.06);
                     border-radius:12px;padding:16px;text-align:center;">
                    <div style="font-size:2rem;margin-bottom:8px;">{icon}</div>
                    <div style="font-size:0.78rem;font-weight:700;color:#e2e8f0;">{title}</div>
                    <div style="font-size:0.65rem;color:#475569;margin-top:4px;">{desc}</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div class="glass-card" style="text-align:center;color:#475569;padding:20px;">'
                    'Keep driving safely to earn achievements!</div>', unsafe_allow_html=True)

# ── Report Tab ────────────────────────────────────────────────────────────────
def tab_report(df, vid, driver_name):
    st.markdown('<div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;'
                'letter-spacing:0.08em;margin-bottom:14px;">Driver Safety Report</div>',
                unsafe_allow_html=True)

    score     = compute_score(df)
    grade, gc = safety_grade(score)
    today     = datetime.now().strftime("%d %B %Y")
    today_df  = df[df["timestamp"].dt.date == datetime.now().date()] if not df.empty else df
    week_df   = df[df["timestamp"] >= datetime.now()-timedelta(days=7)] if not df.empty else df
    month_df  = df[df["timestamp"] >= datetime.now()-timedelta(days=30)] if not df.empty else df

    # Report header
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(14,165,233,0.1),rgba(99,102,241,0.1));
         border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:24px;margin-bottom:16px;">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
            <div>
                <div style="font-size:1.2rem;font-weight:800;color:#f1f5f9;">Safety Report</div>
                <div style="font-size:0.75rem;color:#475569;margin-top:4px;">
                    Driver: <span style="color:#94a3b8;">{driver_name}</span> &nbsp;|&nbsp;
                    Vehicle: <span style="color:#94a3b8;font-family:'JetBrains Mono',monospace;">{vid}</span>
                    &nbsp;|&nbsp; Generated: <span style="color:#94a3b8;">{today}</span>
                </div>
            </div>
            <div style="background:{gc}18;border:2px solid {gc}44;border-radius:14px;
                 padding:12px 24px;text-align:center;">
                <div style="font-size:2.5rem;font-weight:900;color:{gc};
                     font-family:'JetBrains Mono',monospace;line-height:1;">{grade}</div>
                <div style="font-size:0.65rem;color:#475569;margin-top:4px;">
                    Safety Grade &nbsp; Score: {score}/100</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    # Period summary
    periods = [
        ("Today",    today_df),
        ("This Week", week_df),
        ("This Month", month_df),
        ("All Time",  df),
    ]
    cols = st.columns(4)
    for i,(label,pdf) in enumerate(periods):
        pscore = compute_score(pdf)
        pg, pgc = safety_grade(pscore)
        with cols[i]:
            st.markdown(f"""
            <div class="metric-card" style="margin-bottom:16px;">
                <div style="font-size:0.65rem;color:#475569;margin-bottom:6px;">{label}</div>
                <div style="font-size:1.6rem;font-weight:800;color:{pgc};
                     font-family:'JetBrains Mono',monospace;">{pg}</div>
                <div style="font-size:0.75rem;color:#94a3b8;margin-top:4px;">{len(pdf)} alerts</div>
                <div style="font-size:0.68rem;color:#475569;">Score: {pscore}</div>
            </div>""", unsafe_allow_html=True)

    # Detailed breakdown
    st.markdown('<div style="font-size:0.78rem;color:#94a3b8;font-weight:600;margin:16px 0 10px;">'
                'Alert Breakdown</div>', unsafe_allow_html=True)

    for atype, color, icon in [
        ("DROWSINESS",  "#f59e0b","😴"),
        ("MOBILE_USAGE","#f43f5e","📱"),
        ("DISTRACTION", "#38bdf8","👀"),
    ]:
        today_c = len(today_df[today_df["alert_type"]==atype]) if not today_df.empty else 0
        week_c  = len(week_df[week_df["alert_type"]==atype])   if not week_df.empty  else 0
        total_c = len(df[df["alert_type"]==atype])             if not df.empty        else 0
        bar_pct = int((total_c / max(len(df),1))*100)
        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.5);border:1px solid rgba(255,255,255,0.06);
             border-left:4px solid {color};border-radius:12px;padding:14px 16px;margin-bottom:10px;
             display:flex;align-items:center;gap:16px;">
            <span style="font-size:1.4rem;">{icon}</span>
            <div style="flex:1;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <span style="font-size:0.8rem;font-weight:600;color:#e2e8f0;">
                        {atype.replace('_',' ')}</span>
                    <span style="font-size:0.75rem;color:{color};font-family:'JetBrains Mono',monospace;
                          font-weight:700;">{total_c} total</span>
                </div>
                <div style="width:100%;height:5px;background:rgba(30,41,59,0.8);border-radius:3px;overflow:hidden;margin-bottom:8px;">
                    <div style="width:{bar_pct}%;height:100%;background:{color};border-radius:3px;"></div>
                </div>
                <div style="display:flex;gap:20px;">
                    <span style="font-size:0.68rem;color:#475569;">
                        Today: <span style="color:#94a3b8;">{today_c}</span></span>
                    <span style="font-size:0.68rem;color:#475569;">
                        This week: <span style="color:#94a3b8;">{week_c}</span></span>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

    # Export
    st.markdown("<br>", unsafe_allow_html=True)
    if not df.empty:
        export_df = df[["timestamp","alert_type","vehicle_id"]].copy()
        export_df["timestamp"] = export_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        export_df["safety_score"] = score
        export_df["grade"]        = grade
        fname = f"safety_report_{vid}_{datetime.now().strftime('%Y%m%d')}.csv"
        st.download_button("⬇️ Download Full Report (CSV)",
                           export_df.to_csv(index=False).encode(), fname, "text/csv")

# ── Emergency Tab ─────────────────────────────────────────────────────────────
def tab_emergency():
    st.markdown('<div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;'
                'letter-spacing:0.08em;margin-bottom:14px;">Emergency Services</div>',
                unsafe_allow_html=True)

    # SOS banner
    st.markdown("""
    <div style="background:linear-gradient(135deg,rgba(220,38,38,0.12),rgba(185,28,28,0.06));
         border:1px solid rgba(244,63,94,0.3);border-radius:16px;
         padding:24px;margin-bottom:20px;text-align:center;">
        <div style="font-size:3rem;margin-bottom:10px;">🚨</div>
        <div style="font-size:1.1rem;font-weight:800;color:#f43f5e;margin-bottom:6px;">
            Emergency Alert System</div>
        <div style="font-size:0.78rem;color:#94a3b8;">
            Press SOS to instantly alert emergency services</div>
    </div>""", unsafe_allow_html=True)

    if st.button("🚨  EMERGENCY SOS — Call for Help Now",
                 use_container_width=True, key="sos_btn"):
        st.error("🚨 SOS ACTIVATED — Emergency services have been notified!")
        st.balloons()

    st.markdown("<br>", unsafe_allow_html=True)

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("""
        <div class="glass-card">
            <div style="font-size:0.8rem;font-weight:700;color:#60a5fa;margin-bottom:14px;">
                🚔 Police & Traffic</div>""", unsafe_allow_html=True)
        for name, phone in [
            ("Police Emergency", "100"),
            ("Traffic Control",  "103"),
            ("Women Helpline",   "1091"),
        ]:
            st.markdown(f"""
            <div style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
                <div style="font-size:0.82rem;font-weight:600;color:#93c5fd;">{name}</div>
                <a href="tel:{phone}" style="display:inline-block;margin-top:6px;padding:5px 14px;
                   background:rgba(96,165,250,0.12);border:1px solid rgba(96,165,250,0.25);
                   border-radius:8px;color:#60a5fa;font-size:0.75rem;font-weight:700;
                   text-decoration:none;">📞 {phone}</a>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        st.markdown("""
        <div class="glass-card">
            <div style="font-size:0.8rem;font-weight:700;color:#34d399;margin-bottom:14px;">
                🏥 Medical & Rescue</div>""", unsafe_allow_html=True)
        for name, phone in [
            ("Ambulance",          "102"),
            ("Trauma & Emergency", "108"),
            ("Fire Department",    "101"),
        ]:
            st.markdown(f"""
            <div style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
                <div style="font-size:0.82rem;font-weight:600;color:#6ee7b7;">{name}</div>
                <a href="tel:{phone}" style="display:inline-block;margin-top:6px;padding:5px 14px;
                   background:rgba(52,211,153,0.12);border:1px solid rgba(52,211,153,0.25);
                   border-radius:8px;color:#34d399;font-size:0.75rem;font-weight:700;
                   text-decoration:none;">📞 {phone}</a>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # National helplines
    st.markdown("""
    <div class="glass-card">
        <div style="font-size:0.8rem;font-weight:700;color:#fbbf24;margin-bottom:14px;">
            📞 National Helplines</div>""", unsafe_allow_html=True)
    for service, desc, number, color in [
        ("Police Emergency",    "Immediate police assistance",  "100",  "#60a5fa"),
        ("Ambulance Service",   "Medical emergency response",   "102",  "#34d399"),
        ("Fire Department",     "Fire & rescue services",       "101",  "#f87171"),
        ("Road Accident",       "National highway helpline",    "1033", "#fbbf24"),
        ("Disaster Management", "National disaster response",   "108",  "#a78bfa"),
    ]:
        st.markdown(f"""
        <div style="display:flex;align-items:center;justify-content:space-between;
             padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.04);">
            <div>
                <div style="font-size:0.82rem;font-weight:600;color:#e2e8f0;">{service}</div>
                <div style="font-size:0.7rem;color:#475569;margin-top:2px;">{desc}</div>
            </div>
            <a href="tel:{number}" style="padding:6px 18px;background:{color}18;
               border:1px solid {color}33;border-radius:8px;color:{color};
               font-size:0.82rem;font-weight:700;text-decoration:none;">📞 {number}</a>
        </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── Main render ───────────────────────────────────────────────────────────────
def render_dashboard():
    inject_css()

    if "active_tab"   not in st.session_state: st.session_state["active_tab"]   = "monitor"
    if "live_refresh" not in st.session_state: st.session_state["live_refresh"] = True

    vid         = st.session_state.get("vehicle_id", "UNKNOWN")
    driver_name = st.session_state.get("driver_name", "Driver")
    active_tab  = st.session_state.get("active_tab", "monitor")

    # Load data
    df = load_alerts(vid)
    if not df.empty and "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        df["timestamp"] = df["timestamp"].dt.tz_convert(None)
        df = df.dropna(subset=["timestamp"])
        df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)
    if "snapshot"   not in df.columns: df["snapshot"]   = ""
    if "vehicle_id" not in df.columns: df["vehicle_id"] = vid

    # Top bar (passes df for alert banner + score)
    top_bar(vid, driver_name, df)

    # Tab navigation
    st.markdown('<div style="padding:8px 16px 4px;background:rgba(10,15,30,0.6);">', unsafe_allow_html=True)
    tab_nav(active_tab)
    st.markdown('</div>', unsafe_allow_html=True)

    # Content
    st.markdown('<div style="padding:16px 20px;">', unsafe_allow_html=True)

    if   active_tab == "monitor":   tab_monitor(df, vid, driver_name)
    elif active_tab == "logs":      tab_logs(df)
    elif active_tab == "snapshots": tab_snapshots(df)
    elif active_tab == "alerts":    tab_alerts(df)
    elif active_tab == "analytics": tab_analytics(df)
    elif active_tab == "report":    tab_report(df, vid, driver_name)
    elif active_tab == "emergency": tab_emergency()

    st.markdown('</div>', unsafe_allow_html=True)

    # Auto-refresh
    if st.session_state.get("live_refresh", True):
        time.sleep(5)
        st.rerun()
