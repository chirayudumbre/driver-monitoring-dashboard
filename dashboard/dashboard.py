import streamlit as st
import pandas as pd
import os, json, time, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime, timedelta
from PIL import Image
from utils.config import set_active_vehicle, get_active_vehicle

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Driver Safety Monitor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE        = os.path.dirname(__file__)
LOG_FILE    = os.path.join(BASE, "..", "data", "alert_log.csv")
USERS_FILE  = os.path.join(BASE, "users.json")
SNAP_DIR    = os.path.join(BASE, "..", "data", "snapshots")

# ── Theme palette ─────────────────────────────────────────────────────────────
C = {
    "bg":        "#0D1117",
    "card":      "#161B22",
    "border":    "#30363D",
    "accent":    "#58A6FF",
    "green":     "#3FB950",
    "yellow":    "#D29922",
    "red":       "#F85149",
    "purple":    "#BC8CFF",
    "orange":    "#FFA657",
    "text":      "#E6EDF3",
    "muted":     "#8B949E",
    "drowsy":    "#F85149",
    "distract":  "#FFA657",
    "mobile":    "#BC8CFF",
}

# ── Global CSS ────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
        background-color: {C['bg']};
        color: {C['text']};
    }}

    /* Hide streamlit branding */
    #MainMenu, footer, header {{ visibility: hidden; }}
    .block-container {{ padding: 1.5rem 2rem 2rem 2rem; }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background: {C['card']};
        border-right: 1px solid {C['border']};
    }}
    [data-testid="stSidebar"] * {{ color: {C['text']} !important; }}
    [data-testid="stSidebar"] .stRadio label {{
        padding: 8px 12px;
        border-radius: 8px;
        cursor: pointer;
        transition: background 0.2s;
    }}
    [data-testid="stSidebar"] .stRadio label:hover {{
        background: rgba(88,166,255,0.1);
    }}

    /* Metric cards */
    div[data-testid="metric-container"] {{
        background: {C['card']};
        border: 1px solid {C['border']};
        border-radius: 12px;
        padding: 20px 24px;
        transition: transform 0.2s, box-shadow 0.2s;
    }}
    div[data-testid="metric-container"]:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    }}
    div[data-testid="metric-container"] label {{
        color: {C['muted']} !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {{
        color: {C['text']} !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }}

    /* Dataframe */
    [data-testid="stDataFrame"] {{
        border: 1px solid {C['border']};
        border-radius: 10px;
        overflow: hidden;
    }}

    /* Inputs */
    .stTextInput input, .stSelectbox select {{
        background: {C['card']} !important;
        border: 1px solid {C['border']} !important;
        border-radius: 8px !important;
        color: {C['text']} !important;
    }}
    .stTextInput input:focus {{
        border-color: {C['accent']} !important;
        box-shadow: 0 0 0 3px rgba(88,166,255,0.15) !important;
    }}

    /* Buttons */
    .stButton > button {{
        background: {C['accent']};
        color: #0D1117;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 10px 20px;
        transition: all 0.2s;
    }}
    .stButton > button:hover {{
        background: #79B8FF;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(88,166,255,0.3);
    }}

    /* Divider */
    hr {{ border-color: {C['border']}; margin: 1.5rem 0; }}

    /* Scrollbar */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: {C['bg']}; }}
    ::-webkit-scrollbar-thumb {{ background: {C['border']}; border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {C['muted']}; }}

    /* Alert cards */
    .alert-row {{
        display: flex;
        align-items: center;
        gap: 14px;
        background: {C['card']};
        border: 1px solid {C['border']};
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 8px;
        transition: border-color 0.2s;
    }}
    .alert-row:hover {{ border-color: {C['accent']}; }}

    .badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }}

    .stat-card {{
        background: {C['card']};
        border: 1px solid {C['border']};
        border-radius: 14px;
        padding: 24px;
        text-align: center;
    }}

    .section-title {{
        font-size: 1rem;
        font-weight: 600;
        color: {C['muted']};
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 16px;
    }}

    .login-wrap {{
        max-width: 440px;
        margin: 60px auto 0 auto;
    }}
    .login-card {{
        background: {C['card']};
        border: 1px solid {C['border']};
        border-radius: 16px;
        padding: 44px 40px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.5);
    }}
    </style>
    """, unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(u):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(u, f, indent=4)

def load_log() -> pd.DataFrame:
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame(columns=["timestamp","alert_type","vehicle_id","snapshot"])
    rows = []
    with open(LOG_FILE, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.lower().startswith("timestamp"):
                continue
            parts = line.split(",")
            if len(parts) >= 2:
                rows.append({
                    "timestamp":  parts[0].strip(),
                    "alert_type": parts[1].strip(),
                    "vehicle_id": parts[2].strip() if len(parts) > 2 else "UNKNOWN",
                    "snapshot":   parts[3].strip() if len(parts) > 3 else "",
                })
    if not rows:
        return pd.DataFrame(columns=["timestamp","alert_type","vehicle_id","snapshot"])
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df.dropna(subset=["timestamp"])

def filter_df(df, vid):
    """Return rows for this vehicle. Falls back to all rows if no vehicle match (covers old UNKNOWN logs)."""
    if df.empty:
        return df
    own = df[df["vehicle_id"] == vid]
    return own if not own.empty else df


def badge_html(label, color):
    return f'<span class="badge" style="background:{color}22;color:{color};border:1px solid {color}55;">{label}</span>'

def icon_for(atype):
    return {"DROWSINESS":"😴","DISTRACTION":"👀","MOBILE_USAGE":"📱"}.get(atype,"⚠️")

def color_for(atype):
    return {"DROWSINESS": C["drowsy"], "DISTRACTION": C["distract"], "MOBILE_USAGE": C["mobile"]}.get(atype, C["accent"])

# ── Login Page ────────────────────────────────────────────────────────────────
def login_page():
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown(f"""
        <div class="login-card">
            <div style="text-align:center;margin-bottom:32px;">
                <div style="font-size:3rem;">🛡️</div>
                <h2 style="color:{C['text']};margin:8px 0 4px;font-weight:700;">Driver Safety Monitor</h2>
                <p style="color:{C['muted']};font-size:0.9rem;">Sign in to access your dashboard</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        vehicle_id = st.text_input("🚗  Vehicle Number", placeholder="e.g. MH12AB1234").strip().upper()
        password   = st.text_input("🔒  Password", type="password", placeholder="Enter your password")

        col1, col2 = st.columns(2)
        with col1:
            login_btn = st.button("Sign In", use_container_width=True, type="primary")
        with col2:
            reg_btn = st.button("Register", use_container_width=True)

        if login_btn:
            users = load_users()
            if vehicle_id in users and users[vehicle_id] == password:
                st.session_state.update({"logged_in": True, "vehicle_id": vehicle_id})
                set_active_vehicle(vehicle_id)
                st.rerun()
            else:
                st.error("Invalid vehicle number or password.")

        if reg_btn:
            st.session_state["show_reg"] = True

        if st.session_state.get("show_reg"):
            st.markdown("---")
            st.markdown(f"<p style='color:{C['accent']};font-weight:600;'>Create New Account</p>", unsafe_allow_html=True)
            nv  = st.text_input("Vehicle Number", key="rv").strip().upper()
            np1 = st.text_input("Password",         type="password", key="rp1")
            np2 = st.text_input("Confirm Password", type="password", key="rp2")
            if st.button("Create Account", type="primary"):
                if not nv or not np1:
                    st.warning("Fill all fields.")
                elif np1 != np2:
                    st.error("Passwords don't match.")
                else:
                    users = load_users()
                    if nv in users:
                        st.error("Vehicle already registered.")
                    else:
                        users[nv] = np1
                        save_users(users)
                        st.success(f"✅ Account created for {nv}. You can now sign in.")
                        st.session_state["show_reg"] = False

