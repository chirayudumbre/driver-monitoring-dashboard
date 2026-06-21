import streamlit as st
import pandas as pd
from datetime import timedelta

SEVERITY_MAP = {
    "DROWSINESS":   ("Medium", "#F59E0B"),
    "DISTRACTION":  ("Low",    "#10B981"),
    "MOBILE_USAGE": ("High",   "#F97316"),
}


def _assign_severity(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        df["severity"] = pd.Series(dtype=str)
        return df
    df = df.copy()
    df["severity"] = df["alert_type"].map({k: v[0] for k, v in SEVERITY_MAP.items()}).fillna("Low")
    try:
        if "timestamp" in df.columns:
            df_sorted = df.sort_values("timestamp")
            severities = {}
            for idx, row in df_sorted.iterrows():
                ts   = row["timestamp"]
                atype = row["alert_type"]
                w_start = ts - timedelta(minutes=10)
                mask = (
                    (df_sorted["alert_type"] == atype) &
                    (df_sorted["timestamp"] >= w_start) &
                    (df_sorted["timestamp"] <= ts)
                )
                severities[idx] = "Critical" if mask.sum() >= 3 else SEVERITY_MAP.get(atype, ("Low",))[0]
            df["severity"] = pd.Series(severities)
    except Exception:
        pass
    return df


def render_driver_alerts(df: pd.DataFrame, vid: str):
    st.markdown("""
    <style>
    .page-header { font-size:1.4rem;font-weight:800;color:#F1F5F9;margin-bottom:4px; }
    .page-sub    { font-size:0.78rem;color:#64748B;margin-bottom:20px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-header">🔔 My Alerts</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-sub">Alert history for vehicle {vid}</div>',
                unsafe_allow_html=True)

    # Filter to this vehicle
    try:
        if not df.empty and "vehicle_id" in df.columns:
            fdf = df[df["vehicle_id"] == vid].copy()
        else:
            fdf = df.copy() if df is not None else pd.DataFrame()
    except Exception:
        fdf = pd.DataFrame()

    if fdf.empty:
        st.info("No alerts recorded for your vehicle.")
        return

    fdf = _assign_severity(fdf)

    # Filters
    fc1, fc2 = st.columns(2)
    with fc1:
        types = ["All"] + sorted(fdf["alert_type"].dropna().unique().tolist())
        sel_type = st.selectbox("Alert Type", types, key="da_type")
    with fc2:
        severities = ["All", "Low", "Medium", "High", "Critical"]
        sel_sev = st.selectbox("Severity", severities, key="da_sev")

    dc1, dc2 = st.columns(2)
    try:
        min_d = fdf["timestamp"].min().date() if not fdf.empty else pd.Timestamp.now().date()
        max_d = fdf["timestamp"].max().date() if not fdf.empty else pd.Timestamp.now().date()
    except Exception:
        min_d = max_d = pd.Timestamp.now().date()

    with dc1:
        date_from = st.date_input("From", value=min_d, key="da_from")
    with dc2:
        date_to   = st.date_input("To",   value=max_d, key="da_to")

    # Apply filters
    try:
        if sel_type != "All":
            fdf = fdf[fdf["alert_type"] == sel_type]
        if sel_sev != "All":
            fdf = fdf[fdf["severity"] == sel_sev]
        if "timestamp" in fdf.columns:
            fdf = fdf[
                (fdf["timestamp"].dt.date >= date_from) &
                (fdf["timestamp"].dt.date <= date_to)
            ]
    except Exception as e:
        st.warning(f"Filter error: {e}")

    st.markdown(f"**{len(fdf)} alert(s) found**")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Severity color pills
    if not fdf.empty:
        sev_counts = fdf["severity"].value_counts()
        COLORS = {"Critical": "#EF4444", "High": "#F97316", "Medium": "#F59E0B", "Low": "#10B981"}
        pills = "".join([
            f'<span style="background:{COLORS.get(s,"#64748B")}22;color:{COLORS.get(s,"#64748B")};'
            f'border:1px solid {COLORS.get(s,"#64748B")}44;padding:3px 12px;border-radius:20px;'
            f'font-size:0.75rem;font-weight:600;">{s}: {sev_counts.get(s, 0)}</span>'
            for s in ["Critical", "High", "Medium", "Low"]
        ])
        st.markdown(f'<div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;">{pills}</div>',
                    unsafe_allow_html=True)

    # Table
    try:
        if not fdf.empty:
            display = fdf.copy()
            if "timestamp" in display.columns:
                display["timestamp"] = display["timestamp"].astype(str).str[:19]
            show_cols = [c for c in ["timestamp", "alert_type", "severity"] if c in display.columns]
            st.dataframe(display[show_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No alerts match the current filters.")
    except Exception as e:
        st.warning(f"Display error: {e}")
