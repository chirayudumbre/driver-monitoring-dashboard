import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta


CARD_CSS = """
<style>
.kpi-card {
    background: #1E293B;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 20px;
    text-align: center;
}
.kpi-value { font-size: 2rem; font-weight: 800; }
.kpi-label { font-size: 0.78rem; color: #64748B; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.06em; }
.section-title { font-size: 1rem; font-weight: 700; color: #F1F5F9; margin: 20px 0 10px; }
.alert-table-row { background: #1E293B; }
</style>
"""

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#94A3B8", family="Inter"),
    margin=dict(l=20, r=20, t=30, b=20),
)


def compute_severity(df: pd.DataFrame, row):
    """Compute severity for a single alert row."""
    atype = row.get("alert_type", "")
    base = {"DROWSINESS": "Medium", "DISTRACTION": "Low", "MOBILE_USAGE": "High"}.get(atype, "Low")

    if df.empty or "timestamp" not in df.columns:
        return base

    try:
        ts = row.get("timestamp")
        if pd.isna(ts):
            return base
        window_start = ts - timedelta(minutes=10)
        vid = row.get("vehicle_id", "")
        mask = (
            (df["alert_type"] == atype) &
            (df["timestamp"] >= window_start) &
            (df["timestamp"] <= ts)
        )
        if vid:
            mask = mask & (df["vehicle_id"] == vid)
        if mask.sum() >= 3:
            return "Critical"
    except Exception:
        pass
    return base


def safety_score(df: pd.DataFrame, vehicle_id: str = None) -> int:
    """Score 0-100 based on alert frequency."""
    try:
        if df.empty:
            return 100
        d = df if vehicle_id is None else df[df["vehicle_id"] == vehicle_id]
        today = pd.Timestamp.now().date()
        today_alerts = d[d["timestamp"].dt.date == today] if "timestamp" in d.columns else d
        count = len(today_alerts)
        score = max(0, 100 - count * 5)
        return min(100, score)
    except Exception:
        return 100


