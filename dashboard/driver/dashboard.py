import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import timedelta

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


def _safety_score(df: pd.DataFrame) -> int:
    try:
        if df.empty:
            return 100
        today = pd.Timestamp.now().date()
        today_df = df[df["timestamp"].dt.date == today] if "timestamp" in df.columns else df
        count = len(today_df)
        return max(0, min(100, 100 - count * 5))
    except Exception:
        return 100


def _score_grade(score: int):
    if score >= 90: return "A", "#10B981", "Excellent"
    if score >= 75: return "B", "#3B82F6", "Good"
    if score >= 60: return "C", "#F59E0B", "Fair"
    if score >= 40: return "D", "#F97316", "Poor"
    return "F", "#EF4444", "Critical"


def _risk_level(score: int):
    if score >= 80: return "Low",    "#10B981"
    if score >= 60: return "Medium", "#F59E0B"
    return "High", "#EF4444"


def render_driver_dashboard(df: pd.DataFrame, vid: str, driver_name: str):
    st.markdown("""
    <style>
    .kpi-card { background:#1E293B;border:1px solid rgba(255,255,255,0.07);
                border-radius:14px;padding:18px;text-align:center; }
    .kpi-value { font-size:1.9rem;font-weight:800; }
    .kpi-label { font-size:0.75rem;color:#64748B;margin-top:4px;
                 text-transform:uppercase;letter-spacing:0.06em; }
    </style>
    """, unsafe_allow_html=True)

    # ── Driver Header ────────────────────────────────────────────────────────
    score          = _safety_score(df)
    grade, gc, gtxt = _score_grade(score)
    risk, rc       = _risk_level(score)

    st.markdown(f"""
    <div style="background:#1E293B;border:1px solid rgba(255,255,255,0.07);
         border-radius:16px;padding:20px 24px;margin-bottom:20px;
         display:flex;align-items:center;gap:18px;flex-wrap:wrap;">
        <div style="font-size:2.5rem;">👤</div>
        <div style="flex:1;min-width:160px;">
            <div style="font-size:1.3rem;font-weight:800;color:#F1F5F9;">{driver_name}</div>
            <div style="font-size:0.78rem;color:#64748B;font-family:monospace;margin-top:2px;">
                Vehicle: {vid}</div>
        </div>
        <div style="text-align:center;">
            <div style="font-size:2rem;font-weight:800;color:{gc};">Grade {grade}</div>
            <div style="font-size:0.72rem;color:#64748B;">{gtxt}</div>
        </div>
        <div style="text-align:center;">
            <div style="font-size:1.5rem;font-weight:800;color:{rc};">{risk} Risk</div>
            <div style="font-size:0.72rem;color:#64748B;">Current Level</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI Cards ────────────────────────────────────────────────────────────
    today = pd.Timestamp.now().date()
    try:
        today_df = df[df["timestamp"].dt.date == today] if not df.empty and "timestamp" in df.columns else pd.DataFrame()
        today_count = len(today_df)
    except Exception:
        today_df = pd.DataFrame()
        today_count = 0

    try:
        latest_alert = str(df.iloc[0]["alert_type"]).replace("_", " ").title() if not df.empty else "—"
        latest_ts    = str(df.iloc[0]["timestamp"])[:19] if not df.empty else "—"
    except Exception:
        latest_alert = "—"
        latest_ts    = "—"

    c1, c2, c3 = st.columns(3)
    with c1:
        color = "#F59E0B" if today_count > 0 else "#10B981"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value" style="color:{color};">{today_count}</div>
            <div class="kpi-label">Today's Alerts</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value" style="color:{gc};">{score}</div>
            <div class="kpi-label">Safety Score</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        total = len(df) if not df.empty else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value" style="color:#A78BFA;">{total}</div>
            <div class="kpi-label">Total Alerts</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Latest alert card
    if latest_alert != "—":
        a_color = ALERT_COLORS.get(df.iloc[0]["alert_type"] if not df.empty else "", "#64748B")
        st.markdown(f"""
        <div style="background:#1E293B;border-left:4px solid {a_color};
             border-radius:10px;padding:12px 16px;margin-bottom:16px;">
            <div style="font-size:0.7rem;color:#64748B;text-transform:uppercase;
                 letter-spacing:0.06em;">Latest Alert</div>
            <div style="font-size:1rem;font-weight:700;color:{a_color};margin-top:2px;">
                {latest_alert}</div>
            <div style="font-size:0.72rem;color:#64748B;margin-top:2px;">⏱ {latest_ts}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── 7-Day Safety Trend ───────────────────────────────────────────────────
    col_chart, col_summary = st.columns([3, 2])

    with col_chart:
        st.markdown("**📈 Safety Score – Last 7 Days**")
        try:
            if not df.empty and "timestamp" in df.columns:
                end_date   = pd.Timestamp.now().normalize()
                start_date = end_date - timedelta(days=6)
                mask  = (df["timestamp"] >= start_date) & (df["timestamp"] <= end_date + timedelta(days=1))
                week  = df[mask].copy()
                week["date"] = week["timestamp"].dt.date
                daily = week.groupby("date").size().reset_index(name="count")
                dates = pd.date_range(start=start_date.date(), periods=7).date
                full  = pd.DataFrame({"date": dates})
                daily["date"] = pd.to_datetime(daily["date"]).dt.date
                merged = full.merge(daily, on="date", how="left").fillna(0)
                scores = merged["count"].apply(lambda c: max(0, 100 - c * 5)).tolist()

                fig = go.Figure(go.Scatter(
                    x=merged["date"].astype(str).tolist(),
                    y=scores,
                    mode="lines+markers",
                    line=dict(color="#10B981", width=2),
                    marker=dict(color="#10B981", size=7),
                    fill="tozeroy",
                    fillcolor="rgba(16,185,129,0.08)",
                ))
                fig.update_layout(**PLOTLY_LAYOUT, height=230,
                                  yaxis=dict(range=[0, 110], showgrid=True,
                                             gridcolor="rgba(255,255,255,0.05)"),
                                  xaxis=dict(showgrid=False))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data for trend chart.")
        except Exception as e:
            st.warning(f"Trend chart error: {e}")

    with col_summary:
        st.markdown("**📊 Alert Summary**")
        try:
            drowsy_c = len(df[df["alert_type"] == "DROWSINESS"])  if not df.empty else 0
            phone_c  = len(df[df["alert_type"] == "MOBILE_USAGE"]) if not df.empty else 0
            dist_c   = len(df[df["alert_type"] == "DISTRACTION"]) if not df.empty else 0
        except Exception:
            drowsy_c = phone_c = dist_c = 0

        for label, count, color, icon in [
            ("Drowsiness", drowsy_c, "#F59E0B", "😴"),
            ("Phone Usage", phone_c, "#EF4444", "📱"),
            ("Distraction", dist_c, "#3B82F6", "👀"),
        ]:
            st.markdown(f"""
            <div style="background:#1E293B;border-radius:10px;padding:12px 16px;
                 margin-bottom:8px;display:flex;justify-content:space-between;
                 align-items:center;border:1px solid rgba(255,255,255,0.06);">
                <span style="color:#94A3B8;font-size:0.82rem;">{icon} {label}</span>
                <span style="color:{color};font-weight:700;font-size:1.1rem;">{count}</span>
            </div>
            """, unsafe_allow_html=True)
