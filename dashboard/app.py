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

# Inject PWA manifest + theme color for mobile home screen icon
st.markdown("""
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#3B82F6">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="DriverAI">
<link rel="apple-touch-icon" href="https://img.icons8.com/fluency/192/shield.png">
""", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None

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