def render_admin_dashboard(df: pd.DataFrame, vehicles: dict, drivers: dict):
    st.markdown(CARD_CSS, unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">
        <span style="font-size:1.6rem;">📊</span>
        <div>
            <div style="font-size:1.4rem;font-weight:800;color:#F1F5F9;">Fleet Dashboard</div>
            <div style="font-size:0.78rem;color:#64748B;">Real-time overview of all vehicles & drivers</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI Computations ────────────────────────────────────────────────────
    total_vehicles  = len(vehicles)
    active_vehicles = sum(1 for v in vehicles.values()
                          if isinstance(v, dict) and v.get("status", "Active") == "Active")
    total_drivers   = len(drivers) if drivers else len(vehicles)

    today = pd.Timestamp.now().date()
    try:
        today_alerts = df[df["timestamp"].dt.date == today] if not df.empty else df
        todays_count = len(today_alerts)
    except Exception:
        today_alerts = pd.DataFrame()
        todays_count = 0

    fleet_score = safety_score(df)

    # Critical: same type 3+ times in 10 min
    critical_count = 0
    try:
        if not df.empty and "timestamp" in df.columns:
            for _, row in df.iterrows():
                if compute_severity(df, row) == "Critical":
                    critical_count += 1
    except Exception:
        critical_count = 0

    # ── Row 1 KPIs ──────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value" style="color:#3B82F6;">{total_vehicles}</div>
            <div class="kpi-label">Total Vehicles</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value" style="color:#10B981;">{active_vehicles}</div>
            <div class="kpi-label">Active Vehicles</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value" style="color:#A78BFA;">{total_drivers}</div>
            <div class="kpi-label">Total Drivers</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3)
    with c4:
        color = "#F59E0B" if todays_count > 0 else "#10B981"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value" style="color:{color};">{todays_count}</div>
            <div class="kpi-label">Today's Alerts</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        score_color = "#10B981" if fleet_score >= 80 else "#F59E0B" if fleet_score >= 60 else "#EF4444"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value" style="color:{score_color};">{fleet_score}</div>
            <div class="kpi-label">Fleet Safety Score</div>
        </div>""", unsafe_allow_html=True)
    with c6:
        crit_color = "#EF4444" if critical_count > 0 else "#10B981"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value" style="color:{crit_color};">{critical_count}</div>
            <div class="kpi-label">Emergency Cases</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Charts ──────────────────────────────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('<div class="section-title">Alert Distribution</div>', unsafe_allow_html=True)
        try:
            if not df.empty and "alert_type" in df.columns:
                dist = df["alert_type"].value_counts().reset_index()
                dist.columns = ["Alert Type", "Count"]
                colors = {"DROWSINESS": "#F59E0B", "DISTRACTION": "#3B82F6", "MOBILE_USAGE": "#EF4444"}
                bar_colors = [colors.get(t, "#64748B") for t in dist["Alert Type"]]
                fig = go.Figure(go.Bar(
                    x=dist["Alert Type"],
                    y=dist["Count"],
                    marker_color=bar_colors,
                    text=dist["Count"],
                    textposition="auto",
                ))
                fig.update_layout(**PLOTLY_LAYOUT, height=260,
                                  xaxis=dict(showgrid=False),
                                  yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No alert data available.")
        except Exception as e:
            st.warning(f"Chart error: {e}")

    with col_right:
        st.markdown('<div class="section-title">7-Day Alert Trend</div>', unsafe_allow_html=True)
        try:
            if not df.empty and "timestamp" in df.columns:
                end_date   = pd.Timestamp.now().normalize()
                start_date = end_date - timedelta(days=6)
                mask  = (df["timestamp"] >= start_date) & (df["timestamp"] <= end_date + timedelta(days=1))
                week_df = df[mask].copy()
                week_df["date"] = week_df["timestamp"].dt.date
                daily = week_df.groupby("date").size().reset_index(name="count")
                date_range = pd.date_range(start=start_date.date(), periods=7).date
                full = pd.DataFrame({"date": date_range})
                daily["date"] = pd.to_datetime(daily["date"]).dt.date
                merged = full.merge(daily, on="date", how="left").fillna(0)

                fig2 = go.Figure(go.Scatter(
                    x=merged["date"].astype(str),
                    y=merged["count"],
                    mode="lines+markers",
                    line=dict(color="#3B82F6", width=2),
                    marker=dict(color="#3B82F6", size=6),
                    fill="tozeroy",
                    fillcolor="rgba(59,130,246,0.08)",
                ))
                fig2.update_layout(**PLOTLY_LAYOUT, height=260,
                                   xaxis=dict(showgrid=False),
                                   yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No trend data available.")
        except Exception as e:
            st.warning(f"Trend chart error: {e}")

    # ── Recent Alerts Table ─────────────────────────────────────────────────
    st.markdown('<div class="section-title">Recent Alerts (Last 10)</div>', unsafe_allow_html=True)
    try:
        if not df.empty:
            cols = [c for c in ["timestamp", "alert_type", "vehicle_id"] if c in df.columns]
            recent = df[cols].head(10).copy()
            if "timestamp" in recent.columns:
                recent["timestamp"] = recent["timestamp"].astype(str).str[:19]
            st.dataframe(
                recent,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No alerts recorded yet.")
    except Exception as e:
        st.warning(f"Table error: {e}")

    # ── Vehicle Status Table ────────────────────────────────────────────────
    st.markdown('<div class="section-title">Vehicle Status</div>', unsafe_allow_html=True)
    try:
        rows = []
        for vid, vdata in vehicles.items():
            v = vdata if isinstance(vdata, dict) else {}
            alert_count = len(df[df["vehicle_id"] == vid]) if not df.empty else 0
            rows.append({
                "Vehicle ID":  vid,
                "Driver":      v.get("driver", "—"),
                "Status":      v.get("status", "Active"),
                "Model":       v.get("vehicle_model", "—"),
                "Alert Count": alert_count,
            })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No vehicles registered.")
    except Exception as e:
        st.warning(f"Vehicle table error: {e}")
