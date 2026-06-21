import streamlit as st
import pandas as pd
import os, sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from utils.supabase_client import (
        fetch_vehicles, create_vehicle, update_vehicle, delete_vehicle
    )
    CLOUD = True
except Exception:
    CLOUD = False


def render_vehicles(vehicles_dict: dict):
    st.markdown("""
    <style>
    .page-header{font-size:1.4rem;font-weight:800;color:#F1F5F9;margin-bottom:4px;}
    .page-sub{font-size:0.78rem;color:#64748B;margin-bottom:20px;}
    .form-card{background:#1E293B;border:1px solid rgba(255,255,255,0.07);
               border-radius:14px;padding:20px;margin-bottom:16px;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-header">🚗 Vehicle Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Register, edit and manage all vehicles in the fleet</div>',
                unsafe_allow_html=True)

    # ── Load vehicles from Supabase ───────────────────────────────────────────
    rows = []
    if CLOUD:
        try:
            rows = fetch_vehicles()
        except Exception:
            rows = []

    # Fallback to passed dict if Supabase empty
    if not rows and vehicles_dict:
        for vid, vdata in vehicles_dict.items():
            v = vdata if isinstance(vdata, dict) else {}
            rows.append({
                "vehicle_number": vid,
                "vehicle_model":  v.get("vehicle_model", "—"),
                "status":         v.get("status", "Active"),
                "registration_date": v.get("registration_date", "—"),
            })

    # ── Add Vehicle form ──────────────────────────────────────────────────────
    with st.expander("➕ Register New Vehicle", expanded=False):
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            v_num   = st.text_input("Vehicle Number *", placeholder="e.g. MH12AB1234", key="v_num")
            v_pass  = st.text_input("Vehicle Password *", type="password",
                                    placeholder="Set login password", key="v_pass")
        with col2:
            v_model = st.text_input("Vehicle Model", placeholder="e.g. Toyota Camry", key="v_model")
            v_status = st.selectbox("Status", ["Active", "Inactive"], key="v_status")

        if st.button("✅ Register Vehicle", key="v_add"):
            num = v_num.strip().upper()
            if not num or not v_pass:
                st.warning("Vehicle Number and Password are required.")
            elif len(v_pass) < 4:
                st.error("Password must be at least 4 characters.")
            else:
                ok = create_vehicle(num, v_pass, v_model, v_status) if CLOUD else False
                if ok:
                    st.success(f"✅ Vehicle {num} registered successfully!")
                    st.rerun()
                elif not CLOUD:
                    st.warning("Supabase not connected. Vehicle not saved to cloud.")
                else:
                    st.error("Failed to register. Vehicle may already exist.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Vehicles table ────────────────────────────────────────────────────────
    st.markdown(f'<div style="font-size:0.78rem;color:#64748B;margin-bottom:12px;">'
                f'{len(rows)} vehicle(s) registered</div>', unsafe_allow_html=True)

    if not rows:
        st.markdown("""
        <div style="background:#1E293B;border:1px solid rgba(255,255,255,0.07);
             border-radius:14px;padding:40px;text-align:center;color:#64748B;">
            <div style="font-size:2.5rem;margin-bottom:12px;">🚗</div>
            <div style="font-size:0.9rem;font-weight:600;color:#94A3B8;">No vehicles registered yet</div>
            <div style="font-size:0.78rem;margin-top:6px;">Use the form above to add your first vehicle</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Table header
    hcols = st.columns([2, 2, 1.2, 1.5, 1, 1])
    for h, c in zip(["Vehicle Number","Model","Status","Registered","Edit","Delete"], hcols):
        c.markdown(f'<div style="font-size:0.68rem;color:#64748B;text-transform:uppercase;'
                   f'letter-spacing:0.06em;font-weight:700;padding:8px 0;">{h}</div>',
                   unsafe_allow_html=True)

    for i, row in enumerate(rows):
        vid   = row.get("vehicle_number", "—")
        model = row.get("vehicle_model", "—") or "—"
        stat  = row.get("status", "Active")
        reg   = str(row.get("registration_date", "—"))[:10]
        sc    = "#10B981" if stat == "Active" else "#EF4444"

        c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 1.2, 1.5, 1, 1])
        c1.markdown(f'<span style="font-size:0.82rem;color:#F1F5F9;'
                    f'font-family:monospace;">{vid}</span>', unsafe_allow_html=True)
        c2.markdown(f'<span style="font-size:0.82rem;color:#94A3B8;">{model}</span>',
                    unsafe_allow_html=True)
        c3.markdown(f'<span style="background:{sc}22;color:{sc};border:1px solid {sc}44;'
                    f'padding:2px 8px;border-radius:6px;font-size:0.72rem;font-weight:600;">'
                    f'{stat}</span>', unsafe_allow_html=True)
        c4.markdown(f'<span style="font-size:0.78rem;color:#64748B;">{reg}</span>',
                    unsafe_allow_html=True)

        with c5:
            if st.button("✏️", key=f"vedit_{i}_{vid}", help="Edit"):
                st.session_state[f"edit_v_{vid}"] = True

        with c6:
            if st.button("🗑️", key=f"vdel_{i}_{vid}", help="Delete"):
                ok = delete_vehicle(vid) if CLOUD else False
                if ok:
                    st.success(f"Deleted {vid}")
                    st.rerun()
                else:
                    st.error("Delete failed.")

        # Edit form inline
        if st.session_state.get(f"edit_v_{vid}"):
            with st.container():
                st.markdown(f'<div class="form-card">', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:0.82rem;color:#93C5FD;font-weight:600;'
                            f'margin-bottom:10px;">Editing: {vid}</div>', unsafe_allow_html=True)
                ec1, ec2 = st.columns(2)
                with ec1:
                    new_model  = st.text_input("Model",    value=model, key=f"em_{vid}")
                    new_status = st.selectbox("Status",    ["Active","Inactive"],
                                              index=0 if stat=="Active" else 1, key=f"es_{vid}")
                with ec2:
                    new_pass = st.text_input("New Password (leave blank to keep current)",
                                             type="password", key=f"ep_{vid}")

                sc1, sc2 = st.columns(2)
                with sc1:
                    if st.button("💾 Save", key=f"esave_{vid}"):
                        upd = {"vehicle_model": new_model, "status": new_status}
                        if new_pass:
                            upd["vehicle_password"] = new_pass
                        ok = update_vehicle(vid, upd) if CLOUD else False
                        if ok:
                            st.success("Updated!")
                            del st.session_state[f"edit_v_{vid}"]
                            st.rerun()
                        else:
                            st.error("Update failed.")
                with sc2:
                    if st.button("❌ Cancel", key=f"ecancel_{vid}"):
                        del st.session_state[f"edit_v_{vid}"]
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
