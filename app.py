import streamlit as st
import pandas as pd

# --- 1. GLOBAL CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=2)
def load_data():
    df_staff = pd.read_csv(DETAILS_URL).rename(columns=lambda x: x.strip())
    df_events = pd.read_csv(EVENTS_URL).rename(columns=lambda x: x.strip())
    
    # Aggressive SN Cleaning
    clean_val = lambda x: str(x).split('.')[0].strip()
    df_staff['SN'] = df_staff['SN'].apply(clean_val)
    df_events['SN'] = df_events['SN'].apply(clean_val)
    
    # Flexible Column Discovery (Prevents KeyErrors)
    dur_col = next((c for c in df_events.columns if 'duration' in c.lower()), "Duration")
    loc_col = next((c for c in df_events.columns if 'location' in c.lower()), "Event Location")
    cat_col = next((c for c in df_events.columns if 'group' in c.lower() or 'category' in c.lower()), "Master Group")
    date_col = next((c for c in df_events.columns if 'date' in c.lower()), "Date")

    if dur_col in df_events.columns:
        df_events[dur_col] = pd.to_numeric(df_events[dur_col], errors='coerce').fillna(0)

    # Category Mapping for metrics
    def get_cat(b):
        b = str(b).strip()
        if b in ["Assist.Technician", "Driver"]: return "AT"
        if b in ["Master in Fireworks", "Pro in Fireworks", "Team Leader"]: return "TL"
        return "Other"
    df_staff['Category_Group'] = df_staff['Leader Badge'].apply(get_cat)

    return df_staff, df_events, dur_col, loc_col, cat_col, date_col

df_staff, df_events, dur_col, loc_col, cat_col, date_col = load_data()

# --- 2. THE UI ---
# We use standard tabs but give all widgets 'keys' to stop the shifting
t1, t2, t3, t4, t5 = st.tabs(["📊 Dashboard", "👤 Staff Details", "➕ Add Data", "🗓️ Event Logs", "🏆 Leaderboard"])

# --- TAB 1: DASHBOARD (CHART RESTORED) ---
with t1:
    st.title("📊 Strategic Overview")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Registered", len(df_staff))
    m2.metric("Team Leaders", len(df_staff[df_staff['Category_Group'] == "TL"]))
    m3.metric("Assist. Technicians", len(df_staff[df_staff['Category_Group'] == "AT"]))
    
    st.write("---")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Event Frequency Table")
        if cat_col in df_events.columns:
            summary = df_events.groupby(cat_col).size().reset_index(name='Total Events')
            st.dataframe(summary, use_container_width=True, hide_index=True)
    
    with c2:
        st.subheader("Visual Breakdown")
        if cat_col in df_events.columns:
            chart_data = df_events[cat_col].value_counts()
            st.bar_chart(chart_data, color="#0072B2")

# --- TAB 2: STAFF DETAILS ---
with t2:
    st.title("👤 Staff Profiles")
    # Unique Key prevents tab reset on search
    search_sn = st.text_input("🔍 Search SN", key="anchor_sn_search")
    
    if search_sn:
        p_match = df_staff[df_staff['SN'] == search_sn.strip()]
        if not p_match.empty:
            p = p_match.iloc[0]
            st.header(f"Profile: {p['Name']}")
            hist = df_events[df_events['SN'] == search_sn.strip()]
            st.metric("Total Duration", f"{int(hist[dur_col].sum())} Mins")
            st.dataframe(hist, use_container_width=True, hide_index=True)
        else:
            st.warning("SN not found.")

# --- TAB 4: EVENT LOGS ---
with t4:
    st.title("🗓️ Event Logs")
    # Unique Key prevents tab reset on search
    search_loc = st.text_input("🔍 Search Location", key="anchor_loc_search")
    
    filtered = df_events.copy()
    if search_loc:
        filtered = filtered[filtered[loc_col].str.contains(search_loc, case=False, na=False)]
    
    st.dataframe(filtered, use_container_width=True, hide_index=True)

# --- TAB 5: LEADERBOARD ---
with t5:
    st.title("🏆 Top 5 Performance")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔥 Top 5 Engagements")
        t_eng = df_events['SN'].value_counts().head(5).reset_index()
        t_eng.columns = ['SN', 'Events']
        res_eng = pd.merge(t_eng, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
        st.dataframe(res_eng[['SN', 'Rank', 'Name', 'Events']], use_container_width=True, hide_index=True)

    with col2:
        st.subheader("⏳ Top 5 Duration")
        t_dur = df_events.groupby('SN')[dur_col].sum().sort_values(ascending=False).head(5).reset_index()
        t_dur.columns = ['SN', 'Total Mins']
        res_dur = pd.merge(t_dur, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
        st.dataframe(res_dur[['SN', 'Rank', 'Name', 'Total Mins']], use_container_width=True, hide_index=True)
