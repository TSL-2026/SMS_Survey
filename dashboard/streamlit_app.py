import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(
    page_title="SMS Dashboard | The Safety Layer",
    page_icon="✈️",
    layout="wide"
)

st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #0a1f35 0%, #1a4a7a 100%);
    padding: 1.2rem 1.5rem; border-radius: 10px; color: white;
    margin-bottom: 1.5rem; display: flex; align-items: center;
    justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;
}
.main-header h1 { font-size: 1.4rem; margin: 0; }
.main-header p  { opacity: 0.7; font-size: 0.82rem; margin: 0; }
.airline-tag {
    background: rgba(240,165,0,0.2); border: 1px solid #f0a500;
    color: #f0a500; padding: 0.3rem 0.8rem; border-radius: 20px;
    font-size: 0.82rem; font-weight: 600;
}
.metric-card {
    background: #f8f9fa; padding: 1.4rem 1rem; border-radius: 12px;
    text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    border: 1px solid #e9ecef;
}
.metric-title { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 1px; color: #6c757d; margin-bottom: 0.4rem; }
.metric-value { font-size: 2.4rem; font-weight: 700; }
.metric-sub   { font-size: 0.73rem; color: #6c757d; margin-top: 0.2rem; }
.good { color: #27ae60; } .fair { color: #f0a500; } .poor { color: #e74c3c; }
.site-footer {
    text-align: center; padding: 1.5rem; color: #6c757d;
    font-size: 0.82rem; border-top: 1px solid #e9ecef; margin-top: 2rem;
}
.site-footer a { color: #2d7dd2; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# ── SUPABASE CONNECTION ────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    try:
        from supabase import create_client
        return create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_SERVICE_KEY"]   # service_role key — server-side only
        )
    except Exception as e:
        st.error(f"Supabase connection failed: {e}")
        return None

supabase = get_supabase()
if supabase is None:
    st.stop()

# ── AUTH ──────────────────────────────────────────────────────────────────────
def login(email, password):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state["sb_session"] = res.session
        return True, None
    except Exception as e:
        return False, str(e)

def logout():
    try: supabase.auth.sign_out()
    except: pass
    st.session_state.pop("sb_session", None)
    st.session_state.pop("airline_info", None)
    st.rerun()

def get_airline_info(session):
    if "airline_info" in st.session_state:
        return st.session_state["airline_info"]
    try:
        res = supabase.table("airline_users") \
            .select("airline_id, role, full_name, airlines(id, name, name_local, slug, status)") \
            .eq("auth_user_id", session.user.id).single().execute()
        if res.data:
            st.session_state["airline_info"] = res.data
            return res.data
    except Exception as e:
        st.error(f"Could not load airline info: {e}")
    return None

# ── LOGIN SCREEN ──────────────────────────────────────────────────────────────
session = st.session_state.get("sb_session")

if not session:
    st.markdown("""
        <div style='text-align:center;margin-bottom:2rem;'>
            <div style='font-size:2.5rem;'>✈️</div>
            <h2 style='color:#0a1f35;'>The Safety Layer</h2>
            <p style='color:#6c757d;'>Safety Manager Portal</p>
        </div>
    """, unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        email    = st.text_input("Email", placeholder="you@airline.com")
        password = st.text_input("Password", type="password")
        if st.button("Sign In →", use_container_width=True, type="primary"):
            if email and password:
                with st.spinner("Signing in..."):
                    ok, err = login(email, password)
                if ok: st.rerun()
                else: st.error(f"❌ {err}")
            else:
                st.error("Please enter email and password.")
        st.caption("Need access? [Request an invite](mailto:hello@gsacharya.com)")
    st.stop()

# ── AIRLINE CONTEXT ───────────────────────────────────────────────────────────
airline_info = get_airline_info(session)
if not airline_info:
    st.error("Could not load airline information.")
    if st.button("Sign Out"): logout()
    st.stop()

airline      = airline_info.get("airlines", {})
airline_id   = airline.get("id")
airline_name = airline.get("name", "Your Airline")

# ── QUESTION METADATA ─────────────────────────────────────────────────────────
# All scores are 0–100 (from Supabase views)
# Pillar A: Safety Policy (5 questions incl. q1_aware)
# Pillar B: Risk Management (8 questions)
# Pillar C: Safety Assurance (5 questions)
# Pillar D: Safety Promotion (5 questions)

PILLAR_COLS = {
    "Safety Policy":    ["q1_score","q2_score","q3_score","q4_score","q5_score"],
    "Risk Management":  ["q6_score","q7_score","q8_score","q9_score","q10_score","q11_score","q12_score","q13_score"],
    "Safety Assurance": ["q14_score","q15_score","q16_score","q19_score","q20_score"],
    "Safety Promotion": ["q17_score","q18_score","q21_score","q22_score","q23_score"],
}

QUESTION_LABELS = {
    "q1_score":  "Aware of Safety Policy Statement",
    "q2_score":  "Regularly informed about Safety Policy",
    "q3_score":  "Policy shows organisation commitment",
    "q4_score":  "Policy applicable to all levels",
    "q5_score":  "Aware of safety performance targets",
    "q6_score":  "Effective hazard reporting process",
    "q7_score":  "Comfortable reporting concerns",
    "q8_score":  "Reporting process easy to use",
    "q9_score":  "Reporting has value for safety",
    "q10_score": "Feel safe to report without fear",
    "q11_score": "Reports unsafe acts via proper channel",
    "q12_score": "Understands risk assessment process",
    "q13_score": "Informed of actions after reporting",
    "q14_score": "Management gives good safety feedback",
    "q15_score": "Management follows up on reported issues",
    "q16_score": "Safety audits carried out regularly",
    "q19_score": "Informed of investigation outcomes",
    "q20_score": "Corrective actions are implemented",
    "q17_score": "Sufficient training to perform duties safely",
    "q18_score": "Has checklists and procedures",
    "q21_score": "Informed about safety-affecting changes",
    "q22_score": "Knows emergency response procedures",
    "q23_score": "Colleagues take safety seriously",
}

SCORE_THRESHOLD = 50  # equivalent to 3.5/5 on 0–100 scale (midpoint above neutral)

# ── DATA LOADING FROM VIEWS ───────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_scores(_airline_id):
    """Load per-response 0-100 scored data from response_scores view."""
    try:
        res = supabase.table("response_scores") \
            .select("*").eq("airline_id", _airline_id).execute()
        if not res.data:
            return pd.DataFrame()
        df = pd.DataFrame(res.data)
        if "submitted_at" in df.columns:
            df["submitted_at"] = pd.to_datetime(df["submitted_at"], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Error loading scores: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_dimension_scores(_airline_id):
    """Load per-response pillar scores and indexes from response_dimension_scores view."""
    try:
        res = supabase.table("response_dimension_scores") \
            .select("*").eq("airline_id", _airline_id).execute()
        if not res.data:
            return pd.DataFrame()
        df = pd.DataFrame(res.data)
        if "submitted_at" in df.columns:
            df["submitted_at"] = pd.to_datetime(df["submitted_at"], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Error loading dimension scores: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_summary(_airline_id):
    """Load airline-level KPI summary from dashboard_summary view."""
    try:
        res = supabase.table("dashboard_summary") \
            .select("*").eq("airline_id", _airline_id).single().execute()
        return res.data or {}
    except Exception as e:
        return {}

@st.cache_data(ttl=300)
def load_trends(_airline_id):
    """Load monthly trend data from dashboard_trends_monthly view."""
    try:
        res = supabase.table("dashboard_trends_monthly") \
            .select("*").eq("airline_id", _airline_id).execute()
        if not res.data:
            return pd.DataFrame()
        df = pd.DataFrame(res.data)
        df["month"] = pd.to_datetime(df["month"], errors="coerce")
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_question_summary(_airline_id):
    """Load question-level averages from dashboard_question_summary view."""
    try:
        res = supabase.table("dashboard_question_summary") \
            .select("*").eq("airline_id", _airline_id).execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# ── LOAD ALL DATA ─────────────────────────────────────────────────────────────
df_scores  = load_scores(airline_id)
df_dim     = load_dimension_scores(airline_id)
summary    = load_summary(airline_id)
df_trends  = load_trends(airline_id)
df_q_summ  = load_question_summary(airline_id)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
st.sidebar.markdown(f"""
    <div style='text-align:center;padding:0.5rem 0 1rem;'>
        <div style='font-size:1.8rem;'>✈️</div>
        <div style='font-weight:700;color:#0a1f35;'>{airline_name}</div>
        <div style='font-size:0.75rem;color:#6c757d;'>
            {airline_info.get('role','').capitalize()} · SMS Dashboard
        </div>
    </div>
""", unsafe_allow_html=True)

st.sidebar.header("🔍 Filters")

# Date filter
if not df_dim.empty and df_dim["submitted_at"].notna().any():
    min_d = df_dim["submitted_at"].min().date()
    max_d = df_dim["submitted_at"].max().date()
    date_range = st.sidebar.date_input("Date Range", [min_d, max_d], min_value=min_d, max_value=max_d)
    if len(date_range) == 2:
        mask = (df_dim["submitted_at"].dt.date >= date_range[0]) & \
               (df_dim["submitted_at"].dt.date <= date_range[1])
        df_dim_f = df_dim[mask].copy()
        df_scores_f = df_scores[
            (df_scores["submitted_at"].dt.date >= date_range[0]) &
            (df_scores["submitted_at"].dt.date <= date_range[1])
        ].copy() if not df_scores.empty else df_scores.copy()
    else:
        df_dim_f = df_dim.copy()
        df_scores_f = df_scores.copy()
else:
    df_dim_f = df_dim.copy()
    df_scores_f = df_scores.copy()
    date_range = [None, None]

# Department filter — dynamic from actual data
depts = ["All Departments"] + sorted(df_dim_f["department"].dropna().unique().tolist()) \
    if not df_dim_f.empty and "department" in df_dim_f.columns else ["All Departments"]
sel_dept = st.sidebar.selectbox("Department", depts)
if sel_dept != "All Departments":
    df_dim_f    = df_dim_f[df_dim_f["department"] == sel_dept]
    df_scores_f = df_scores_f[df_scores_f["department"] == sel_dept] if not df_scores_f.empty else df_scores_f

# Category filter — dynamic from actual data
cats = ["All Categories"] + sorted(df_dim_f["employee_category"].dropna().unique().tolist()) \
    if not df_dim_f.empty and "employee_category" in df_dim_f.columns else ["All Categories"]
sel_cat = st.sidebar.selectbox("Employee Category", cats)
if sel_cat != "All Categories":
    df_dim_f    = df_dim_f[df_dim_f["employee_category"] == sel_cat]
    df_scores_f = df_scores_f[df_scores_f["employee_category"] == sel_cat] if not df_scores_f.empty else df_scores_f

# Language filter
sel_lang = st.sidebar.selectbox("Survey Language", ["All", "English (en)", "Nepali (ne)"])
if sel_lang == "English (en)":
    df_dim_f    = df_dim_f[df_dim_f["language_used"] == "en"] if "language_used" in df_dim_f.columns else df_dim_f
    df_scores_f = df_scores_f[df_scores_f["language_used"] == "en"] if "language_used" in df_scores_f.columns else df_scores_f
elif sel_lang == "Nepali (ne)":
    df_dim_f    = df_dim_f[df_dim_f["language_used"] == "ne"] if "language_used" in df_dim_f.columns else df_dim_f
    df_scores_f = df_scores_f[df_scores_f["language_used"] == "ne"] if "language_used" in df_scores_f.columns else df_scores_f

# Pillar selector for question drill-down
sel_pillar = st.sidebar.selectbox("Question Detail", ["All Pillars"] + list(PILLAR_COLS.keys()))

st.sidebar.markdown("---")
fc = len(df_dim_f)
tc = len(df_dim)
st.sidebar.info(f"📊 **{fc}** of **{tc}** responses shown")
st.sidebar.caption(f"🕐 Refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sign Out"):
    logout()

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
    <div class="main-header">
        <div>
            <h1>✈️ SMS Safety Culture Dashboard</h1>
            <p>ICAO Annex 19 aligned · 4-Pillar SMS Framework · Real-time</p>
        </div>
        <div class="airline-tag">{airline_name}</div>
    </div>
""", unsafe_allow_html=True)

# ── NO DATA STATE ─────────────────────────────────────────────────────────────
if df_dim.empty:
    st.info("📭 No survey responses yet. Share your survey link with employees.")
    survey_url = f"https://tsl-2026.github.io/SMS_Survey/?airline={airline.get('slug','')}"
    st.code(survey_url)
    st.stop()

if df_dim_f.empty:
    st.warning("⚠️ No responses match the current filters. Try adjusting the sidebar.")
    st.stop()

# ── SECTION 1: KPI CARDS ──────────────────────────────────────────────────────
st.header("📊 Key Performance Indicators")

overall_idx   = df_dim_f["overall_index"].mean()
balanced_idx  = df_dim_f["balanced_pillar_index"].mean()
policy_score  = df_dim_f["safety_policy_score"].mean()
risk_score    = df_dim_f["risk_management_score"].mean()
assurance_score = df_dim_f["safety_assurance_score"].mean()
promotion_score = df_dim_f["safety_promotion_score"].mean()

def score_class(v):
    return "good" if v >= 70 else "fair" if v >= 50 else "poor"

c1, c2, c3, c4 = st.columns(4)
with c1:
    cls = score_class(overall_idx)
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🎯 OVERALL SMS INDEX</div>
            <div class="metric-value {cls}">{overall_idx:.1f}</div>
            <div class="metric-sub">out of 100 · threshold ≥ 50</div>
        </div>
    """, unsafe_allow_html=True)
with c2:
    cls = score_class(balanced_idx)
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">⚖️ BALANCED PILLAR INDEX</div>
            <div class="metric-value {cls}">{balanced_idx:.1f}</div>
            <div class="metric-sub">Equal 25% weight per pillar</div>
        </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📋 TOTAL RESPONSES</div>
            <div class="metric-value" style="color:#0a1f35;">{fc}</div>
            <div class="metric-sub">{tc} total · {fc} in filter</div>
        </div>
    """, unsafe_allow_html=True)
with c4:
    last_30 = summary.get("responses_last_30_days", 0)
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📅 LAST 30 DAYS</div>
            <div class="metric-value" style="color:#2d7dd2;">{last_30}</div>
            <div class="metric-sub">Recent submissions</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ── SECTION 2: PILLAR SCORES ──────────────────────────────────────────────────
st.subheader("🏛️ SMS Pillar Performance (ICAO Annex 19)")

pillar_data = {
    "Safety Policy":    policy_score,
    "Risk Management":  risk_score,
    "Safety Assurance": assurance_score,
    "Safety Promotion": promotion_score,
}
p_df = pd.DataFrame(list(pillar_data.items()), columns=["Pillar", "Score"])

col_l, col_r = st.columns([3, 2])

with col_l:
    fig_p = px.bar(
        p_df, x="Pillar", y="Score",
        color="Score",
        color_continuous_scale=["#e74c3c","#f0a500","#27ae60"],
        range_y=[0, 110], text="Score",
        title=f"Pillar Scores — {airline_name}"
    )
    fig_p.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig_p.add_hline(y=50, line_dash="dash", line_color="#e74c3c", line_width=2,
                    annotation_text="Threshold (50)", annotation_position="top right",
                    annotation_font_color="#e74c3c")
    fig_p.update_layout(height=400, showlegend=False, coloraxis_showscale=False,
                        yaxis_title="Score (0–100)")
    st.plotly_chart(fig_p, use_container_width=True)
    try:
        st.download_button("⬇️ Download Pillar Chart",
            data=fig_p.to_image(format="png", width=1200, height=450, scale=2),
            file_name=f"{airline.get('slug','sms')}_pillars.png", mime="image/png")
    except: pass

with col_r:
    # Radar chart
    categories = list(pillar_data.keys())
    values     = list(pillar_data.values()) + [list(pillar_data.values())[0]]
    categories_closed = categories + [categories[0]]
    fig_r = go.Figure(go.Scatterpolar(
        r=values, theta=categories_closed,
        fill="toself", fillcolor="rgba(45,125,210,0.2)",
        line=dict(color="#2d7dd2", width=2),
        name="Score"
    ))
    fig_r.add_trace(go.Scatterpolar(
        r=[50]*5, theta=categories_closed,
        line=dict(color="#e74c3c", width=1, dash="dash"),
        name="Threshold", showlegend=True
    ))
    fig_r.update_layout(
        polar=dict(radialaxis=dict(range=[0, 100], tickfont_size=10)),
        height=400, title="Pillar Radar",
        legend=dict(orientation="h", y=-0.15)
    )
    st.plotly_chart(fig_r, use_container_width=True)

st.markdown("---")

# ── SECTION 3: QUESTION DRILL-DOWN ────────────────────────────────────────────
st.subheader("🔍 Question-Level Analysis")

if not df_q_summ.empty:
    # Filter by pillar if selected
    if sel_pillar != "All Pillars":
        pillar_map = {
            "Safety Policy":    "safety_policy",
            "Risk Management":  "risk_management",
            "Safety Assurance": "safety_assurance",
            "Safety Promotion": "safety_promotion",
        }
        q_filtered = df_q_summ[df_q_summ["pillar"] == pillar_map[sel_pillar]].copy()
    else:
        q_filtered = df_q_summ.copy()

    if not q_filtered.empty:
        # Map question codes to labels
        code_to_label = {
            "q1_aware": QUESTION_LABELS["q1_score"],
            "q2": QUESTION_LABELS["q2_score"],
            "q3": QUESTION_LABELS["q3_score"],
            "q4": QUESTION_LABELS["q4_score"],
            "q5_spi": QUESTION_LABELS["q5_score"],
            "q6": QUESTION_LABELS["q6_score"],
            "q7": QUESTION_LABELS["q7_score"],
            "q8": QUESTION_LABELS["q8_score"],
            "q9": QUESTION_LABELS["q9_score"],
            "q10": QUESTION_LABELS["q10_score"],
            "q11": QUESTION_LABELS["q11_score"],
            "q12_risk_assess": QUESTION_LABELS["q12_score"],
            "q13_action_inform": QUESTION_LABELS["q13_score"],
            "q14": QUESTION_LABELS["q14_score"],
            "q15": QUESTION_LABELS["q15_score"],
            "q16": QUESTION_LABELS["q16_score"],
            "q19_invest_outcome": QUESTION_LABELS["q19_score"],
            "q20_corrective": QUESTION_LABELS["q20_score"],
            "q17": QUESTION_LABELS["q17_score"],
            "q18": QUESTION_LABELS["q18_score"],
            "q21": QUESTION_LABELS["q21_score"],
            "q22": QUESTION_LABELS["q22_score"],
            "q23_peer": QUESTION_LABELS["q23_score"],
        }
        q_filtered["label"] = q_filtered["question_code"].map(code_to_label).fillna(q_filtered["question_code"])
        q_filtered = q_filtered.sort_values("avg_score")

        fig_q = px.bar(
            q_filtered, y="label", x="avg_score",
            color="avg_score",
            color_continuous_scale=["#e74c3c","#f0a500","#27ae60"],
            range_x=[0, 110], orientation="h",
            text="avg_score",
            title=f"Question Scores — {sel_pillar}"
        )
        fig_q.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig_q.add_vline(x=50, line_dash="dash", line_color="#e74c3c", line_width=2,
                        annotation_text="Threshold (50)")
        fig_q.update_layout(
            height=max(400, len(q_filtered) * 38),
            coloraxis_showscale=False,
            yaxis_title="", xaxis_title="Score (0–100)"
        )
        st.plotly_chart(fig_q, use_container_width=True)
        try:
            st.download_button("⬇️ Download Question Chart",
                data=fig_q.to_image(format="png", width=1400, height=max(500, len(q_filtered)*38), scale=2),
                file_name=f"{airline.get('slug','sms')}_questions.png", mime="image/png")
        except: pass

        # Weakest and strongest
        w_col, s_col = st.columns(2)
        with w_col:
            st.markdown("**⚠️ Weakest Questions**")
            for _, row in q_filtered.head(3).iterrows():
                cls = "poor" if row["avg_score"] < 50 else "fair"
                st.markdown(f"<span class='{cls}'>● {row['label']}: **{row['avg_score']:.1f}**</span>", unsafe_allow_html=True)
        with s_col:
            st.markdown("**✅ Strongest Questions**")
            for _, row in q_filtered.tail(3).iloc[::-1].iterrows():
                st.markdown(f"<span class='good'>● {row['label']}: **{row['avg_score']:.1f}**</span>", unsafe_allow_html=True)

st.markdown("---")

# ── SECTION 4: PRIORITY ACTIONS ───────────────────────────────────────────────
st.subheader("🚨 Priority Actions")

if not df_q_summ.empty:
    df_q_summ["label"] = df_q_summ["question_code"].map(code_to_label).fillna(df_q_summ["question_code"])
    critical = df_q_summ[df_q_summ["avg_score"] < 35].sort_values("avg_score")
    attention = df_q_summ[(df_q_summ["avg_score"] >= 35) & (df_q_summ["avg_score"] < 50)].sort_values("avg_score")

    c1, c2 = st.columns(2)
    with c1:
        if not critical.empty:
            st.error("**⚠️ CRITICAL (< 35)**")
            for _, row in critical.iterrows():
                st.write(f"- **{row['label']}**: {row['avg_score']:.1f}/100")
        else:
            st.success("✅ No critical issues")
    with c2:
        if not attention.empty:
            st.warning("**📌 Needs Attention (35–50)**")
            for _, row in attention.iterrows():
                st.write(f"- **{row['label']}**: {row['avg_score']:.1f}/100")
        else:
            st.info("No medium-priority issues.")

st.markdown("---")

# ── SECTION 5: DEPARTMENT BREAKDOWN ──────────────────────────────────────────
st.subheader("🏢 Score by Department")

if not df_dim_f.empty and "department" in df_dim_f.columns:
    dept_df = df_dim_f.groupby("department").agg(
        overall_index=("overall_index", "mean"),
        responses=("overall_index", "count")
    ).reset_index().sort_values("overall_index")
    dept_df["overall_index"] = dept_df["overall_index"].round(1)

    fig_d = px.bar(
        dept_df, y="department", x="overall_index",
        orientation="h", color="overall_index",
        color_continuous_scale=["#e74c3c","#f0a500","#27ae60"],
        range_x=[0, 110], text="overall_index",
        hover_data=["responses"],
        title="Overall SMS Index by Department"
    )
    fig_d.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig_d.add_vline(x=50, line_dash="dash", line_color="#e74c3c", line_width=2)
    fig_d.update_layout(height=max(300, len(dept_df)*50), coloraxis_showscale=False,
                        xaxis_title="Score (0–100)", yaxis_title="")
    st.plotly_chart(fig_d, use_container_width=True)
    try:
        st.download_button("⬇️ Download Department Chart",
            data=fig_d.to_image(format="png", width=1200, height=max(350, len(dept_df)*50), scale=2),
            file_name=f"{airline.get('slug','sms')}_depts.png", mime="image/png")
    except: pass

st.markdown("---")

# ── SECTION 6: MANAGEMENT VS FRONTLINE GAP ───────────────────────────────────
st.subheader("👥 Management vs. Frontline Perception Gap")
st.caption("Gaps ≥ 15 points are a key safety culture risk indicator (ICAO Doc 9859).")

if not df_scores_f.empty and "employee_category" in df_scores_f.columns:
    mgmt      = df_scores_f[df_scores_f["employee_category"] == "Manager / Head of Department"]
    frontline = df_scores_f[~df_scores_f["employee_category"].isin(
        ["Manager / Head of Department", ""]
    ) & df_scores_f["employee_category"].notna()]

    if not mgmt.empty and not frontline.empty:
        gap_rows = []
        for pillar, cols in PILLAR_COLS.items():
            valid_cols = [c for c in cols if c in df_scores_f.columns]
            m_score = mgmt[valid_cols].mean().mean()
            f_score = frontline[valid_cols].mean().mean()
            gap_rows.append({
                "Pillar": pillar,
                "Management": round(m_score, 1),
                "Frontline":  round(f_score, 1),
                "Gap":        round(abs(m_score - f_score), 1)
            })
        gdf = pd.DataFrame(gap_rows)

        fig_g = go.Figure()
        fig_g.add_trace(go.Bar(
            name="Management", x=gdf["Pillar"], y=gdf["Management"],
            marker_color="#2d7dd2", text=gdf["Management"],
            texttemplate="%{text:.1f}", textposition="outside"
        ))
        fig_g.add_trace(go.Bar(
            name="Frontline", x=gdf["Pillar"], y=gdf["Frontline"],
            marker_color="#f0a500", text=gdf["Frontline"],
            texttemplate="%{text:.1f}", textposition="outside"
        ))
        fig_g.add_hline(y=50, line_dash="dash", line_color="#e74c3c",
                        line_width=2, annotation_text="Threshold (50)")
        fig_g.update_layout(
            barmode="group", yaxis_range=[0, 115], height=440,
            title="Management vs. Frontline — Pillar Scores",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            yaxis_title="Score (0–100)"
        )
        st.plotly_chart(fig_g, use_container_width=True)

        large_gaps = gdf[gdf["Gap"] >= 15]
        if not large_gaps.empty:
            st.warning("⚠️ Significant perception gaps in: " +
                       ", ".join(large_gaps["Pillar"]) +
                       " — Investigate and communicate.")
        else:
            st.success("✅ No significant perception gaps detected.")

        try:
            st.download_button("⬇️ Download Gap Chart",
                data=fig_g.to_image(format="png", width=1200, height=480, scale=2),
                file_name=f"{airline.get('slug','sms')}_gap.png", mime="image/png")
        except: pass
    else:
        st.info("Insufficient data for both groups in current filter.")

st.markdown("---")

# ── SECTION 7: TRENDS ─────────────────────────────────────────────────────────
st.subheader("📈 SMS Score Trend Over Time")

if not df_trends.empty and len(df_trends) >= 2:
    fig_t = go.Figure()
    fig_t.add_trace(go.Scatter(
        x=df_trends["month"], y=df_trends["overall_index"],
        mode="lines+markers", name="Overall SMS Index",
        line=dict(color="#2d7dd2", width=2.5), marker=dict(size=7)
    ))
    for pillar, col in [
        ("Safety Policy",    "safety_policy_score"),
        ("Risk Management",  "risk_management_score"),
        ("Safety Assurance", "safety_assurance_score"),
        ("Safety Promotion", "safety_promotion_score"),
    ]:
        if col in df_trends.columns:
            fig_t.add_trace(go.Scatter(
                x=df_trends["month"], y=df_trends[col],
                mode="lines", name=pillar,
                line=dict(width=1.5, dash="dot"), opacity=0.7
            ))
    fig_t.add_hline(y=50, line_dash="dash", line_color="#e74c3c", line_width=2,
                    annotation_text="Threshold (50)", annotation_position="top right")
    fig_t.update_layout(
        height=400, yaxis_range=[0, 110],
        yaxis_title="Score (0–100)", xaxis_title="Month",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        title="Monthly SMS Culture Score Trend"
    )
    st.plotly_chart(fig_t, use_container_width=True)
    try:
        st.download_button("⬇️ Download Trend Chart",
            data=fig_t.to_image(format="png", width=1400, height=450, scale=2),
            file_name=f"{airline.get('slug','sms')}_trend.png", mime="image/png")
    except: pass
else:
    st.info("📈 Trend chart will appear once responses span multiple months.")

st.markdown("---")

# ── SECTION 8: EMPLOYEE FEEDBACK ─────────────────────────────────────────────
st.subheader("💬 Employee Feedback")

# Load raw responses for comments (lightweight query)
@st.cache_data(ttl=300)
def load_comments(_airline_id):
    try:
        res = supabase.table("responses") \
            .select("submitted_at, department, language_used, q24_comments") \
            .eq("airline_id", _airline_id) \
            .not_.is_("q24_comments", "null") \
            .execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except:
        return pd.DataFrame()

df_comments = load_comments(airline_id)
if not df_comments.empty:
    df_comments["submitted_at"] = pd.to_datetime(df_comments["submitted_at"], errors="coerce")
    df_comments = df_comments[df_comments["q24_comments"].str.strip() != ""]
    st.info(f"📝 **{len(df_comments)}** comment(s) received "
            f"({len(df_comments)/len(df_dim)*100:.0f}% of respondents)")
    if not df_comments.empty:
        df_comments = df_comments.sort_values("submitted_at", ascending=False)
        for _, row in df_comments.head(10).iterrows():
            d = row["submitted_at"].strftime("%Y-%m-%d") if pd.notna(row.get("submitted_at")) else "N/A"
            dept = row.get("department") or "Dept not provided"
            lang = (row.get("language_used") or "en").upper()
            with st.expander(f"📝 {dept} · {lang} · {d}"):
                st.write(row["q24_comments"])
else:
    st.info("No written feedback submitted yet.")

st.markdown("---")

# ── SECTION 9: SURVEY LINK ────────────────────────────────────────────────────
st.subheader("🔗 Your Survey Link")
survey_url = f"https://tsl-2026.github.io/SMS_Survey/?airline={airline.get('slug','')}"
st.code(survey_url)
st.caption("Share this link with your employees. It loads your airline branding automatically.")

# ── FOOTER ────────────────────────────────────────────────────────────────────
latest = summary.get("latest_submission_at", "N/A")
if latest and latest != "N/A":
    try:
        latest = datetime.fromisoformat(latest.replace("Z","")).strftime("%Y-%m-%d %H:%M")
    except: pass

st.markdown(f"""
    <div class="site-footer">
        📊 {airline_name} · {fc} of {tc} responses ·
        Last submission: {latest} ·
        <a href="https://thesafetylayer.xyz" target="_blank">The Safety Layer</a> ·
        Built by <a href="https://gsacharya.com" target="_blank">Ghanshyam Acharya</a>
    </div>
""", unsafe_allow_html=True)
