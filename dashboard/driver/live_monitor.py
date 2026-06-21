import streamlit as st
import os
import sys
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

SNAPSHOTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "snapshots"
)

ALERT_COLORS = {
    "DROWSINESS":   "#F59E0B",
    "DISTRACTION":  "#3B82F6",
    "MOBILE_USAGE": "#EF4444",
}


def _latest_snapshot(vid: str = None):
    """Return path to the most recent snapshot file for this vehicle."""
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


def render_driver_live_monitor(vid: str):
    st.markdown("""
    <style>
    .page-header { font-size:1.4rem;font-weight:800;color:#F1F5F9;margin-bottom:4px; }
    .page-sub    { font-size:0.78rem;color:#64748B;margin-bottom:20px; }
    .status-dot  { display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-header">📹 Live Monitor</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-sub">Real-time monitoring for vehicle {vid}</div>',
                unsafe_allow_html=True)

    st.info("🎥 Live detection runs via **main.py**. This page shows your latest snapshot and recent alerts.")

    col_snap, col_alerts = st.columns([1, 1])

    with col_snap:
        st.markdown("**📸 Latest Snapshot**")
        snap = _latest_snapshot(vid)
        if snap:
            try:
                from PIL import Image
                img = Image.open(snap)
                st.image(img, use_container_width=True, caption=os.path.basename(snap))
            except Exception:
                st.image(snap, use_container_width=True)
        else:
            st.markdown("""
            <div style="height:200px;background:#0F172A;border-radius:10px;
                 border:1px dashed rgba(255,255,255,0.1);
                 display:flex;align-items:center;justify-content:center;
                 color:#475569;font-size:0.85rem;">
                No snapshots captured yet
            </div>
            """, unsafe_allow_html=True)

    with col_alerts:
        st.markdown("**🔔 Last 5 Alerts**")
        try:
            from db import load_alerts
            df = load_alerts(vehicle_id=vid)
            if not df.empty:
                recent = df.head(5)
                for _, row in recent.iterrows():
                    atype = row.get("alert_type", "")
                    color = ALERT_COLORS.get(atype, "#64748B")
                    ts    = str(row.get("timestamp", ""))[:19]
                    label = atype.replace("_", " ").title()
                    st.markdown(f"""
                    <div style="background:#0F172A;border-left:3px solid {color};
                         border-radius:8px;padding:10px 12px;margin-bottom:8px;">
                        <div style="color:{color};font-weight:600;font-size:0.85rem;">{label}</div>
                        <div style="color:#64748B;font-size:0.72rem;margin-top:2px;">⏱ {ts}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No alerts for your vehicle yet.")
        except Exception as e:
            st.warning(f"Could not load alerts: {e}")

    # Detection status indicators
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown("**🔍 Detection Status**")

    try:
        from db import load_alerts
        df = load_alerts(vehicle_id=vid)
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

    ds1, ds2, ds3 = st.columns(3)
    for col, label, count, color, icon in [
        (ds1, "Drowsy Events",   drowsy_c, "#F59E0B", "😴"),
        (ds2, "Phone Events",    phone_c,  "#EF4444", "📱"),
        (ds3, "Distract Events", dist_c,   "#3B82F6", "👀"),
    ]:
        with col:
            dot_color = color if count > 0 else "#10B981"
            st.markdown(f"""
            <div style="background:#1E293B;border:1px solid rgba(255,255,255,0.07);
                 border-radius:12px;padding:14px;text-align:center;">
                <div style="font-size:1.5rem;font-weight:800;color:{color};">{count}</div>
                <div style="font-size:0.72rem;color:#64748B;">{icon} {label}</div>
            </div>
            """, unsafe_allow_html=True)

    # Refresh
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    col_r, col_info = st.columns([1, 3])
    with col_r:
        if st.button("🔄 Refresh", use_container_width=True, key="dlm_refresh"):
            st.rerun()
    with col_info:
        st.markdown(
            f'<div style="color:#475569;font-size:0.75rem;padding-top:8px;">'
            f'Last updated: {datetime.now().strftime("%H:%M:%S")}</div>',
            unsafe_allow_html=True,
        )

    auto = st.checkbox("⚡ Auto-refresh every 5s", key="dlm_auto")
    if auto:
        import time
        time.sleep(5)
        st.rerun()