# ── Sidebar ───────────────────────────────────────────────────────────────────
def sidebar(vid):
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:20px 8px 16px;">
            <div style="display:flex;align-items:center;gap:12px;">
                <div style="background:{C['accent']}22;border:1px solid {C['accent']}44;
                     border-radius:10px;padding:10px;font-size:1.4rem;">🛡️</div>
                <div>
                    <div style="font-weight:700;font-size:1rem;color:{C['text']};">{vid}</div>
                    <div style="font-size:0.75rem;color:{C['green']};font-weight:500;">● Live Monitoring</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"<div style='color:{C['muted']};font-size:0.7rem;text-transform:uppercase;"
                    f"letter-spacing:0.1em;padding:0 8px 8px;font-weight:600;'>Navigation</div>",
                    unsafe_allow_html=True)

        page = st.radio("Navigation", [
            "📊  Overview",
            "🔔  Live Alerts",
            "🖼️  Snapshots",
            "📋  Full Log",
            "⚙️  Settings",
        ], label_visibility="hidden")

        st.markdown("---")
        st.markdown(f"<div style='color:{C['muted']};font-size:0.75rem;font-weight:600;"
                    f"text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;'>"
                    f"Auto Refresh</div>", unsafe_allow_html=True)
        refresh = st.slider("Refresh interval (seconds)", 2, 30, 5, label_visibility="hidden")
        st.markdown(f"<div style='color:{C['muted']};font-size:0.75rem;text-align:center;'>"
                    f"Every {refresh}s</div>", unsafe_allow_html=True)

        st.markdown("---")
        # Active vehicle indicator
        try:
            active = get_active_vehicle()
        except Exception:
            active = "UNKNOWN"
        active_color = C["green"] if active == vid else C["yellow"]
        st.markdown(
            f"<div style='background:{C['bg']};border:1px solid {active_color}33;"
            f"border-radius:8px;padding:10px 12px;margin-bottom:8px;'>"
            f"<div style='color:{C['muted']};font-size:0.7rem;text-transform:uppercase;"
            f"letter-spacing:0.06em;margin-bottom:4px;'>Active Vehicle</div>"
            f"<div style='color:{active_color};font-weight:600;font-size:0.85rem;'>"
            f"{'● ' if active == vid else '○ '}{active}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
        if active != vid:
            if st.button("▶  Set as Active Vehicle", use_container_width=True, type="primary"):
                set_active_vehicle(vid)
                st.rerun()
        if st.button("🚪  Sign Out", use_container_width=True):
            for k in ["logged_in","vehicle_id","show_reg"]:
                st.session_state.pop(k, None)
            st.rerun()

        st.markdown(f"""
        <div style="position:fixed;bottom:20px;left:0;width:260px;text-align:center;
             color:{C['muted']};font-size:0.7rem;">
            Driver Safety Monitor v2.0<br>
            <span style="color:{C['green']};">● System Active</span>
        </div>
        """, unsafe_allow_html=True)

    return page, refresh

# ── Header ────────────────────────────────────────────────────────────────────
def page_header(title, subtitle=""):
    now = datetime.now().strftime("%d %b %Y  •  %H:%M:%S")
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:flex-start;
         margin-bottom:28px;padding-bottom:20px;border-bottom:1px solid {C['border']};">
        <div>
            <h1 style="margin:0;font-size:1.6rem;font-weight:700;color:{C['text']};">{title}</h1>
            <p style="margin:4px 0 0;color:{C['muted']};font-size:0.88rem;">{subtitle}</p>
        </div>
        <div style="text-align:right;">
            <div style="background:{C['card']};border:1px solid {C['border']};border-radius:8px;
                 padding:8px 14px;font-size:0.8rem;color:{C['muted']};">
                🕐 {now}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── KPI card ──────────────────────────────────────────────────────────────────
def kpi_card(icon, label, value, color):
    html = (
        "<div style='"
        "background:" + C["card"] + ";"
        "border:1px solid " + C["border"] + ";"
        "border-left:4px solid " + color + ";"
        "border-radius:12px;"
        "padding:20px 22px;"
        "height:100%;'>"
        "<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        "<div>"
        "<div style='color:" + C["muted"] + ";font-size:0.75rem;font-weight:600;"
        "text-transform:uppercase;letter-spacing:0.06em;'>" + str(label) + "</div>"
        "<div style='font-size:2.2rem;font-weight:700;color:" + C["text"] + ";"
        "margin-top:6px;line-height:1;'>" + str(value) + "</div>"
        "</div>"
        "<div style='font-size:2rem;opacity:0.8;'>" + str(icon) + "</div>"
        "</div>"
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


# ── Overview Page ─────────────────────────────────────────────────────────────
def page_overview(df, vid):
    page_header("📊 Overview", "Real-time driver behaviour summary")

    vdf = filter_df(df, vid)

    if vdf.empty:
        st.markdown(
            f"<div style='text-align:center;padding:60px;background:{C['card']};"
            f"border:1px solid {C['border']};border-radius:14px;color:{C['muted']};'>"
            f"<div style='font-size:3rem;'>✅</div>"
            f"<div style='font-size:1.1rem;margin-top:12px;font-weight:500;'>No alerts recorded yet</div>"
            f"<div style='font-size:0.85rem;margin-top:6px;'>Driver behaviour is being monitored</div>"
            f"</div>",
            unsafe_allow_html=True
        )
        return

    # ── Date range selector ───────────────────────────────────────────────────
    min_date = vdf["timestamp"].min().date()
    max_date = vdf["timestamp"].max().date()

    dr1, dr2, _ = st.columns([1, 1, 2])
    with dr1:
        d_from = st.date_input("From", value=min_date, key="ov_from",
                               min_value=min_date, max_value=max_date)
    with dr2:
        d_to = st.date_input("To", value=max_date, key="ov_to",
                             min_value=min_date, max_value=max_date)

    vdf_r = vdf[(vdf["timestamp"].dt.date >= d_from) & (vdf["timestamp"].dt.date <= d_to)]

    st.markdown("<br>", unsafe_allow_html=True)

    # ── KPI cards (based on selected date range) ──────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("⚠️", "Total Alerts",  len(vdf_r),                                    C["accent"])
    with c2: kpi_card("😴", "Drowsiness",     len(vdf_r[vdf_r["alert_type"]=="DROWSINESS"]), C["drowsy"])
    with c3: kpi_card("👀", "Distraction",    len(vdf_r[vdf_r["alert_type"]=="DISTRACTION"]),C["distract"])
    with c4: kpi_card("📱", "Mobile Usage",   len(vdf_r[vdf_r["alert_type"]=="MOBILE_USAGE"]),C["mobile"])

    st.markdown("<br>", unsafe_allow_html=True)

    if vdf_r.empty:
        st.info("No alerts in selected date range.")
        return

    # ── Charts ────────────────────────────────────────────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown(f"<div class='section-title'>Alert Distribution</div>", unsafe_allow_html=True)
        counts = vdf_r["alert_type"].value_counts().reset_index()
        counts.columns = ["Type", "Count"]
        st.bar_chart(counts.set_index("Type"), color=C["accent"], height=260)

    with col_r:
        st.markdown(f"<div class='section-title'>Daily Trend</div>", unsafe_allow_html=True)
        vdf2 = vdf_r.copy()
        vdf2["day"] = vdf2["timestamp"].dt.floor("D")
        daily = vdf2.groupby(["day", "alert_type"]).size().unstack(fill_value=0)
        st.line_chart(daily, height=260)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Alerts by hour of day ─────────────────────────────────────────────────
    st.markdown(f"<div class='section-title'>Alerts by Hour of Day</div>", unsafe_allow_html=True)
    vdf3 = vdf_r.copy()
    vdf3["hour"] = vdf3["timestamp"].dt.hour
    hourly = vdf3.groupby(["hour", "alert_type"]).size().unstack(fill_value=0)
    st.bar_chart(hourly, height=200)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Recent activity ───────────────────────────────────────────────────────
    st.markdown(f"<div class='section-title'>Recent Activity</div>", unsafe_allow_html=True)
    for _, row in vdf.head(8).iterrows():
        atype = str(row["alert_type"])
        col   = color_for(atype)
        ts    = row["timestamp"].strftime("%d %b %Y  %H:%M:%S")
        st.markdown(
            f"<div class='alert-row' style='border-left:3px solid {col};'>"
            f"<span style='font-size:1.3rem;'>{icon_for(atype)}</span>"
            f"{badge_html(atype, col)}"
            f"<span style='color:{C['muted']};font-size:0.83rem;margin-left:auto;'>{ts}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

# ── Live Alerts Page ──────────────────────────────────────────────────────────
def page_live_alerts(df, vid):
    page_header("🔔 Live Alerts", "Most recent driver behaviour events")

    vdf = filter_df(df, vid)

    if vdf.empty:
        st.markdown(f"""
        <div style="text-align:center;padding:60px;background:{C['card']};
             border:1px solid {C['border']};border-radius:14px;color:{C['muted']};">
            <div style="font-size:3rem;">🟢</div>
            <div style="font-size:1.1rem;margin-top:12px;font-weight:500;">No alerts yet</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Filter bar
    fc1, fc2 = st.columns([2, 1])
    with fc1:
        ftype = st.selectbox("Filter by type", ["ALL","DROWSINESS","DISTRACTION","MOBILE_USAGE"],
                             label_visibility="hidden")
    with fc2:
        limit = st.selectbox("Show last", [25, 50, 100, 200], label_visibility="hidden")

    filtered = vdf.sort_values("timestamp", ascending=False)
    if ftype != "ALL":
        filtered = filtered[filtered["alert_type"] == ftype]
    filtered = filtered.head(limit)

    st.markdown(f"<div style='color:{C['muted']};font-size:0.82rem;margin-bottom:12px;'>"
                f"Showing {len(filtered)} alerts</div>", unsafe_allow_html=True)

    for _, row in filtered.iterrows():
        atype = str(row["alert_type"])
        col   = color_for(atype)
        ts    = row["timestamp"].strftime("%d %b %Y  %H:%M:%S")
        snap  = str(row.get("snapshot",""))

        left, right = st.columns([4, 1])
        with left:
            st.markdown(f"""
            <div class="alert-row" style="border-left:3px solid {col};">
                <div style="font-size:1.5rem;">{icon_for(atype)}</div>
                <div style="flex:1;">
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
                        {badge_html(atype, col)}
                        <span style="color:{C['muted']};font-size:0.8rem;">{ts}</span>
                    </div>
                    <div style="color:{C['muted']};font-size:0.78rem;">
                        Vehicle: <span style="color:{C['text']};font-weight:500;">{row.get('vehicle_id','—')}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with right:
            if snap and os.path.exists(snap):
                try:
                    st.image(Image.open(snap), width=110)
                except Exception:
                    pass

# ── Snapshots Page ────────────────────────────────────────────────────────────
def page_snapshots(df, vid):
    page_header("Snapshots", "Captured frames at moment of alert")

    vdf = filter_df(df, vid)

    fc1, fc2, fc3 = st.columns([2, 1, 1])
    with fc1:
        ft = st.selectbox("Filter by type",
                          ["ALL", "DROWSINESS", "DISTRACTION", "MOBILE_USAGE"],
                          label_visibility="hidden")
    with fc2:
        d_from = st.date_input("From",
                               value=datetime.now().date() - timedelta(days=30),
                               key="sp_from", label_visibility="hidden")
    with fc3:
        d_to = st.date_input("To", value=datetime.now().date(),
                             key="sp_to", label_visibility="hidden")

    # Try log-linked snapshots first
    snaps = vdf[vdf["snapshot"].astype(str).str.strip() != ""].copy()
    snaps = snaps[
        (snaps["timestamp"].dt.date >= d_from) &
        (snaps["timestamp"].dt.date <= d_to)
    ]
    if ft != "ALL":
        snaps = snaps[snaps["alert_type"] == ft]
    snaps = snaps[snaps["snapshot"].apply(lambda p: os.path.exists(str(p)))]

    # Fallback: scan snapshots folder directly
    if snaps.empty:
        files = []
        if os.path.exists(SNAP_DIR):
            files = sorted(
                [f for f in os.listdir(SNAP_DIR) if f.lower().endswith(".jpg")],
                reverse=True
            )
        if ft != "ALL":
            files = [f for f in files if f.upper().startswith(ft)]

        if not files:
            st.info("No snapshots yet. Run main.py to start capturing.")
            return

        st.markdown(
            f"<div style='color:{C['muted']};font-size:0.82rem;margin-bottom:12px;'>"
            f"Found {len(files)} snapshots on disk</div>",
            unsafe_allow_html=True
        )
        cols = st.columns(4)
        for i, fname in enumerate(files[:60]):
            fpath = os.path.join(SNAP_DIR, fname)
            try:
                atype = fname.split("_")[0].upper()
                col   = color_for(atype)
                ts    = "_".join(fname.replace(".jpg", "").split("_")[1:3])
                with cols[i % 4]:
                    st.image(Image.open(fpath), use_container_width=True)
                    st.markdown(
                        f"<div style='text-align:center;margin-top:4px;margin-bottom:12px;'>"
                        f"{badge_html(atype, col)}"
                        f"<div style='color:{C['muted']};font-size:0.7rem;margin-top:3px;'>{ts}</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
            except Exception:
                pass
        return

    # Show log-linked snapshots
    st.markdown(
        f"<div style='color:{C['muted']};font-size:0.82rem;margin-bottom:12px;'>"
        f"{len(snaps)} snapshots</div>",
        unsafe_allow_html=True
    )
    cols = st.columns(4)
    for i, (_, row) in enumerate(snaps.iterrows()):
        snap  = str(row["snapshot"])
        atype = str(row["alert_type"])
        col   = color_for(atype)
        ts    = row["timestamp"].strftime("%d %b  %H:%M:%S")
        try:
            with cols[i % 4]:
                st.image(Image.open(snap), use_container_width=True)
                st.markdown(
                    f"<div style='text-align:center;margin-top:4px;margin-bottom:12px;'>"
                    f"{badge_html(atype, col)}"
                    f"<div style='color:{C['muted']};font-size:0.7rem;margin-top:3px;'>{ts}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
        except Exception:
            pass

def page_full_log(df, vid):
    page_header("📋 Full Log", "Complete alert history with filters")

    vdf = filter_df(df, vid)

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        ft = st.selectbox("Alert Type", ["ALL","DROWSINESS","DISTRACTION","MOBILE_USAGE"])
    with fc2:
        d_from = st.date_input("From", value=datetime.now().date() - timedelta(days=7))
    with fc3:
        d_to   = st.date_input("To",   value=datetime.now().date())

    if ft != "ALL":
        vdf = vdf[vdf["alert_type"] == ft]
    vdf = vdf[(vdf["timestamp"].dt.date >= d_from) & (vdf["timestamp"].dt.date <= d_to)]
    vdf = vdf.sort_values("timestamp", ascending=False)

    # Summary row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Records",    len(vdf))
    c2.metric("😴 Drowsy",  len(vdf[vdf["alert_type"]=="DROWSINESS"]))
    c3.metric("👀 Distract",len(vdf[vdf["alert_type"]=="DISTRACTION"]))
    c4.metric("📱 Mobile",  len(vdf[vdf["alert_type"]=="MOBILE_USAGE"]))

    st.markdown("<br>", unsafe_allow_html=True)

    display = vdf[["timestamp","alert_type","vehicle_id"]].copy()
    display["timestamp"] = display["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(display, use_container_width=True, height=460,
                 column_config={
                     "timestamp":  st.column_config.TextColumn("Timestamp",  width="medium"),
                     "alert_type": st.column_config.TextColumn("Alert Type", width="medium"),
                     "vehicle_id": st.column_config.TextColumn("Vehicle",    width="small"),
                 })

    csv = display.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️  Export CSV", csv, "alert_log_export.csv", "text/csv",
                       use_container_width=False)

# ── Settings Page ─────────────────────────────────────────────────────────────
def page_settings(vid):
    page_header("⚙️ Settings", "Account and system configuration")

    col_l, col_r = st.columns([1, 1])

    with col_l:
        st.markdown(f"<div class='section-title'>Change Password</div>", unsafe_allow_html=True)
        with st.container():
            old  = st.text_input("Current Password",     type="password", key="s1")
            new1 = st.text_input("New Password",         type="password", key="s2")
            new2 = st.text_input("Confirm New Password", type="password", key="s3")
            if st.button("Update Password", type="primary"):
                users = load_users()
                if users.get(vid) != old:
                    st.error("Current password is incorrect.")
                elif new1 != new2:
                    st.error("New passwords do not match.")
                elif len(new1) < 4:
                    st.warning("Password must be at least 4 characters.")
                else:
                    users[vid] = new1
                    save_users(users)
                    st.success("✅ Password updated successfully.")

    with col_r:
        st.markdown(f"<div class='section-title'>System Info</div>", unsafe_allow_html=True)
        log_size = f"{os.path.getsize(LOG_FILE)/1024:.1f} KB" if os.path.exists(LOG_FILE) else "N/A"
        snap_count = len([f for f in os.listdir(SNAP_DIR) if f.endswith(".jpg")]) if os.path.exists(SNAP_DIR) else 0

        st.markdown(f"""
        <div style="background:{C['card']};border:1px solid {C['border']};border-radius:12px;padding:20px;">
            <div style="display:flex;justify-content:space-between;padding:10px 0;
                 border-bottom:1px solid {C['border']};">
                <span style="color:{C['muted']};">Vehicle ID</span>
                <span style="color:{C['text']};font-weight:600;">{vid}</span>
            </div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;
                 border-bottom:1px solid {C['border']};">
                <span style="color:{C['muted']};">Log File Size</span>
                <span style="color:{C['text']};font-weight:600;">{log_size}</span>
            </div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;
                 border-bottom:1px solid {C['border']};">
                <span style="color:{C['muted']};">Total Snapshots</span>
                <span style="color:{C['text']};font-weight:600;">{snap_count}</span>
            </div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;">
                <span style="color:{C['muted']};">Dashboard Version</span>
                <span style="color:{C['green']};font-weight:600;">v2.0</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    inject_css()

    if "logged_in"  not in st.session_state: st.session_state["logged_in"]  = False
    if "show_reg"   not in st.session_state: st.session_state["show_reg"]   = False

    if not st.session_state["logged_in"]:
        login_page()
        return

    vid          = st.session_state["vehicle_id"]
    page, refresh = sidebar(vid)
    df           = load_log()

    if   "Overview"    in page: page_overview(df, vid)
    elif "Live Alerts" in page: page_live_alerts(df, vid)
    elif "Snapshots"   in page: page_snapshots(df, vid)
    elif "Full Log"    in page: page_full_log(df, vid)
    elif "Settings"    in page: page_settings(vid)

    time.sleep(refresh)
    st.rerun()

if __name__ == "__main__":
    main()
