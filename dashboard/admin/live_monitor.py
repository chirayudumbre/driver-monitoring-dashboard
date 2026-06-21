import streamlit as st
import os
import sys
import json
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

SNAPSHOTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "snapshots"
)
ACTIVE_VEHICLE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "active_vehicle.json"
)

ALERT_COLORS = {
    "DROWSINESS":   "#F59E0B",
    "DISTRACTION":  "#3B82F6",
    "MOBILE_USAGE": "#EF4444",
}


def _get_active_vehicle() -> str:
    try:
        if os.path.exists(ACTIVE_VEHICLE_FILE):
            with open(ACTIVE_VEHICLE_FILE, encoding="utf-8") as f:
                return json.load(f).get("vehicle_id", "UNKNOWN")
    except Exception:
        pass
    return "UNKNOWN"


def _latest_snapshot():
    """Return path to the most recent snapshot file."""
    try:
        if not os.path.exists(SNAPSHOTS_DIR):
            return None
        files = [
            f for f in os.listdir(SNAPSHOTS_DIR)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        if not files:
            return None
        files.sort(reverse=True)
        return os.path.join(SNAPSHOTS_DIR, files[0])
    except Exception:
        return None


def render_live_monitor():
    st.markdown("""
    <style>
    .page-header { font-size:1.4rem;font-weight:800;color:#F1F5F9;margin-bottom:4px; }
    .page-sub    { font-size:0.78rem;color:#64748B;margin-bottom:20px; }
    .stat-card   { background:#1E293B;border:1px solid rgba(255,255,255,0.07);
                   border-radius:12px;padding:14px;text-align:center; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-header">📹 Live Monitor</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Real-time fleet monitoring (camera runs via main.py)</div>',
                unsafe_allow_html=True)

    # Info banner
    st.info(
        "🎥 Live monitoring runs via **main.py**. "
        "This page shows the latest captured snapshot and recent alerts."
    )

    # Active vehicle
    active_vid = _get_active_vehicle()
    st.markdown(f"""
    <div style="background:#1E293B;border:1px solid rgba(59,130,246,0.3);
         border-radius:10px;padding:12px 18px;margin-bottom:16px;
         display:flex;align-items:center;gap:10px;">
        <span style="font-size:1.2rem;">🚗</span>
        <div>
            <div style="font-size:0.72rem;color:#64748B;text-transform:uppercase;letter-spacing:0.06em;">
                Currently Monitored Vehicle</div>
            <div style="font-size:1.1rem;font-weight:700;color:#93C5FD;font-family:monospace;">
                {active_vid}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_snap, col_alerts = st.columns([1, 1])

    # ── Latest Snapshot ─────────────────────────────────────────────────────
    with col_snap:
        st.markdown("**📸 Latest Snapshot**")
        snap = _latest_snapshot()
        if snap:
            try:
                from PIL import Image
                img = Image.open(snap)
                st.image(img, use_container_width=True, caption=os.path.basename(snap))
            except Exception:
                st.image(snap, use_container_width=True)
        else:
            st.markdown("""
            <div style="height:220px;background:#0F172A;border-radius:10px;
                 border:1px dashed rgba(255,255,255,0.1);
                 display:flex;align-items:center;justify-content:center;
                 color:#475569;font-size:0.85rem;">
                No snapshots captured yet
            </div>
            """, unsafe_allow_html=True)

    # ── Last 5 Alerts ───────────────────────────────────────────────────────
    with col_alerts:
        st.markdown("**🔔 Last 5 Alerts**")
        try:
            from db import load_alerts
            df = load_alerts()
            if not df.empty:
                recent = df.head(5)
                for _, row in recent.iterrows():
                    atype   = row.get("alert_type", "")
                    color   = ALERT_COLORS.get(atype, "#64748B")
                    ts      = str(row.get("timestamp", ""))[:19]
                    vid_str = row.get("vehicle_id", "")
                    label   = atype.replace("_", " ").title()
                    st.markdown(f"""
                    <div style="background:#0F172A;border-left:3px solid {color};
                         border-radius:8px;padding:10px 12px;margin-bottom:8px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <span style="color:{color};font-weight:600;font-size:0.85rem;">{label}</span>
                            <span style="color:#64748B;font-size:0.7rem;">{ts}</span>
                        </div>
                        <div style="color:#64748B;font-size:0.72rem;margin-top:2px;">🚗 {vid_str}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No alerts yet.")
        except Exception as e:
            st.warning(f"Could not load alerts: {e}")

    # ── Today's Stats ────────────────────────────────────────────────────────
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown("**📊 Today's Detection Stats**")

    try:
        from db import load_alerts
        df = load_alerts()
        today = pd.Timestamp.now().date()
        if not df.empty and "timestamp" in df.columns:
            today_df = df[df["timestamp"].dt.date == today]
        else:
            today_df = pd.DataFrame()

        drowsy_c = len(today_df[today_df["alert_type"] == "DROWSINESS"])  if not today_df.empty else 0
        phone_c  = len(today_df[today_df["alert_type"] == "MOBILE_USAGE"]) if not today_df.empty else 0
        dist_c   = len(today_df[today_df["alert_type"] == "DISTRACTION"]) if not today_df.empty else 0
    except Exception:
        drowsy_c = phone_c = dist_c = 0

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.markdown(f"""
        <div class="stat-card">
            <div style="font-size:1.6rem;font-weight:800;color:#F59E0B;">{drowsy_c}</div>
            <div style="font-size:0.72rem;color:#64748B;">😴 Drowsy Events</div>
        </div>""", unsafe_allow_html=True)
    with sc2:
        st.markdown(f"""
        <div class="stat-card">
            <div style="font-size:1.6rem;font-weight:800;color:#EF4444;">{phone_c}</div>
            <div style="font-size:0.72rem;color:#64748B;">📱 Phone Events</div>
        </div>""", unsafe_allow_html=True)
    with sc3:
        st.markdown(f"""
        <div class="stat-card">
            <div style="font-size:1.6rem;font-weight:800;color:#3B82F6;">{dist_c}</div>
            <div style="font-size:0.72rem;color:#64748B;">👀 Distraction Events</div>
        </div>""", unsafe_allow_html=True)

    # Auto-refresh
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    col_r, col_info = st.columns([1, 3])
    with col_r:
        if st.button("🔄 Refresh Now", use_container_width=True, key="lm_refresh"):
            st.rerun()
    with col_info:
        st.markdown(
            '<div style="color:#475569;font-size:0.75rem;padding-top:8px;">'
            f'Last updated: {datetime.now().strftime("%H:%M:%S")} — '
            'Click Refresh for latest data</div>',
            unsafe_allow_html=True,
        )

    # Auto-refresh every 5 seconds
    try:
        import time
        if st.session_state.get("lm_auto_refresh", False):
            time.sleep(5)
            st.rerun()
    except Exception:
        pass

    auto = st.checkbox("⚡ Auto-refresh every 5s", key="lm_auto_refresh")
