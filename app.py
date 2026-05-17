"""
Root-level entry point for Streamlit Cloud deployment.
Streamlit Cloud requires the main file to be at the repo root.
"""
import os
import sys

# Make sure dashboard/ and project root are on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "dashboard"))
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

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
