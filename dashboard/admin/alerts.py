import streamlit as st
import pandas as pd
from datetime import timedelta


SEVERITY_MAP = {
    "DROWSINESS":   "Medium",
    "DISTRACTION":  "Low",
    "MOBILE_USAGE": "High",
}

SEVERITY_COLORS = {
    "Low":      "#10B981",
    "Medium":   "#F59E0B",
    "High":     "#F97316",
    "Critical": "#EF4444",
}


def _assign_severity(df: pd.DataFrame) -> pd.DataFrame:
    """Add 'severity' column, escalating to Critical if 3+ same-type in 10 min."""
    if df.empty:
        df["severity"] = pd.Series(dtype=str)
        return df

    df = df.copy()
    df["severity"] = df["alert_type"].map(SEVERITY_MAP).fillna("Low")

    try:
        if "timestamp" in df.columns:
            df_sorted = df.sort_values("timestamp")
            severities = []
            for idx, row in df_sorted.iterrows():
                ts    = row["timestamp"]
                atype = row["alert_type"]
                vid   = row.get("vehicle_id", "")
                window_start = ts - timedelta(minutes=10)
                mask = (
                    (df_sorted["alert_type"] == atype) &
                    (df_sorted["timestamp"] >= window_start) &
                    (df_sorted["timestamp"] <= ts)
                )
                if vid:
                    mask = mask & (df_sorted["vehicle_id"] == vid)
                count = mask.sum()
                if count >= 3:
                    severities.append((idx, "Critical"))
                else:
                    severities.append((idx, SEVERITY_MAP.get(atype, "Low")))

            sev_series = pd.Series(dict(severities))
            df["severity"] = sev_series
    except Exception:
        pass

    return df


def _severity_badge(sev: str) -> str:
    color = SEVERITY_COLORS.get(sev, "#64748B")
    return (
        f'<span style="background:{color}22;color:{color};border:1px solid {color}44;'
        f'padding:2px 8px;border-radius:6px;font-size:0.72rem;font-weight:600;">{sev}</span>'
    )


def render_alerts(df: pd.DataFrame):
    st.markdown("""
    <style>
    .page-header { font-size:1.4rem;font-weight:800;color:#F1F5F9;margin-bottom:4px; }
    .page-sub    { font-size:0.78rem;color:#64748B;margin-bottom:20px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-header">🔔 Alerts</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">All detected alerts with severity classification</div>',
                unsafe_allow_html=True)

    if df is None or df.empty:
        st.info("No alerts recorded yet.")
        return

    # Assign severity
    try:
        df = _assign_severity(df)
    except Exception:
        df["severity"] = df.get("alert_type", pd.Series()).map(SEVERITY_MAP).fillna("Low")

    # ── Filters ─────────────────────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 3])

    with fc1:
        alert_types = ["All"] + sorted(df["alert_type"].dropna().unique().tolist())
        sel_type    = st.selectbox("Alert Type", alert_types, key="al_type")

    with fc2:
        vehicles = ["All"] + sorted(df["vehicle_id"].dropna().unique().tolist()) \
            if "vehicle_id" in df.columns else ["All"]
        sel_veh  = st.selectbox("Vehicle", vehicles, key="al_veh")

    with fc3:
        severities = ["All", "Low", "Medium", "High", "Critical"]
        sel_sev    = st.selectbox("Severity", severities, key="al_sev")

    with fc4:
        search_text = st.text_input("🔍 Search", placeholder="Search vehicle / type…", key="al_search")

    # Date range
    dc1, dc2 = st.columns(2)
    try:
        min_date = df["timestamp"].min().date() if not df.empty else pd.Timestamp.now().date()
        max_date = df["timestamp"].max().date() if not df.empty else pd.Timestamp.now().date()
    except Exception:
        min_date = max_date = pd.Timestamp.now().date()

    with dc1:
        date_from = st.date_input("From", value=min_date, key="al_from")
    with dc2:
        date_to   = st.date_input("To",   value=max_date, key="al_to")

    # Apply filters
    try:
        fdf = df.copy()
        if sel_type != "All":
            fdf = fdf[fdf["alert_type"] == sel_type]
        if sel_veh != "All" and "vehicle_id" in fdf.columns:
            fdf = fdf[fdf["vehicle_id"] == sel_veh]
        if sel_sev != "All":
            fdf = fdf[fdf["severity"] == sel_sev]
        if "timestamp" in fdf.columns:
            fdf = fdf[
                (fdf["timestamp"].dt.date >= date_from) &
                (fdf["timestamp"].dt.date <= date_to)
            ]
        if search_text.strip():
            q = search_text.strip().upper()
            mask = pd.Series([False] * len(fdf), index=fdf.index)
            for col in ["alert_type", "vehicle_id"]:
                if col in fdf.columns:
                    mask = mask | fdf[col].astype(str).str.upper().str.contains(q, na=False)
            fdf = fdf[mask]
    except Exception as e:
        st.warning(f"Filter error: {e}")
        fdf = df.copy()

    st.markdown(f"**{len(fdf)} alert(s) found**")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Severity counts ─────────────────────────────────────────────────────
    if not fdf.empty:
        sev_counts = fdf["severity"].value_counts()
        pill_html  = ""
        for sev in ["Critical", "High", "Medium", "Low"]:
            cnt   = sev_counts.get(sev, 0)
            color = SEVERITY_COLORS.get(sev, "#64748B")
            pill_html += (
                f'<span style="background:{color}22;color:{color};border:1px solid {color}44;'
                f'padding:4px 14px;border-radius:20px;font-size:0.78rem;font-weight:600;">'
                f'{sev}: {cnt}</span>'
            )
        st.markdown(
            f'<div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;">{pill_html}</div>',
            unsafe_allow_html=True,
        )

    # ── Table ────────────────────────────────────────────────────────────────
    try:
        if not fdf.empty:
            display = fdf.copy()
            if "timestamp" in display.columns:
                display["timestamp"] = display["timestamp"].astype(str).str[:19]

            show_cols = [c for c in ["timestamp", "alert_type", "severity", "vehicle_id"] if c in display.columns]
            st.dataframe(display[show_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No alerts match the current filters.")
    except Exception as e:
        st.warning(f"Display error: {e}")
