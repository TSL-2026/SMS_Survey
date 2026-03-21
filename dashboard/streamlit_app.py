import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="SMS Dashboard | The Safety Layer", page_icon="✈️", layout="wide")

st.markdown("""
<style>
.main-header { background: linear-gradient(135deg, #0a1f35 0%, #1a4a7a 100%); padding: 1.2rem 1.5rem; border-radius: 10px; color: white; margin-bottom: 1.5rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; }
.main-header h1 { font-size: 1.4rem; margin: 0; }
.main-header p  { opacity: 0.7; font-size: 0.82rem; margin: 0; }
.airline-tag { background: rgba(240,165,0,0.2); border: 1px solid #f0a500; color: #f0a500; padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.82rem; font-weight: 600; }
.metric-card { background: #f8f9fa; padding: 1.4rem 1rem; border-radius: 12px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border: 1px solid #e9ecef; }
.metric-title { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 1px; color: #6c757d; margin-bottom: 0.4rem; }
.metric-value { font-size: 2.4rem; font-weight: 700; }
.metric-sub   { font-size: 0.73rem; color: #6c757d; margin-top: 0.2rem; }
.good { color: #27ae60; } .fair { color: #f0a500; } .poor { color: #e74c3c; }
.site-footer { text-align: center; padding: 1.5rem; color: #6c757d; font-size: 0.82rem; border-top: 1px solid #e9ecef; margin-top: 2rem; }
.site-footer a { color: #2d7dd2; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_supabase():
    try:
        from supabase import create_client
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        st.error(f"Supabase connection failed: {e}")
        return None

supabase = get_supabase()
if supabase is None:
    st.stop()

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
        authed = get_supabase()
        authed.postgrest.auth(session.access_token)
        res = authed.table("airline_users") \
            .select("airline_id, role, full_name, airlines(id, name, name_local, slug, plan, status)") \
            .eq("auth_user_id", session.user.id).single().execute()
        if res.data:
            st.session_state["airline_info"] = res.data
            return res.data
    except Exception as e:
        st.error(f"Could not load airline info: {e}")
    return None

session = st.session_state.get("sb_session")

if not session:
    st.markdown("<div style='text-align:center;margin-bottom:2rem;'><div style='font-size:2.5rem;'>✈️</div><h2 style='color:#0a1f35;'>The Safety Layer</h2><p style='color:#6c757d;'>Safety Manager Portal</p></div>", unsafe_allow_html=True)
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

airline_info = get_airline_info(session)
if not airline_info:
    st.error("Could not load airline information.")
    if st.button("Sign Out"): logout()
    st.stop()

airline      = airline_info.get("airlines", {})
airline_id   = airline.get("id")
airline_name = airline.get("name", "Your Airline")

SCORE_COLS = ['q2','q3','q4','q5_spi','q6','q7','q8','q9','q10','q11','q12_risk_assess','q13_action_inform','q14','q15','q16','q19_invest_outcome','q20_corrective','q17','q18','q21','q22','q23_peer']

SMS_PILLARS = {
    "Pillar 1: Safety Policy & Objectives":  {'cols': ['q2','q3','q4','q5_spi']},
    "Pillar 2: Safety Risk Management":       {'cols': ['q6','q7','q8','q9','q10','q11','q12_risk_assess','q13_action_inform']},
    "Pillar 3: Safety Assurance":             {'cols': ['q14','q15','q16','q19_invest_outcome','q20_corrective']},
    "Pillar 4: Safety Promotion":             {'cols': ['q17','q18','q21','q22','q23_peer']},
}

QUESTION_NAMES = {
    'q2':'Regularly informed about Safety Policy','q3':'Policy shows company commitment','q4':'Policy applicable to all levels','q5_spi':'★ Aware of safety performance targets','q6':'Effective hazard reporting process','q7':'Comfortable reporting concerns','q8':'Reporting process easy to use','q9':'Reporting has value for safety','q10':'★ Feel safe to report without fear','q11':'★ Reports unsafe acts via proper channel','q12_risk_assess':'★ Understands risk assessment process','q13_action_inform':'★ Informed of actions after reporting','q14':'Management gives good safety feedback','q15':'Management follows up on reported issues','q16':'Safety audits carried out regularly','q19_invest_outcome':'★ Informed of investigation outcomes','q20_corrective':'★ Corrective actions are implemented','q17':'Enough training to complete tasks safely','q18':'Has checklists and procedures','q21':'Informed about safety-affecting changes','q22':'Knows emergency response document','q23_peer':'★ Colleagues take safety seriously',
}

@st.cache_data(ttl=300)
def load_responses(_airline_id, _token):
    try:
        authed = get_supabase()
        authed.postgrest.auth(_token)
        res = authed.table("responses").select("*").eq("airline_id", _airline_id).execute()
        if not res.data: return pd.DataFrame()
        df = pd.DataFrame(res.data)
        if 'submitted_at' in df.columns:
            df['submitted_at'] = pd.to_datetime(df['submitted_at'], errors='coerce')
        for c in SCORE_COLS:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
        if 'q1_aware' in df.columns:
            df['q1_aware'] = df['q1_aware'].astype(str).str.lower().map({'true':True,'false':False,'1':True,'0':False})
        return df
    except Exception as e:
        st.error(f"Error loading responses: {e}")
        return pd.DataFrame()

df_raw = load_responses(airline_id, session.access_token)

# SIDEBAR
st.sidebar.markdown(f"<div style='text-align:center;padding:0.5rem 0 1rem;'><div style='font-size:1.8rem;'>✈️</div><div style='font-weight:700;color:#0a1f35;'>{airline_name}</div><div style='font-size:0.75rem;color:#6c757d;'>{airline_info.get('role','').capitalize()} · {airline.get('plan','free').capitalize()} Plan</div></div>", unsafe_allow_html=True)
st.sidebar.header("🔍 Filters")

if 'submitted_at' in df_raw.columns and df_raw['submitted_at'].notna().any():
    min_d = df_raw['submitted_at'].min().date()
    max_d = df_raw['submitted_at'].max().date()
    date_range = st.sidebar.date_input("Date Range", [min_d, max_d], min_value=min_d, max_value=max_d)
    df_filtered = df_raw[(df_raw['submitted_at'].dt.date >= date_range[0]) & (df_raw['submitted_at'].dt.date <= date_range[1])].copy() if len(date_range)==2 else df_raw.copy()
else:
    df_filtered = df_raw.copy(); date_range = [None, None]

DEPTS = ["All Departments","Flight Operations","Maintenance & Engineering","Ground Operations","Administration & Finance","Corporate Safety"]
CATS  = ["All Categories","Flight Crew (Pilot/Co-pilot)","Licensed Engineer / Technician","Ground Staff / Handling","Manager / Head of Department","Flight Dispatcher"]

sel_dept = st.sidebar.selectbox("Department", DEPTS)
if sel_dept != "All Departments": df_filtered = df_filtered[df_filtered['department'] == sel_dept]
sel_cat = st.sidebar.selectbox("Employee Category", CATS)
if sel_cat != "All Categories": df_filtered = df_filtered[df_filtered['employee_category'] == sel_cat]
sel_lang = st.sidebar.selectbox("Survey Language", ["All","en (English)","ne (Nepali)"])
if sel_lang.startswith("en") and 'language_used' in df_filtered.columns: df_filtered = df_filtered[df_filtered['language_used']=='en']
elif sel_lang.startswith("ne") and 'language_used' in df_filtered.columns: df_filtered = df_filtered[df_filtered['language_used']=='ne']
sel_pillar = st.sidebar.selectbox("Pillar Detail", ["All Pillars"]+list(SMS_PILLARS.keys()))

st.sidebar.markdown("---")
fc, tc = len(df_filtered), len(df_raw)
st.sidebar.info(f"📊 **{fc}** of **{tc}** responses")
st.sidebar.caption(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
if st.sidebar.button("🔄 Refresh"): st.cache_data.clear(); st.rerun()
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sign Out"): logout()

# HEADER
st.markdown(f'<div class="main-header"><div><h1>✈️ SMS Safety Culture Dashboard</h1><p>ICAO Annex 19 aligned · Real-time monitoring · v2.0</p></div><div class="airline-tag">{airline_name}</div></div>', unsafe_allow_html=True)

if df_raw.empty:
    st.info("📭 No survey responses yet. Share your survey link with employees.")
    st.code(f"https://survey.thesafetylayer.xyz/{airline.get('slug','')}")
    st.stop()

# KPIs
st.header("📊 Key Performance Indicators")
num_cols = [c for c in SCORE_COLS if c in df_filtered.columns]
overall  = df_filtered[num_cols].mean().mean() if num_cols and not df_filtered.empty else 0
aware_pct = (df_filtered['q1_aware'].sum()/len(df_filtered)*100) if 'q1_aware' in df_filtered.columns and not df_filtered.empty else 0
oc = "good" if overall>=3.5 else "fair" if overall>=2.5 else "poor"
ac = "good" if aware_pct>=80 else "fair" if aware_pct>=60 else "poor"
_, c2, c3, _ = st.columns([1,2,2,1])
with c2: st.markdown(f'<div class="metric-card"><div class="metric-title">🎯 OVERALL SMS SCORE</div><div class="metric-value {oc}">{overall:.1f}</div><div class="metric-sub">out of 5.0 · threshold ≥ 3.5</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="metric-card"><div class="metric-title">📢 POLICY AWARENESS</div><div class="metric-value {ac}">{aware_pct:.0f}%</div><div class="metric-sub">Employees aware of Safety Policy</div></div>', unsafe_allow_html=True)
st.markdown("---")

# PILLARS
st.subheader("🏛️ SMS Pillar Performance (ICAO Annex 19)")
p_scores = {pn: round(df_filtered[[c for c in pi['cols'] if c in df_filtered.columns]].mean().mean(),2) for pn,pi in SMS_PILLARS.items() if not df_filtered.empty}
p_df = pd.DataFrame(list(p_scores.items()), columns=['Pillar','Score'])
fig_p = px.bar(p_df, x='Pillar', y='Score', color='Score', color_continuous_scale=['#e74c3c','#f0a500','#27ae60'], range_y=[0,5.5], text='Score', title=f'Pillar Performance — {airline_name}')
fig_p.update_traces(texttemplate='%{text:.2f}', textposition='outside')
fig_p.add_hline(y=3.5, line_dash="dash", line_color="#e74c3c", line_width=2, annotation_text="Acceptable Threshold (3.5)", annotation_position="top right", annotation_font_color="#e74c3c")
fig_p.update_layout(height=460, showlegend=False, coloraxis_showscale=False)
st.plotly_chart(fig_p, use_container_width=True)
try:
    st.download_button("⬇️ Download Pillar Chart", data=fig_p.to_image(format="png",width=1400,height=500,scale=2), file_name=f"{airline.get('slug','sms')}_pillars.png", mime="image/png")
except: pass
st.markdown("---")

# QUESTIONS
st.subheader("🔍 Detailed Question Analysis")
all_q = [{"Pillar":pn,"Column":col,"Question":QUESTION_NAMES.get(col,col),"Score":round(df_filtered[col].dropna().mean() if col in df_filtered.columns and not df_filtered.empty else 0,2)} for pn,pi in SMS_PILLARS.items() for col in pi['cols']]
dq = [q for q in all_q if q["Pillar"]==sel_pillar] if sel_pillar!="All Pillars" else all_q
if dq:
    qdf = pd.DataFrame(dq).sort_values('Score')
    fig_q = px.bar(qdf, y='Question', x='Score', color='Score', color_continuous_scale=['#e74c3c','#f0a500','#27ae60'], range_x=[0,5.5], orientation='h', text='Score', title=f'Question Scores — {sel_pillar}')
    fig_q.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    fig_q.add_vline(x=3.5, line_dash="dash", line_color="#e74c3c", line_width=2)
    fig_q.update_layout(height=max(450,len(qdf)*42), coloraxis_showscale=False)
    st.plotly_chart(fig_q, use_container_width=True)
    try:
        st.download_button("⬇️ Download Question Chart", data=fig_q.to_image(format="png",width=1400,height=max(500,len(qdf)*42),scale=2), file_name=f"{airline.get('slug','sms')}_questions.png", mime="image/png")
    except: pass
st.markdown("---")

# PERCEPTION GAP
st.subheader("👥 Management vs. Frontline Perception Gap")
st.caption("Gaps ≥ 0.5 are a key safety culture risk indicator (ICAO Doc 9859).")
if 'employee_category' in df_filtered.columns and not df_filtered.empty:
    dm = df_filtered[df_filtered['employee_category']=='Manager / Head of Department']
    df2= df_filtered[df_filtered['employee_category'].isin(['Flight Crew (Pilot/Co-pilot)','Licensed Engineer / Technician','Ground Staff / Handling','Flight Dispatcher'])]
    if not dm.empty and not df2.empty:
        gr=[]
        for pn,pi in SMS_PILLARS.items():
            cs=[c for c in pi['cols'] if c in df_filtered.columns]; sh=pn.split(":")[0].strip()
            gr.append({"Pillar":sh,"Management":round(dm[cs].mean().mean(),2),"Frontline":round(df2[cs].mean().mean(),2),"Gap":round(abs(dm[cs].mean().mean()-df2[cs].mean().mean()),2)})
        gdf=pd.DataFrame(gr)
        fig_g=go.Figure()
        fig_g.add_trace(go.Bar(name='Management',x=gdf['Pillar'],y=gdf['Management'],marker_color='#2d7dd2',text=gdf['Management'],texttemplate='%{text:.2f}',textposition='outside'))
        fig_g.add_trace(go.Bar(name='Frontline', x=gdf['Pillar'],y=gdf['Frontline'], marker_color='#f0a500',text=gdf['Frontline'], texttemplate='%{text:.2f}',textposition='outside'))
        fig_g.add_hline(y=3.5,line_dash="dash",line_color="#e74c3c",line_width=2,annotation_text="Threshold (3.5)")
        fig_g.update_layout(barmode='group',yaxis_range=[0,5.5],height=440,title='Management vs. Frontline Perception',legend=dict(orientation='h',yanchor='bottom',y=1.02))
        st.plotly_chart(fig_g,use_container_width=True)
        lg=gdf[gdf['Gap']>=0.5]
        if not lg.empty: st.warning("⚠️ Significant gaps in: "+", ".join(lg['Pillar'])+" — Investigate and communicate.")
        else: st.success("✅ No significant perception gaps detected.")
        try:
            st.download_button("⬇️ Download Gap Chart", data=fig_g.to_image(format="png",width=1400,height=480,scale=2), file_name=f"{airline.get('slug','sms')}_gap.png", mime="image/png")
        except: pass
    else: st.info("Insufficient data for both groups in current filter.")
st.markdown("---")

# PRIORITY ACTIONS
st.subheader("🚨 Priority Actions")
low_q=[( q['Question'],q['Score']) for q in all_q if 0<q['Score']<2.5]
med_q=[(q['Question'],q['Score']) for q in all_q if 2.5<=q['Score']<3.5]
c1,c2=st.columns(2)
with c1:
    if low_q: st.error("**⚠️ CRITICAL (< 2.5)**"); [st.write(f"- **{q}**: {s:.2f}/5.0") for q,s in sorted(low_q,key=lambda x:x[1])]
    else: st.success("✅ No critical issues")
with c2:
    if med_q: st.warning("**📌 Needs Attention (2.5–3.5)**"); [st.write(f"- **{q}**: {s:.2f}/5.0") for q,s in sorted(med_q,key=lambda x:x[1])]
    else: st.info("No medium-priority issues.")
st.markdown("---")

# DEPARTMENT BREAKDOWN
st.subheader("🏢 Score by Department")
if 'department' in df_filtered.columns and not df_filtered.empty:
    dr=[{"Department":d,"Score":round(df_filtered[df_filtered['department']==d][[c for c in SCORE_COLS if c in df_filtered.columns]].mean().mean(),2),"Responses":len(df_filtered[df_filtered['department']==d])} for d in df_filtered['department'].dropna().unique()]
    ddf=pd.DataFrame(dr).sort_values('Score')
    fig_d=px.bar(ddf,y='Department',x='Score',orientation='h',color='Score',color_continuous_scale=['#e74c3c','#f0a500','#27ae60'],range_x=[0,5.5],text='Score',hover_data=['Responses'],title='Score by Department')
    fig_d.update_traces(texttemplate='%{text:.2f}',textposition='outside')
    fig_d.add_vline(x=3.5,line_dash="dash",line_color="#e74c3c",line_width=2)
    fig_d.update_layout(height=360,coloraxis_showscale=False)
    st.plotly_chart(fig_d,use_container_width=True)
    try:
        st.download_button("⬇️ Download Department Chart", data=fig_d.to_image(format="png",width=1400,height=400,scale=2), file_name=f"{airline.get('slug','sms')}_depts.png", mime="image/png")
    except: pass
    st.markdown("---")

# TREND
if 'submitted_at' in df_filtered.columns and len(df_filtered)>=3:
    st.subheader("📈 Score Trend Over Time")
    df_filtered['Date']=df_filtered['submitted_at'].dt.date
    tr=df_filtered.groupby('Date')[num_cols].mean().mean(axis=1).reset_index(); tr.columns=['Date','Average Score']
    fig_t=px.line(tr,x='Date',y='Average Score',markers=True,title='Overall SMS Score Trend')
    fig_t.add_hline(y=3.5,line_dash="dash",line_color="#e74c3c",line_width=2,annotation_text="Threshold (3.5)",annotation_position="top right")
    fig_t.update_layout(yaxis_range=[0,5],height=380)
    st.plotly_chart(fig_t,use_container_width=True)
    try:
        st.download_button("⬇️ Download Trend Chart", data=fig_t.to_image(format="png",width=1400,height=420,scale=2), file_name=f"{airline.get('slug','sms')}_trend.png", mime="image/png")
    except: pass
    st.markdown("---")

# FEEDBACK
if 'q24_comments' in df_filtered.columns:
    fb=df_filtered[df_filtered['q24_comments'].notna()&(df_filtered['q24_comments'].str.strip()!='')]
    if not fb.empty:
        st.subheader("💬 Employee Feedback")
        st.info(f"📝 **{len(fb)}** comments ({len(fb)/len(df_filtered)*100:.0f}% of respondents)")
        if 'submitted_at' in fb.columns: fb=fb.sort_values('submitted_at',ascending=False)
        for _,row in fb.head(10).iterrows():
            d=row['submitted_at'].strftime('%Y-%m-%d') if pd.notna(row.get('submitted_at')) else 'N/A'
            with st.expander(f"📝 {row.get('department','Unknown')} · {row.get('language_used','en').upper()} · {d}"):
                st.write(row['q24_comments'])

# SURVEY LINK
st.markdown("---")
st.subheader("🔗 Your Survey Link")
st.code(f"https://survey.thesafetylayer.xyz/{airline.get('slug','')}")
st.caption("Share this with your employees. It loads your airline branding automatically.")

# FOOTER
st.markdown(f'<div class="site-footer">📊 {airline_name} · {fc} of {tc} responses · {datetime.now().strftime("%Y-%m-%d %H:%M")} · <a href="https://thesafetylayer.xyz">The Safety Layer</a> · A project by <a href="https://gsacharya.com">Ghanshyam Acharya</a></div>', unsafe_allow_html=True)
