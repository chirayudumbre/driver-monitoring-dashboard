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
