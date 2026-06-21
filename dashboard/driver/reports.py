import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#94A3B8", family="Inter"),
    margin=dict(l=20, r=20, t=30, b=20),
)

ALERT_COLORS = {
    "DROWSINESS":   "#F59E0B",
    "DISTRACTION":  "#3B82F6",
    "MOBILE_USAGE": "#EF4444",
}


def _score(count: int) -> int:
    return max(0, min(100, 100 - count * 5))


def _grade(score: int):
    if score >= 90: return "A", "#10B981"
    if score >= 75: return "B", "#3B82F6"
    if score >= 60: return "C", "#F59E0B"
    if score >= 40: return "D", "#F97316"
    return "F", "#EF4444"


def render_driver_reports(df: pd.DataFrame, vid: str, driver_name: str):
    st.markdown("""
    <style>
    .page-header { font-size:1.4rem;font-weight:800;color:#F1F5F9;margin-bottom:4px; }
    .page-sub    { font-size:0.78rem;color:#64748B;margin-bottom:20px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-header">📄 My Reports</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-sub">Safety analytics for {driver_name} — Vehicle {vid}</div>',
                unsafe_allow_html=True)

    # Filter to this vehicle
    try:
        if not df.empty and "vehicle_id" in df.columns:
            vdf = df[df["vehicle_id"] == vid].copy()
        else:
            vdf = df.copy() if df is not None else pd.DataFrame()
    except Exception:
        vdf = pd.DataFrame()

    # ── Overall Safety Score ─────────────────────────────────────────────────
    total  = len(vdf)
    sc     = _score(total)
    gr, gc = _grade(sc)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div style="background:#1E293B;border-radius:12px;padding:16px;text-align:center;
             border:1px solid rgba(255,255,255,0.07);">
            <div style="font-size:1.8rem;font-weight:800;color:#EF4444;">{total}</div>
            <div style="font-size:0.75rem;color:#64748B;">Total Alerts</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div style="background:#1E293B;border-radius:12px;padding:16px;text-align:center;
             border:1px solid rgba(255,255,255,0.07);">
            <div style="font-size:1.8rem;font-weight:800;color:{gc};">{sc}</div>
            <div style="font-size:0.75rem;color:#64748B;">Overall Safety Score</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div style="background:#1E293B;border-radius:12px;padding:16px;text-align:center;
             border:1px solid rgba(255,255,255,0.07);">
            <div style="font-size:1.8rem;font-weight:800;color:{gc};">Grade {gr}</div>
            <div style="font-size:0.75rem;color:#64748B;">Performance Grade</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    if vdf.empty:
        st.info("No alert data available for your vehicle.")
        return

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("**Alert Breakdown**")
        try:
            dist = vdf["alert_type"].value_counts().reset_index()
            dist.columns = ["Type", "Count"]
            bar_colors = [ALERT_COLORS.get(t, "#64748B") for t in dist["Type"]]
            fig = go.Figure(go.Bar(
                y=dist["Type"], x=dist["Count"], orientation="h",
                marker_color=bar_colors, text=dist["Count"], textposition="auto",
            ))
            fig.update_layout(**PLOTLY_LAYOUT, height=220,
                              xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
                              yaxis=dict(showgrid=False))
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Chart error: {e}")

    with col_right:
        st.markdown("**Weekly Trend**")
        try:
            if "timestamp" in vdf.columns:
                end_date   = pd.Timestamp.now().normalize()
                start_date = end_date - timedelta(days=6)
                week = vdf[(vdf["timestamp"] >= start_date) &
                           (vdf["timestamp"] <= end_date + timedelta(days=1))].copy()
                week["date"] = week["timestamp"].dt.date
                daily = week.groupby("date").size().reset_index(name="count")
                dates = pd.date_range(start=start_date.date(), periods=7).date
                full  = pd.DataFrame({"date": dates})
                daily["date"] = pd.to_datetime(daily["date"]).dt.date
                merged = full.merge(daily, on="date", how="left").fillna(0)

                fig2 = go.Figure(go.Scatter(
                    x=merged["date"].astype(str).tolist(),
                    y=merged["count"].tolist(),
                    mode="lines+markers",
                    line=dict(color="#3B82F6", width=2),
                    marker=dict(size=6, color="#3B82F6"),
                    fill="tozeroy",
                    fillcolor="rgba(59,130,246,0.08)",
                ))
                fig2.update_layout(**PLOTLY_LAYOUT, height=220,
                                   xaxis=dict(showgrid=False),
                                   yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No timestamp data.")
        except Exception as e:
            st.warning(f"Trend chart error: {e}")

    # Export CSV
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    try:
        export_cols = [c for c in ["timestamp", "alert_type"] if c in vdf.columns]
        csv_data = vdf[export_cols].to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇ Export My Report (CSV)",
            data=csv_data,
            file_name=f"my_report_{vid}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    except Exception as e:
        st.warning(f"Export error: {e}")
