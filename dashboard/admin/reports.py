import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

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


def _safety_score(count: int) -> int:
    return max(0, min(100, 100 - count * 5))


def _score_grade(score: int) -> tuple:
    if score >= 90: return "A", "#10B981"
    if score >= 75: return "B", "#3B82F6"
    if score >= 60: return "C", "#F59E0B"
    if score >= 40: return "D", "#F97316"
    return "F", "#EF4444"


def _period_df(df: pd.DataFrame, days: int) -> pd.DataFrame:
    if df.empty or "timestamp" not in df.columns:
        return df
    cutoff = pd.Timestamp.now() - timedelta(days=days)
    return df[df["timestamp"] >= cutoff].copy()


def _render_period(df: pd.DataFrame, period_label: str, days: int, vehicles: dict, drivers: dict):
    try:
        pdf = _period_df(df, days)
    except Exception:
        pdf = pd.DataFrame(columns=["timestamp", "alert_type", "vehicle_id"])

    total     = len(pdf)
    score     = _safety_score(total)
    grade, gc = _score_grade(score)

    # Summary row
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
            <div style="font-size:1.8rem;font-weight:800;color:{gc};">{score}</div>
            <div style="font-size:0.75rem;color:#64748B;">Safety Score</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div style="background:#1E293B;border-radius:12px;padding:16px;text-align:center;
             border:1px solid rgba(255,255,255,0.07);">
            <div style="font-size:1.8rem;font-weight:800;color:{gc};">Grade {grade}</div>
            <div style="font-size:0.75rem;color:#64748B;">Performance</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    if pdf.empty:
        st.info("No alerts in this period.")
    else:
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("**Alert Breakdown by Type**")
            try:
                dist = pdf["alert_type"].value_counts().reset_index()
                dist.columns = ["Type", "Count"]
                bar_colors = [ALERT_COLORS.get(t, "#64748B") for t in dist["Type"]]
                fig = go.Figure(go.Bar(
                    y=dist["Type"],
                    x=dist["Count"],
                    orientation="h",
                    marker_color=bar_colors,
                    text=dist["Count"],
                    textposition="auto",
                ))
                fig.update_layout(**PLOTLY_LAYOUT, height=220,
                                  xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
                                  yaxis=dict(showgrid=False))
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Chart error: {e}")

        with col_right:
            st.markdown("**Top Vehicles by Alert Count**")
            try:
                if "vehicle_id" in pdf.columns:
                    top_v = pdf["vehicle_id"].value_counts().head(8).reset_index()
                    top_v.columns = ["Vehicle", "Alerts"]
                    fig2 = go.Figure(go.Bar(
                        x=top_v["Vehicle"],
                        y=top_v["Alerts"],
                        marker_color="#3B82F6",
                        text=top_v["Alerts"],
                        textposition="auto",
                    ))
                    fig2.update_layout(**PLOTLY_LAYOUT, height=220,
                                       xaxis=dict(showgrid=False),
                                       yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"))
                    st.plotly_chart(fig2, use_container_width=True)
            except Exception as e:
                st.warning(f"Chart error: {e}")

        # Export
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        try:
            export_cols = [c for c in ["timestamp", "alert_type", "vehicle_id"] if c in pdf.columns]
            csv_data = pdf[export_cols].to_csv(index=False).encode("utf-8")
            st.download_button(
                f"⬇ Export {period_label} Report (CSV)",
                data=csv_data,
                file_name=f"report_{period_label.lower()}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                key=f"export_{period_label}",
            )
        except Exception as e:
            st.warning(f"Export error: {e}")


def render_reports(df: pd.DataFrame, vehicles: dict, drivers: dict):
    st.markdown("""
    <style>
    .page-header { font-size:1.4rem;font-weight:800;color:#F1F5F9;margin-bottom:4px; }
    .page-sub    { font-size:0.78rem;color:#64748B;margin-bottom:20px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-header">📄 Reports</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Fleet performance reports and analytics</div>',
                unsafe_allow_html=True)

    tab_daily, tab_weekly, tab_monthly = st.tabs(["📅 Daily", "📆 Weekly", "🗓 Monthly"])

    with tab_daily:
        st.markdown("#### Today's Report")
        _render_period(df, "Daily", 1, vehicles, drivers)

    with tab_weekly:
        st.markdown("#### Last 7 Days Report")
        _render_period(df, "Weekly", 7, vehicles, drivers)

    with tab_monthly:
        st.markdown("#### Last 30 Days Report")
        _render_period(df, "Monthly", 30, vehicles, drivers)
