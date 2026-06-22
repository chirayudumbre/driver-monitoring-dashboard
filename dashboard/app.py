import streamlit as st
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="AI Driver Monitoring System",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── PWA manifest ──────────────────────────────────────────────────────────────
st.markdown("""
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#3B82F6">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="DriverAI">
<link rel="apple-touch-icon" href="https://img.icons8.com/fluency/192/shield.png">
""", unsafe_allow_html=True)

# ── Session state defaults ────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None

# ── Restore session from query params on refresh ──────────────────────────────
# When user logs in we set query params. On refresh Streamlit keeps query params
# so we can restore the session automatically.
params = st.query_params

if not st.session_state["logged_in"]:
    role = params.get("role", "")
    if role in ("admin", "driver"):
        # Validate the token matches what we stored
        token = params.get("token", "")
        vid   = params.get("vid", "UNKNOWN")
        name  = params.get("name", "Driver")

        # Simple token validation — check token exists and matches role
        import hashlib
        expected = hashlib.md5(f"{role}:{vid}:driver_monitor_2026".encode()).hexdigest()[:12]

        if token == expected:
            st.session_state["logged_in"]   = True
            st.session_state["role"]        = role
            st.session_state["vehicle_id"]  = vid
            st.session_state["driver_name"] = name
            if role == "admin":
                if "admin_page" not in st.session_state:
                    st.session_state["admin_page"] = "Dashboard"
            else:
                if "driver_page" not in st.session_state:
                    st.session_state["driver_page"] = "Dashboard"

# ── Route ─────────────────────────────────────────────────────────────────────
if not st.session_state["logged_in"]:
    from login_page import render_login
    render_login()
    st.stop()
elif st.session_state["role"] == "admin":
    from admin.layout import render_admin
    render_admin()
else:
    from driver.layout import render_driver
    render_driver()
