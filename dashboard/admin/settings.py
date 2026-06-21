import streamlit as st
import sys
import platform
from datetime import datetime


def render_settings():
    st.markdown("""
    <style>
    .page-header { font-size:1.4rem;font-weight:800;color:#F1F5F9;margin-bottom:4px; }
    .page-sub    { font-size:0.78rem;color:#64748B;margin-bottom:20px; }
    .section-card {
        background:#1E293B;border:1px solid rgba(255,255,255,0.07);
        border-radius:14px;padding:20px;margin-bottom:16px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-header">⚙️ Settings</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Configure detection thresholds and system parameters</div>',
                unsafe_allow_html=True)

    # ── Alert Thresholds ─────────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:1rem;font-weight:700;color:#F1F5F9;margin-bottom:12px;">
        🎯 Alert Thresholds
    </div>
    """, unsafe_allow_html=True)

    with st.form("settings_form"):
        col1, col2 = st.columns(2)

        with col1:
            ear = st.slider(
                "👁 EAR Threshold (Eye Aspect Ratio)",
                min_value=0.10, max_value=0.40,
                value=st.session_state.get("cfg_ear", 0.25),
                step=0.01,
                help="Lower = more sensitive drowsiness detection",
                key="s_ear",
            )

            frames = st.slider(
                "🎞 Consecutive Frames for Alert",
                min_value=5, max_value=30,
                value=st.session_state.get("cfg_frames", 15),
                step=1,
                help="Number of consecutive frames before triggering alert",
                key="s_frames",
            )

        with col2:
            phone_conf = st.slider(
                "📱 Phone Detection Confidence",
                min_value=0.10, max_value=0.90,
                value=st.session_state.get("cfg_phone", 0.30),
                step=0.05,
                help="Minimum confidence for phone detection",
                key="s_phone",
            )

            cooldown = st.slider(
                "⏱ Alert Cooldown (seconds)",
                min_value=1, max_value=10,
                value=st.session_state.get("cfg_cooldown", 3),
                step=1,
                help="Minimum seconds between repeated alerts",
                key="s_cooldown",
            )

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        save_btn = st.form_submit_button("💾 Save Settings", use_container_width=True)

    if save_btn:
        st.session_state["cfg_ear"]      = ear
        st.session_state["cfg_frames"]   = frames
        st.session_state["cfg_phone"]    = phone_conf
        st.session_state["cfg_cooldown"] = cooldown
        st.success("✅ Settings saved successfully. Restart main.py to apply changes.")

    # Show current values
    st.markdown(
        '<div style="background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.15);'
        'border-radius:10px;padding:14px 18px;margin-top:8px;">'
        '<div style="font-size:0.72rem;color:#64748B;text-transform:uppercase;'
        'letter-spacing:0.06em;margin-bottom:8px;">Current Active Values</div>'
        '</div>',
        unsafe_allow_html=True
    )

    cv1, cv2, cv3, cv4 = st.columns(4)
    with cv1:
        st.metric("EAR", f"{st.session_state.get('cfg_ear', 0.25):.2f}")
    with cv2:
        st.metric("Frames", st.session_state.get("cfg_frames", 15))
    with cv3:
        st.metric("Phone Conf", f"{st.session_state.get('cfg_phone', 0.30):.2f}")
    with cv4:
        st.metric("Cooldown", f"{st.session_state.get('cfg_cooldown', 3)}s")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── System Info ──────────────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:1rem;font-weight:700;color:#F1F5F9;margin-bottom:12px;">
        💻 System Information
    </div>
    """, unsafe_allow_html=True)

    try:
        py_version = sys.version.split(" ")[0]
    except Exception:
        py_version = "Unknown"

    try:
        import streamlit as _st
        st_version = _st.__version__
    except Exception:
        st_version = "Unknown"

    try:
        import pandas as pd
        pd_version = pd.__version__
    except Exception:
        pd_version = "Unknown"

    try:
        import plotly
        plotly_version = plotly.__version__
    except Exception:
        plotly_version = "Unknown"

    sys_items = [
        ("🐍 Python Version",    py_version),
        ("📊 Streamlit Version", st_version),
        ("🐼 Pandas Version",    pd_version),
        ("📈 Plotly Version",    plotly_version),
        ("💻 OS",                platform.system() + " " + platform.release()),
        ("🕐 Last Update",       datetime.now().strftime("%d %b %Y %H:%M:%S")),
    ]

    rows_html = "".join([
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
        f'<span style="color:#94A3B8;font-size:0.82rem;">{label}</span>'
        f'<span style="color:#F1F5F9;font-size:0.82rem;font-family:monospace;">{value}</span>'
        f'</div>'
        for label, value in sys_items
    ])

    st.markdown(
        f'<div style="background:#1E293B;border:1px solid rgba(255,255,255,0.07);'
        f'border-radius:14px;padding:16px 20px;">{rows_html}</div>',
        unsafe_allow_html=True
    )
