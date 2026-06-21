import streamlit as st
import pandas as pd
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from utils.supabase_client import (
        fetch_drivers, create_driver, update_driver, delete_driver, fetch_vehicles
    )
    CLOUD = True
except Exception:
    CLOUD = False


def render_drivers(vehicles_dict: dict):
    st.markdown("""
    <style>
    .page-header{font-size:1.4rem;font-weight:800;color:#F1F5F9;margin-bottom:4px;}
    .page-sub{font-size:0.78rem;color:#64748B;margin-bottom:20px;}
    .form-card{background:#1E293B;border:1px solid rgba(255,255,255,0.07);
               border-radius:14px;padding:20px;margin-bottom:16px;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-header">👤 Driver Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Add, edit and assign drivers to vehicles</div>',
                unsafe_allow_html=True)

    # ── Load data ─────────────────────────────────────────────────────────────
    drivers  = []
    vehicles = []
    if CLOUD:
        try:
            drivers  = fetch_drivers()
            vehicles = fetch_vehicles()
        except Exception:
            pass

    # Vehicle list for selectbox
    v_numbers = [v.get("vehicle_number","") for v in vehicles if v.get("vehicle_number")]
    if not v_numbers and vehicles_dict:
        v_numbers = list(vehicles_dict.keys())

    # ── Add Driver form ───────────────────────────────────────────────────────
    with st.expander("➕ Add New Driver", expanded=False):
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            d_name  = st.text_input("Driver Name *",  placeholder="Full name",      key="d_name")
            d_uname = st.text_input("Username *",     placeholder="Login username", key="d_uname")
            d_phone = st.text_input("Phone Number",   placeholder="+91 9999999999", key="d_phone")
        with col2:
            d_pass  = st.text_input("Password *", type="password",
                                    placeholder="Set login password", key="d_pass")
            d_veh   = st.selectbox("Assign Vehicle", ["— None —"] + v_numbers, key="d_veh")

        if st.button("✅ Add Driver", key="d_add"):
            name  = d_name.strip()
            uname = d_uname.strip()
            vid   = d_veh if d_veh != "— None —" else ""

            if not name or not uname or not d_pass:
                st.warning("Name, Username and Password are required.")
            elif len(d_pass) < 4:
                st.error("Password must be at least 4 characters.")
            else:
                ok = create_driver(name, uname, d_pass, d_phone, vid) if CLOUD else False
                if ok:
                    st.success(f"✅ Driver '{name}' added successfully!")
                    st.rerun()
                elif not CLOUD:
                    st.warning("Supabase not connected.")
                else:
                    st.error("Failed to add driver. Username may already exist.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Drivers table ─────────────────────────────────────────────────────────
    st.markdown(f'<div style="font-size:0.78rem;color:#64748B;margin-bottom:12px;">'
                f'{len(drivers)} driver(s) registered</div>', unsafe_allow_html=True)

    if not drivers:
        st.markdown("""
        <div style="background:#1E293B;border:1px solid rgba(255,255,255,0.07);
             border-radius:14px;padding:40px;text-align:center;color:#64748B;">
            <div style="font-size:2.5rem;margin-bottom:12px;">👤</div>
            <div style="font-size:0.9rem;font-weight:600;color:#94A3B8;">No drivers registered yet</div>
            <div style="font-size:0.78rem;margin-top:6px;">Use the form above to add your first driver</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Header
    hcols = st.columns([2, 1.5, 1.5, 1.5, 1, 1])
    for h, c in zip(["Name","Username","Phone","Vehicle","Edit","Delete"], hcols):
        c.markdown(f'<div style="font-size:0.68rem;color:#64748B;text-transform:uppercase;'
                   f'letter-spacing:0.06em;font-weight:700;padding:8px 0;">{h}</div>',
                   unsafe_allow_html=True)

    for i, row in enumerate(drivers):
        name  = row.get("driver_name", "—")
        uname = row.get("username",    "—")
        phone = row.get("phone_number","—") or "—"
        veh   = row.get("vehicle_id",  "—") or "—"

        c1,c2,c3,c4,c5,c6 = st.columns([2,1.5,1.5,1.5,1,1])
        c1.markdown(f'<span style="font-size:0.82rem;color:#F1F5F9;">{name}</span>',
                    unsafe_allow_html=True)
        c2.markdown(f'<span style="font-size:0.82rem;color:#94A3B8;">{uname}</span>',
                    unsafe_allow_html=True)
        c3.markdown(f'<span style="font-size:0.82rem;color:#64748B;">{phone}</span>',
                    unsafe_allow_html=True)
        c4.markdown(f'<span style="font-size:0.78rem;color:#93C5FD;font-family:monospace;">{veh}</span>',
                    unsafe_allow_html=True)

        with c5:
            if st.button("✏️", key=f"dedit_{i}_{uname}", help="Edit"):
                st.session_state[f"edit_d_{uname}"] = True
        with c6:
            if st.button("🗑️", key=f"ddel_{i}_{uname}", help="Delete"):
                ok = delete_driver(uname) if CLOUD else False
                if ok:
                    st.success(f"Deleted {name}")
                    st.rerun()
                else:
                    st.error("Delete failed.")

        # Inline edit form
        if st.session_state.get(f"edit_d_{uname}"):
            with st.container():
                st.markdown('<div class="form-card">', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:0.82rem;color:#93C5FD;font-weight:600;'
                            f'margin-bottom:10px;">Editing: {name}</div>', unsafe_allow_html=True)
                ec1, ec2 = st.columns(2)
                with ec1:
                    new_name  = st.text_input("Name",  value=name,  key=f"dn_{uname}")
                    new_phone = st.text_input("Phone", value=phone if phone!="—" else "",
                                             key=f"dp_{uname}")
                with ec2:
                    v_opts    = ["— None —"] + v_numbers
                    curr_idx  = v_opts.index(veh) if veh in v_opts else 0
                    new_veh   = st.selectbox("Vehicle", v_opts, index=curr_idx, key=f"dv_{uname}")
                    new_pass  = st.text_input("New Password (blank = keep)",
                                             type="password", key=f"dpass_{uname}")
                sc1, sc2 = st.columns(2)
                with sc1:
                    if st.button("💾 Save", key=f"dsave_{uname}"):
                        upd = {
                            "driver_name":  new_name,
                            "phone_number": new_phone,
                            "vehicle_id":   new_veh if new_veh != "— None —" else None,
                        }
                        if new_pass:
                            upd["password"] = new_pass
                        ok = update_driver(uname, upd) if CLOUD else False
                        if ok:
                            st.success("Updated!")
                            del st.session_state[f"edit_d_{uname}"]
                            st.rerun()
                        else:
                            st.error("Update failed.")
                with sc2:
                    if st.button("❌ Cancel", key=f"dcancel_{uname}"):
                        del st.session_state[f"edit_d_{uname}"]
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
