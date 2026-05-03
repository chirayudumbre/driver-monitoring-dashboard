import streamlit as st
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="AI Driver Monitoring System",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if st.session_state["logged_in"]:
    from dashboard_main import render_dashboard
    render_dashboard()
else:
    from login_page import render_login
    render_login()
