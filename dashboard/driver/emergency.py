import streamlit as st
from datetime import datetime


EMERGENCY_CONTACTS = [
    ("🚔", "Police",          "100",  "#3B82F6"),
    ("🚑", "Ambulance",       "108",  "#EF4444"),
    ("🚒", "Fire Brigade",    "101",  "#F97316"),
    ("🛣️",  "Road Accident",   "1033", "#F59E0B"),
]


def render_emergency():
    st.markdown("""
    <style>
    .page-header { font-size:1.4rem;font-weight:800;color:#F1F5F9;margin-bottom:4px; }
    .page-sub    { font-size:0.78rem;color:#64748B;margin-bottom:20px; }
    .contact-card {
        background:#1E293B;border:1px solid rgba(255,255,255,0.07);
        border-radius:14px;padding:18px;text-align:center;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-header">🆘 Emergency</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Quick access to emergency services</div>',
                unsafe_allow_html=True)

    # SOS button area
    st.markdown("""
    <div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);
         border-radius:16px;padding:24px;text-align:center;margin-bottom:24px;">
        <div style="font-size:3rem;margin-bottom:8px;">🆘</div>
        <div style="font-size:1.1rem;font-weight:700;color:#FCA5A5;margin-bottom:6px;">
            Emergency SOS</div>
        <div style="font-size:0.78rem;color:#64748B;">
            Press the button below to send an emergency alert
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_sos, _, _ = st.columns([1, 0.5, 0.5])
    with col_sos:
        if st.button(
            "🆘  SEND SOS ALERT",
            use_container_width=True,
            key="sos_btn",
            type="primary",
        ):
            ts = datetime.now().strftime("%d %b %Y %H:%M:%S")
            vehicle_id  = st.session_state.get("vehicle_id", "UNKNOWN")
            driver_name = st.session_state.get("driver_name", "Driver")

            st.success(f"""
            ✅ **SOS Alert Sent Successfully!**
            - Driver: {driver_name}
            - Vehicle: {vehicle_id}
            - Time: {ts}
            - Status: Emergency services notified
            """)

            st.balloons()

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # Emergency contacts
    st.markdown("""
    <div style="font-size:1rem;font-weight:700;color:#F1F5F9;margin-bottom:14px;">
        📞 Emergency Contacts
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(2)
    for i, (icon, name, number, color) in enumerate(EMERGENCY_CONTACTS):
        with cols[i % 2]:
            st.markdown(f"""
            <div class="contact-card" style="border-top:3px solid {color};margin-bottom:12px;">
                <div style="font-size:2rem;margin-bottom:6px;">{icon}</div>
                <div style="font-size:0.9rem;font-weight:700;color:#F1F5F9;">{name}</div>
                <div style="font-size:1.6rem;font-weight:800;color:{color};
                     font-family:monospace;margin-top:4px;">{number}</div>
            </div>
            """, unsafe_allow_html=True)

    # Safety tips
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#1E293B;border:1px solid rgba(255,255,255,0.07);
         border-radius:14px;padding:18px;">
        <div style="font-size:0.9rem;font-weight:700;color:#F1F5F9;margin-bottom:12px;">
            🛡️ Safety Reminders
        </div>
        <ul style="color:#94A3B8;font-size:0.82rem;margin:0;padding-left:20px;line-height:1.8;">
            <li>If you feel drowsy, pull over to a safe location and rest</li>
            <li>Never use your phone while driving</li>
            <li>Keep both hands on the wheel and eyes on the road</li>
            <li>In case of accident, turn on hazard lights immediately</li>
            <li>Do not block traffic — move vehicles to the roadside if possible</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
