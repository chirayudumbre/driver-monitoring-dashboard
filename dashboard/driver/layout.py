import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

BASE = os.path.dirname(os.path.abspath(__file__))

try:
    from db import load_alerts, is_cloud_connected
except Exception:
    sys.path.insert(0, os.path.join(BASE, ".."))
    from db import load_alerts, is_cloud_connected


PAGES = [
    ("📊", "Dashboard"),
    ("📹", "Live Monitor"),
    ("🔔", "Alerts"),
    ("📷", "Snapshots"),
    ("📄", "Reports"),
    ("🆘", "Emergency"),
    ("🚪", "Logout"),
]

SIDEBAR_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
[data-testid="stSidebar"] {
    background: #1E293B !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stSidebar"] * { color: #F1F5F9 !important; }
.stApp { background: #0F172A !important; }
section.main { background: #0F172A !important; }
.block-container { padding-top: 1.5rem !important; }
</style>
"""


def render_driver():
    st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)

    if "driver_page" not in st.session_state:
        st.session_state["driver_page"] = "Dashboard"

    vid         = st.session_state.get("vehicle_id",  "UNKNOWN")
    driver_name = st.session_state.get("driver_name", "Driver")

    with st.sidebar:
        st.markdown(f"""
        <div style="padding:16px 8px 8px;text-align:center;">
            <div style="display:inline-flex;align-items:center;justify-content:center;
                 width:52px;height:52px;border-radius:50%;
                 background:linear-gradient(135deg,#10B981,#3B82F6);
                 box-shadow:0 0 20px rgba(16,185,129,0.3);margin-bottom:8px;
                 font-size:1.6rem;">👤</div>
            <div style="font-size:0.95rem;font-weight:700;color:#F1F5F9;">{driver_name}</div>
            <div style="font-size:0.7rem;color:#64748B;margin-top:2px;font-family:monospace;">{vid}</div>
        </div>
        <hr style="border:none;border-top:1px solid rgba(255,255,255,0.06);margin:8px 0 12px;">
        """, unsafe_allow_html=True)

        for icon, page in PAGES:
            if st.button(f"{icon}  {page}", key=f"dnav_{page}", use_container_width=True):
                if page == "Logout":
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
                else:
                    st.session_state["driver_page"] = page
                    st.rerun()

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # Cloud status
        try:
            connected = is_cloud_connected()
            status_dot = "🟢" if connected else "🔴"
            status_txt = "Cloud" if connected else "Local"
        except Exception:
            status_dot = "🔴"
            status_txt = "Local"

        st.markdown(f"""
        <div style="margin:8px;padding:8px 12px;background:rgba(15,23,42,0.5);
             border-radius:8px;font-size:0.72rem;color:#64748B;text-align:center;">
            {status_dot} {status_txt}
        </div>
        """, unsafe_allow_html=True)

    # Load data for this vehicle only
    try:
        df = load_alerts(vehicle_id=vid)
    except Exception:
        import pandas as pd
        df = pd.DataFrame(columns=["timestamp", "alert_type", "vehicle_id", "snapshot"])

    page = st.session_state["driver_page"]

    try:
        if page == "Dashboard":
            from driver.dashboard import render_driver_dashboard
            render_driver_dashboard(df, vid, driver_name)

        elif page == "Live Monitor":
            from driver.live_monitor import render_driver_live_monitor
            render_driver_live_monitor(vid)

        elif page == "Alerts":
            from driver.alerts import render_driver_alerts
            render_driver_alerts(df, vid)

        elif page == "Snapshots":
            from driver.snapshots import render_driver_snapshots
            render_driver_snapshots(df, vid)

        elif page == "Reports":
            from driver.reports import render_driver_reports
            render_driver_reports(df, vid, driver_name)

        elif page == "Emergency":
            from driver.emergency import render_emergency
            render_emergency()

    except Exception as e:
        st.error(f"Error loading page '{page}': {e}")
        import traceback
        st.code(traceback.format_exc())
