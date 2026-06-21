import streamlit as st
import pandas as pd
import os

SNAPSHOTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "snapshots"
)

SEVERITY_MAP = {
    "DROWSINESS":   ("Medium", "#F59E0B"),
    "DISTRACTION":  ("Low",    "#10B981"),
    "MOBILE_USAGE": ("High",   "#F97316"),
}


def render_driver_snapshots(df: pd.DataFrame, vid: str):
    st.markdown("""
    <style>
    .page-header { font-size:1.4rem;font-weight:800;color:#F1F5F9;margin-bottom:4px; }
    .page-sub    { font-size:0.78rem;color:#64748B;margin-bottom:20px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-header">📷 My Snapshots</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-sub">Captured frames for vehicle {vid}</div>',
                unsafe_allow_html=True)

    # Filter for this vehicle
    snap_items = []

    try:
        if df is not None and not df.empty and "snapshot" in df.columns:
            vdf = df[df["vehicle_id"] == vid] if "vehicle_id" in df.columns else df
            vdf = vdf[vdf["snapshot"].notna() & (vdf["snapshot"] != "")]
            for _, row in vdf.iterrows():
                snap_items.append({
                    "path":       row["snapshot"],
                    "alert_type": row.get("alert_type", ""),
                    "timestamp":  str(row.get("timestamp", ""))[:19],
                    "is_url":     str(row["snapshot"]).startswith("http"),
                })
    except Exception:
        pass

    # Local snapshots
    try:
        if os.path.exists(SNAPSHOTS_DIR):
            for fname in sorted(os.listdir(SNAPSHOTS_DIR), reverse=True):
                if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue
                fpath = os.path.join(SNAPSHOTS_DIR, fname)
                if not any(s["path"] == fpath for s in snap_items):
                    parts = fname.rsplit("_", 2)
                    atype = parts[0] if parts else ""
                    snap_items.append({
                        "path":       fpath,
                        "alert_type": atype,
                        "timestamp":  fname,
                        "is_url":     False,
                    })
    except Exception:
        pass

    if not snap_items:
        st.info("No snapshots available for your vehicle.")
        return

    st.markdown(f"**{len(snap_items)} snapshot(s)**")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Grid 3 columns
    for i in range(0, len(snap_items), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(snap_items):
                break
            item = snap_items[idx]
            with col:
                try:
                    if item["is_url"]:
                        st.image(item["path"], use_container_width=True)
                    elif os.path.exists(item["path"]):
                        from PIL import Image
                        st.image(Image.open(item["path"]), use_container_width=True)
                    else:
                        st.markdown(
                            '<div style="height:100px;background:#0F172A;border-radius:8px;'
                            'display:flex;align-items:center;justify-content:center;'
                            'color:#475569;font-size:0.72rem;">Not found</div>',
                            unsafe_allow_html=True,
                        )
                except Exception:
                    st.markdown(
                        '<div style="height:100px;background:#0F172A;border-radius:8px;'
                        'display:flex;align-items:center;justify-content:center;'
                        'color:#475569;font-size:0.72rem;">Load error</div>',
                        unsafe_allow_html=True,
                    )

                atype = item["alert_type"]
                _, color = SEVERITY_MAP.get(atype, ("Low", "#64748B"))
                label = atype.replace("_", " ").title() if atype else "Unknown"
                st.markdown(
                    f'<div style="margin-top:4px;">'
                    f'<span style="background:{color}22;color:{color};border:1px solid {color}44;'
                    f'padding:2px 8px;border-radius:6px;font-size:0.68rem;font-weight:600;">'
                    f'{label}</span></div>'
                    f'<div style="font-size:0.68rem;color:#64748B;margin-top:3px;">'
                    f'⏱ {item["timestamp"][:19]}</div>',
                    unsafe_allow_html=True,
                )
