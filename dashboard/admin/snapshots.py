import streamlit as st
import pandas as pd
import os
from datetime import timedelta

SEVERITY_MAP = {
    "DROWSINESS":   ("Medium", "#F59E0B"),
    "DISTRACTION":  ("Low",    "#10B981"),
    "MOBILE_USAGE": ("High",   "#F97316"),
}

SNAPSHOTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "snapshots"
)


def _badge(atype: str) -> str:
    sev, color = SEVERITY_MAP.get(atype, ("Low", "#64748B"))
    label = atype.replace("_", " ").title()
    return (
        f'<span style="background:{color}22;color:{color};border:1px solid {color}44;'
        f'padding:2px 8px;border-radius:6px;font-size:0.7rem;font-weight:600;">'
        f'{label} • {sev}</span>'
    )


def render_snapshots(df: pd.DataFrame):
    st.markdown("""
    <style>
    .page-header { font-size:1.4rem;font-weight:800;color:#F1F5F9;margin-bottom:4px; }
    .page-sub    { font-size:0.78rem;color:#64748B;margin-bottom:20px; }
    .snap-card   { background:#1E293B;border:1px solid rgba(255,255,255,0.07);
                   border-radius:14px;padding:12px;margin-bottom:12px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-header">📷 Snapshots</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Captured frames from alert events</div>', unsafe_allow_html=True)

    # ── Filters ─────────────────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        types = ["All", "DROWSINESS", "DISTRACTION", "MOBILE_USAGE"]
        sel_type = st.selectbox("Alert Type", types, key="sn_type")
    with fc2:
        veh_opts = ["All"]
        if df is not None and not df.empty and "vehicle_id" in df.columns:
            veh_opts += sorted(df["vehicle_id"].dropna().unique().tolist())
        sel_veh = st.selectbox("Vehicle", veh_opts, key="sn_veh")
    with fc3:
        try:
            if df is not None and not df.empty and "timestamp" in df.columns:
                min_d = df["timestamp"].min().date()
                max_d = df["timestamp"].max().date()
            else:
                min_d = max_d = pd.Timestamp.now().date()
        except Exception:
            min_d = max_d = pd.Timestamp.now().date()
        date_from = st.date_input("From date", value=min_d, key="sn_from")

    dc2 = st.columns(1)[0]
    with dc2:
        date_to = st.date_input("To date", value=max_d if 'max_d' in dir() else pd.Timestamp.now().date(), key="sn_to")

    # Build snapshot list from df + local files
    snap_items = []

    # From database rows with snapshot URLs/paths
    try:
        if df is not None and not df.empty and "snapshot" in df.columns:
            fdf = df[df["snapshot"].notna() & (df["snapshot"] != "")].copy()
            if sel_type != "All" and "alert_type" in fdf.columns:
                fdf = fdf[fdf["alert_type"] == sel_type]
            if sel_veh != "All" and "vehicle_id" in fdf.columns:
                fdf = fdf[fdf["vehicle_id"] == sel_veh]
            if "timestamp" in fdf.columns:
                fdf = fdf[
                    (fdf["timestamp"].dt.date >= date_from) &
                    (fdf["timestamp"].dt.date <= date_to)
                ]
            for _, row in fdf.iterrows():
                snap_items.append({
                    "path":       row["snapshot"],
                    "alert_type": row.get("alert_type", ""),
                    "vehicle_id": row.get("vehicle_id", ""),
                    "timestamp":  str(row.get("timestamp", ""))[:19],
                    "is_url":     str(row["snapshot"]).startswith("http"),
                })
    except Exception:
        pass

    # From local directory
    try:
        if os.path.exists(SNAPSHOTS_DIR):
            for fname in sorted(os.listdir(SNAPSHOTS_DIR), reverse=True):
                if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue
                parts = fname.rsplit("_", 2)
                atype = parts[0] if parts else ""
                if sel_type != "All" and atype != sel_type:
                    continue
                fpath = os.path.join(SNAPSHOTS_DIR, fname)
                # Avoid duplicates
                if not any(s["path"] == fpath for s in snap_items):
                    snap_items.append({
                        "path":       fpath,
                        "alert_type": atype,
                        "vehicle_id": "Local",
                        "timestamp":  fname,
                        "is_url":     False,
                    })
    except Exception:
        pass

    if not snap_items:
        st.info("No snapshots available.")
        return

    st.markdown(f"**{len(snap_items)} snapshot(s) found**")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Grid (3 columns) ────────────────────────────────────────────────────
    for i in range(0, len(snap_items), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(snap_items):
                break
            item = snap_items[idx]
            with col:
                with st.container():
                    try:
                        if item["is_url"]:
                            st.image(item["path"], use_container_width=True)
                        elif os.path.exists(item["path"]):
                            from PIL import Image
                            img = Image.open(item["path"])
                            st.image(img, use_container_width=True)
                        else:
                            st.markdown(
                                '<div style="height:120px;background:#0F172A;border-radius:8px;'
                                'display:flex;align-items:center;justify-content:center;'
                                'color:#475569;font-size:0.75rem;">Image not found</div>',
                                unsafe_allow_html=True,
                            )
                    except Exception:
                        st.markdown(
                            '<div style="height:120px;background:#0F172A;border-radius:8px;'
                            'display:flex;align-items:center;justify-content:center;'
                            'color:#475569;font-size:0.75rem;">Cannot load image</div>',
                            unsafe_allow_html=True,
                        )

                    atype = item["alert_type"]
                    _, color = SEVERITY_MAP.get(atype, ("Low", "#64748B"))
                    label = atype.replace("_", " ").title() if atype else "Unknown"
                    st.markdown(
                        f'<div style="margin-top:6px;">'
                        f'<span style="background:{color}22;color:{color};'
                        f'border:1px solid {color}44;padding:2px 8px;'
                        f'border-radius:6px;font-size:0.7rem;font-weight:600;">{label}</span>'
                        f'</div>'
                        f'<div style="font-size:0.7rem;color:#64748B;margin-top:4px;">'
                        f'🚗 {item["vehicle_id"]}</div>'
                        f'<div style="font-size:0.68rem;color:#475569;margin-top:2px;">'
                        f'⏱ {item["timestamp"][:19]}</div>',
                        unsafe_allow_html=True,
                    )

                    # Download button for local files
                    if not item["is_url"] and os.path.exists(item["path"]):
                        try:
                            with open(item["path"], "rb") as f:
                                st.download_button(
                                    "⬇ Download",
                                    data=f.read(),
                                    file_name=os.path.basename(item["path"]),
                                    mime="image/jpeg",
                                    key=f"dl_{idx}_{item['path'][-20:]}",
                                    use_container_width=True,
                                )
                        except Exception:
                            pass
