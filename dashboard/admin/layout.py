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


def load_vehicles() -> dict:
    """Load vehicles from Supabase only. Returns empty dict if none registered."""
    try:
        from utils.supabase_client import fetch_vehicles
        rows = fetch_vehicles()
        # Convert list to dict keyed by vehicle_number for backward compat
        return {r["vehicle_number"]: r for r in rows if r.get("vehicle_number")}
    except Exception:
        return {}


def load_drivers() -> dict:
    """Load drivers from Supabase only. Returns empty dict if none registered."""
    try:
        from utils.supabase_client import fetch_drivers
        rows = fetch_drivers()
        return {r["username"]: r for r in rows if r.get("username")}
    except Exception:
        return {}


PAGES = [
    ("📊", "Dashboard"),
    ("🚗", "Vehicles"),
    ("👤", "Drivers"),
    ("🔔", "Alerts"),
    ("📷", "Snapshots"),
    ("📄", "Reports"),
    ("📹", "Live Monitor"),
    ("⚙️", "Settings"),
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


def render_admin():
    st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)

    if "admin_page" not in st.session_state:
        st.session_state["admin_page"] = "Dashboard"

    with st.sidebar:
        st.markdown("""
        <div style="padding:16px 8px 8px;text-align:center;">
            <div style="display:inline-flex;align-items:center;justify-content:center;
                 width:52px;height:52px;border-radius:14px;
                 background:linear-gradient(135deg,#3B82F6,#6366F1);
                 box-shadow:0 0 20px rgba(59,130,246,0.3);margin-bottom:8px;">
                <span style="font-size:1.5rem;">🛡️</span>
            </div>
            <div style="font-size:1rem;font-weight:700;color:#F1F5F9;">Admin Panel</div>
            <div style="font-size:0.7rem;color:#64748B;margin-top:2px;">AI Driver Monitoring</div>
        </div>
        <hr style="border:none;border-top:1px solid rgba(255,255,255,0.06);margin:8px 0 12px;">
        """, unsafe_allow_html=True)

        for icon, page in PAGES:
            is_active = st.session_state["admin_page"] == page
            bg = "#3B82F6" if is_active else "transparent"
            weight = "700" if is_active else "500"
            opacity = "1" if is_active else "0.7"

            if st.button(
                f"{icon}  {page}",
                key=f"nav_{page}",
                use_container_width=True,
            ):
                if page == "Logout":
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.session_state["admin_page"] = page
                    st.rerun()

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # Cloud status
        try:
            connected = is_cloud_connected()
            status_dot = "🟢" if connected else "🔴"
            status_txt = "Cloud Connected" if connected else "Local Mode"
        except Exception:
            status_dot = "🔴"
            status_txt = "Local Mode"

        st.markdown(f"""
        <div style="margin:8px;padding:8px 12px;background:rgba(15,23,42,0.5);
             border-radius:8px;font-size:0.72rem;color:#64748B;text-align:center;">
            {status_dot} {status_txt}
        </div>
        """, unsafe_allow_html=True)

    # Load data
    try:
        df = load_alerts()
    except Exception:
        import pandas as pd
        df = pd.DataFrame(columns=["timestamp", "alert_type", "vehicle_id", "snapshot"])

    vehicles = load_vehicles()
    drivers  = load_drivers()

    page = st.session_state["admin_page"]

    try:
        if page == "Dashboard":
            from admin.dashboard import render_admin_dashboard
            render_admin_dashboard(df, vehicles, drivers)

        elif page == "Vehicles":
            from admin.vehicles import render_vehicles
            render_vehicles(vehicles)

        elif page == "Drivers":
            from admin.drivers import render_drivers
            render_drivers(vehicles)

        elif page == "Alerts":
            from admin.alerts import render_alerts
            render_alerts(df)

        elif page == "Snapshots":
            from admin.snapshots import render_snapshots
            render_snapshots(df)

        elif page == "Reports":
            from admin.reports import render_reports
            render_reports(df, vehicles, drivers)

        elif page == "Live Monitor":
            from admin.live_monitor import render_live_monitor
            render_live_monitor()

        elif page == "Settings":
            from admin.settings import render_settings
            render_settings()

    except Exception as e:
        st.error(f"Error loading page '{page}': {e}")
        import traceback
        st.code(traceback.format_exc())
