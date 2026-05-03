import streamlit as st
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
from utils.config import set_active_vehicle

USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        out = {}
        for k, v in raw.items():
            out[k] = v if isinstance(v, dict) else {"password": v, "driver": k}
        return out
    return {}

def save_users(u):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(u, f, indent=4)

def render_login():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&display=swap');
    html,body,[class*="css"]{font-family:'Outfit',sans-serif!important;background:#020617!important;}
    #MainMenu,footer,header{visibility:hidden;}
    .block-container{padding:0!important;max-width:100%!important;}
    [data-testid="stSidebar"]{display:none!important;}
    .stTextInput input{
        background:rgba(30,41,59,0.8)!important;
        border:1px solid rgba(100,116,139,0.4)!important;
        border-radius:10px!important;color:white!important;
        font-family:'Outfit',sans-serif!important;
    }
    .stButton>button{
        background:linear-gradient(135deg,#0ea5e9,#6366f1)!important;
        color:white!important;border:none!important;border-radius:10px!important;
        font-weight:600!important;font-size:0.9rem!important;
        padding:10px!important;transition:all 0.3s!important;
    }
    .stRadio>div{gap:8px!important;}
    .stRadio label{color:#94a3b8!important;font-size:0.85rem!important;}
    </style>
    """, unsafe_allow_html=True)

    # Center the login card
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

        # Logo
        st.markdown("""
        <div style="text-align:center;margin-bottom:24px;">
            <div style="display:inline-flex;align-items:center;justify-content:center;
                 width:72px;height:72px;border-radius:18px;
                 background:linear-gradient(135deg,#0ea5e9,#6366f1);
                 box-shadow:0 0 40px rgba(56,189,248,0.4);margin-bottom:14px;">
                <span style="font-size:2rem;">🛡️</span>
            </div>
            <div style="font-size:1.5rem;font-weight:800;
                background:linear-gradient(135deg,#7dd3fc,#a5b4fc);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                AI Driver Monitoring
            </div>
            <div style="color:#475569;font-size:0.7rem;margin-top:4px;
                text-transform:uppercase;letter-spacing:0.12em;">
                Real-time Safety Intelligence
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Card
        st.markdown("""
        <div style="background:rgba(15,23,42,0.7);border:1px solid rgba(255,255,255,0.08);
             border-radius:16px;padding:28px 24px;">
        """, unsafe_allow_html=True)

        mode = st.radio("Mode", ["Sign In", "Register"], horizontal=True,
                        label_visibility="hidden", key="auth_mode")

        if mode == "Sign In":
            vid = st.text_input("Vehicle Number", placeholder="e.g. MH12AB1234", key="si_v").strip().upper()
            pwd = st.text_input("Password", type="password", placeholder="Enter password", key="si_p")
            if st.button("🚀  Access Dashboard", use_container_width=True, key="si_go"):
                users = load_users()
                entry = users.get(vid)
                stored = entry.get("password","") if isinstance(entry, dict) else str(entry or "")
                if entry and stored == pwd:
                    st.session_state["logged_in"]   = True
                    st.session_state["vehicle_id"]  = vid
                    st.session_state["driver_name"] = entry.get("driver", vid) if isinstance(entry, dict) else vid
                    st.session_state["active_tab"]  = "monitor"
                    set_active_vehicle(vid)
                    st.rerun()
                else:
                    st.error("Invalid vehicle number or password.")
        else:
            vid  = st.text_input("Vehicle Number", placeholder="e.g. MH12AB1234", key="rg_v").strip().upper()
            name = st.text_input("Driver Name", placeholder="Full name", key="rg_n")
            pwd  = st.text_input("Password", type="password", placeholder="Create password", key="rg_p")
            if st.button("✅  Register Vehicle", use_container_width=True, key="rg_go"):
                if not vid or not name or not pwd:
                    st.warning("Fill all fields.")
                elif len(pwd) < 4:
                    st.error("Password must be at least 4 characters.")
                else:
                    users = load_users()
                    if vid in users:
                        st.error("Vehicle already registered.")
                    else:
                        users[vid] = {"driver": name, "password": pwd}
                        save_users(users)
                        st.success(f"✅ Registered! Sign in with {vid}")

        st.markdown("</div>", unsafe_allow_html=True)
