"""
Login page — credentials stored in Supabase.
"""
import streamlit as st
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

try:
    from utils.config import set_active_vehicle
except Exception:
    def set_active_vehicle(v): pass

try:
    from utils.supabase_client import (
        admin_exists, create_admin, verify_admin,
        verify_vehicle, verify_driver, test_connection,
    )
    CLOUD_AUTH = True
except Exception:
    CLOUD_AUTH = False

BASE       = os.path.dirname(__file__)
USERS_FILE = os.path.join(BASE, "users.json")


def load_users() -> dict:
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, encoding="utf-8") as f:
                raw = json.load(f)
            return {k: (v if isinstance(v, dict) else {"password": v, "driver": k})
                    for k, v in raw.items()}
        except Exception:
            return {}
    return {}


# ─────────────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

*, html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    box-sizing: border-box;
}

body, .stApp { background: #060B18 !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stSidebar"] { display: none !important; }

/* Input fields */
.stTextInput > div > div > input {
    background: #0F172A !important;
    border: 1.5px solid #1E293B !important;
    border-radius: 12px !important;
    color: #F1F5F9 !important;
    font-size: 0.9rem !important;
    padding: 12px 16px !important;
    transition: border-color 0.2s !important;
}
.stTextInput > div > div > input:focus {
    border-color: #3B82F6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
    outline: none !important;
}
.stTextInput > label {
    color: #64748B !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    margin-bottom: 6px !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
    padding: 14px 24px !important;
    letter-spacing: 0.02em !important;
    transition: all 0.25s ease !important;
    width: 100% !important;
    box-shadow: 0 4px 20px rgba(37,99,235,0.35) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(37,99,235,0.5) !important;
}
.stButton > button:active {
    transform: translateY(0px) !important;
}

/* Radio buttons */
.stRadio > div {
    display: flex !important;
    gap: 8px !important;
    flex-direction: row !important;
}
.stRadio label {
    background: #0F172A !important;
    border: 1.5px solid #1E293B !important;
    border-radius: 10px !important;
    padding: 8px 18px !important;
    color: #64748B !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    transition: all 0.2s !important;
}
.stRadio label:has(input:checked) {
    background: rgba(37,99,235,0.15) !important;
    border-color: #3B82F6 !important;
    color: #93C5FD !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #0F172A !important;
    border-radius: 12px !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1.5px solid #1E293B !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 9px !important;
    color: #475569 !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 8px 20px !important;
    transition: all 0.2s !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #2563EB, #4F46E5) !important;
    color: white !important;
    box-shadow: 0 2px 10px rgba(37,99,235,0.4) !important;
}
.stTabs [data-baseweb="tab-panel"] {
    padding-top: 20px !important;
}

/* Alerts */
.stAlert { border-radius: 10px !important; }

/* Selectbox */
.stSelectbox > div > div {
    background: #0F172A !important;
    border: 1.5px solid #1E293B !important;
    border-radius: 12px !important;
    color: #F1F5F9 !important;
}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
def _page_frame():
    """Inject CSS + full-page background."""
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown("""
    <div style="
        position:fixed;inset:0;z-index:-1;
        background: radial-gradient(ellipse 80% 60% at 50% -10%,
            rgba(37,99,235,0.18) 0%, transparent 70%),
        radial-gradient(ellipse 60% 40% at 80% 90%,
            rgba(79,70,229,0.12) 0%, transparent 70%),
        #060B18;
    "></div>
    """, unsafe_allow_html=True)


def _hide_streamlit_chrome():
    """Hide all Streamlit UI chrome — header, footer, toolbar, deploy button."""
    st.markdown("""
    <style>
    #root > div:first-child { background: #060B18 !important; }
    .stDeployButton, [data-testid="stToolbar"],
    [data-testid="stDecoration"], [data-testid="stStatusWidget"],
    [data-testid="manage-app-button"] { display: none !important; }
    .stApp > header { display: none !important; }
    .stApp { background: #060B18 !important; }
    .main .block-container {
        padding: 0 !important;
        max-width: 480px !important;
        margin: 0 auto !important;
    }
    </style>
    """, unsafe_allow_html=True)


def _logo():
    st.markdown("""
    <div style="text-align:center; padding: 8px 0 28px;">
        <div style="
            display:inline-flex; align-items:center; justify-content:center;
            width:72px; height:72px; border-radius:20px;
            background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%);
            box-shadow: 0 0 40px rgba(37,99,235,0.45), 0 0 80px rgba(79,70,229,0.2);
            margin-bottom:18px;
        ">
            <span style="font-size:2rem; filter:drop-shadow(0 2px 4px rgba(0,0,0,0.3));">&#128737;</span>
        </div>
        <div style="
            font-size:2rem; font-weight:900; letter-spacing:-0.03em;
            color:#E2E8F0;
            line-height:1.1; margin-bottom:8px;
        ">AI Driver Monitoring</div>
        <div style="
            font-size:0.7rem; font-weight:700; letter-spacing:0.2em;
            color:#334155; text-transform:uppercase;
        ">Real-Time Safety Intelligence System</div>
        <div style="
            display:flex; justify-content:center; gap:8px;
            margin-top:18px; flex-wrap:wrap;
        ">
            <span style="background:rgba(37,99,235,0.12);color:#60A5FA;border:1px solid rgba(96,165,250,0.2);
                  padding:5px 14px;border-radius:20px;font-size:0.72rem;font-weight:600;">
                Drowsiness
            </span>
            <span style="background:rgba(79,70,229,0.12);color:#A5B4FC;border:1px solid rgba(165,180,252,0.2);
                  padding:5px 14px;border-radius:20px;font-size:0.72rem;font-weight:600;">
                Distraction
            </span>
            <span style="background:rgba(220,38,38,0.1);color:#FCA5A5;border:1px solid rgba(252,165,165,0.2);
                  padding:5px 14px;border-radius:20px;font-size:0.72rem;font-weight:600;">
                Phone Detection
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _card_open():
    st.markdown(
        '<div style="background:rgba(15,23,42,0.7);border:1.5px solid rgba(255,255,255,0.07);'
        'border-radius:20px;padding:28px 28px 24px;backdrop-filter:blur(24px);'
        'box-shadow:0 32px 64px rgba(0,0,0,0.6);">',
        unsafe_allow_html=True
    )


def _card_close():
    st.markdown("</div>", unsafe_allow_html=True)


def _divider(text: str):
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;margin:16px 0;">'
        f'<div style="flex:1;height:1px;background:rgba(255,255,255,0.06);"></div>'
        f'<span style="font-size:0.7rem;color:#334155;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:0.08em;">{text}</span>'
        f'<div style="flex:1;height:1px;background:rgba(255,255,255,0.06);"></div>'
        f'</div>',
        unsafe_allow_html=True
    )


def _connection_badge():
    if CLOUD_AUTH:
        try:
            connected = test_connection()
            dot = "#10B981" if connected else "#EF4444"
            msg = "Supabase Connected" if connected else "Offline — Local Mode"
        except Exception:
            dot, msg = "#EF4444", "Offline — Local Mode"
    else:
        dot, msg = "#EF4444", "Local Mode"

    st.markdown(
        f'<div style="text-align:center;margin-top:18px;">'
        f'<span style="display:inline-flex;align-items:center;gap:6px;'
        f'font-size:0.7rem;color:#334155;font-weight:500;">'
        f'<span style="width:7px;height:7px;border-radius:50%;background:{dot};'
        f'display:inline-block;box-shadow:0 0 6px {dot};"></span>'
        f'{msg}</span></div>',
        unsafe_allow_html=True
    )


# ── First-time setup ──────────────────────────────────────────────────────────
def render_setup():
    _page_frame()
    _hide_streamlit_chrome()
    _, mid, _ = st.columns([1, 1.0, 1])
    with mid:
        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
        _logo()

        st.markdown("""
        <div style="
            background: rgba(16,185,129,0.08);
            border: 1.5px solid rgba(16,185,129,0.2);
            border-radius: 14px; padding: 14px 18px; margin-bottom: 20px;
        ">
            <div style="font-size:0.95rem;font-weight:700;color:#34D399;margin-bottom:4px;">
                🎉 Welcome — First Time Setup
            </div>
            <div style="font-size:0.78rem;color:#64748B;line-height:1.5;">
                No admin account exists yet. Create one to unlock the full platform.
                Your credentials will be stored securely in Supabase.
            </div>
        </div>
        """, unsafe_allow_html=True)

        _card_open()
        st.markdown("""
        <div style="font-size:1.05rem;font-weight:800;color:#F1F5F9;margin-bottom:20px;">
            Create Admin Account
        </div>
        """, unsafe_allow_html=True)

        username = st.text_input("Admin Username", placeholder="e.g. admin", key="setup_user")
        pwd1     = st.text_input("Password", type="password",
                                 placeholder="Minimum 6 characters", key="setup_p1")
        pwd2     = st.text_input("Confirm Password", type="password",
                                 placeholder="Repeat your password", key="setup_p2")

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        if st.button("✅  Create Admin Account", key="setup_go"):
            u = username.strip()
            if not u or not pwd1 or not pwd2:
                st.warning("Please fill all fields.")
            elif len(u) < 3:
                st.error("Username must be at least 3 characters.")
            elif len(pwd1) < 6:
                st.error("Password must be at least 6 characters.")
            elif pwd1 != pwd2:
                st.error("Passwords do not match.")
            else:
                ok = create_admin(u, pwd1) if CLOUD_AUTH else False
                if ok:
                    st.success(f"✅ Admin '{u}' created! Please sign in.")
                    st.rerun()
                else:
                    st.error("Could not save to Supabase. Check your connection.")

        _card_close()
        _connection_badge()


# ── Normal login ──────────────────────────────────────────────────────────────
def render_login():
    if CLOUD_AUTH:
        try:
            if not admin_exists():
                render_setup()
                return
        except Exception:
            pass

    _page_frame()
    _hide_streamlit_chrome()
    _, mid, _ = st.columns([1, 1.0, 1])
    with mid:
        st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)
        _logo()
        _card_open()

        admin_tab, driver_tab = st.tabs(["🔐  Admin Portal", "🚗  Driver Portal"])

        # ── Admin Tab ─────────────────────────────────────────────────────────
        with admin_tab:
            st.markdown("""
            <div style="font-size:0.78rem;color:#475569;margin-bottom:16px;line-height:1.5;">
                Sign in with your administrator credentials to access the
                fleet management dashboard.
            </div>
            """, unsafe_allow_html=True)

            a_user = st.text_input("Username", placeholder="Admin username", key="a_user")
            a_pass = st.text_input("Password", type="password",
                                   placeholder="Enter your password", key="a_pass")
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            if st.button("🔐  Sign In as Admin", key="a_go"):
                if not a_user or not a_pass:
                    st.warning("Please enter your username and password.")
                else:
                    ok = verify_admin(a_user.strip(), a_pass) if CLOUD_AUTH else False
                    if ok:
                        import hashlib
                        token = hashlib.md5(f"admin:admin:driver_monitor_2026".encode()).hexdigest()[:12]
                        st.session_state.update({
                            "logged_in":  True,
                            "role":       "admin",
                            "admin_page": "Dashboard",
                        })
                        st.query_params["role"]  = "admin"
                        st.query_params["vid"]   = "admin"
                        st.query_params["name"]  = "Admin"
                        st.query_params["token"] = token
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

        # ── Driver Tab ────────────────────────────────────────────────────────
        with driver_tab:
            st.markdown("""
            <div style="font-size:0.78rem;color:#475569;margin-bottom:16px;line-height:1.5;">
                Sign in with your vehicle number and password assigned by your administrator.
            </div>
            """, unsafe_allow_html=True)

            d_vid  = st.text_input("Vehicle Number",
                                   placeholder="e.g. MH12AB1234", key="d_vid")
            d_pass = st.text_input("Password", type="password",
                                   placeholder="Your password", key="d_vpass")
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            if st.button("🚗  Sign In as Driver", key="d_go"):
                vid = d_vid.strip().upper()
                if not vid or not d_pass:
                    st.warning("Please enter your vehicle number and password.")
                else:
                    driver_row = None

                    # Try Supabase vehicles table
                    if CLOUD_AUTH:
                        try:
                            driver_row = verify_vehicle(vid, d_pass)
                        except Exception:
                            pass

                    # Fallback: local users.json
                    if driver_row is None:
                        try:
                            users = load_users()
                            entry = users.get(vid)
                            if entry:
                                stored = entry.get("password", "") if isinstance(entry, dict) else str(entry)
                                if stored == d_pass:
                                    driver_row = {
                                        "vehicle_number": vid,
                                        "driver_name": entry.get("driver", vid)
                                            if isinstance(entry, dict) else vid
                                    }
                        except Exception:
                            pass

                    if driver_row:
                        name = driver_row.get("driver_name", vid)
                        import hashlib
                        token = hashlib.md5(f"driver:{vid}:driver_monitor_2026".encode()).hexdigest()[:12]
                        st.session_state.update({
                            "logged_in":   True,
                            "role":        "driver",
                            "vehicle_id":  vid,
                            "driver_name": name,
                            "driver_page": "Dashboard",
                        })
                        st.query_params["role"]  = "driver"
                        st.query_params["vid"]   = vid
                        st.query_params["name"]  = name
                        st.query_params["token"] = token
                        try:
                            set_active_vehicle(vid)
                        except Exception:
                            pass
                        st.rerun()
                    else:
                        st.error("Invalid vehicle number or password. Contact your admin.")

            _divider("or sign in with username")

            d_uname = st.text_input("Driver Username",
                                    placeholder="Username assigned by admin", key="d_uname")
            d_upass = st.text_input("Password ", type="password",
                                    placeholder="Your password", key="d_upass")

            if st.button("🚗  Sign In with Username", key="d_ugo"):
                if not d_uname or not d_upass:
                    st.warning("Please enter your username and password.")
                else:
                    driver_row = None
                    if CLOUD_AUTH:
                        try:
                            driver_row = verify_driver(d_uname.strip(), d_upass)
                        except Exception:
                            pass

                    if driver_row:
                        vid  = driver_row.get("vehicle_id", "UNKNOWN") or "UNKNOWN"
                        name = driver_row.get("driver_name", d_uname)
                        import hashlib
                        token = hashlib.md5(f"driver:{vid}:driver_monitor_2026".encode()).hexdigest()[:12]
                        st.session_state.update({
                            "logged_in":   True,
                            "role":        "driver",
                            "vehicle_id":  vid,
                            "driver_name": name,
                            "driver_page": "Dashboard",
                        })
                        st.query_params["role"]  = "driver"
                        st.query_params["vid"]   = vid
                        st.query_params["name"]  = name
                        st.query_params["token"] = token
                        try:
                            set_active_vehicle(vid)
                        except Exception:
                            pass
                        st.rerun()
                    else:
                        st.error("Invalid username or password. Contact your admin.")

        _card_close()
        _connection_badge()
