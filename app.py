import streamlit as st
import pandas as pd

# --- 1. GLOBAL CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

# --- 2. THE TAB-SHIFTING CURE ---
# Using session_state + segmented_control/tabs object hybrid
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0

@st.cache_data(ttl=2)
def load_data():
    df_staff = pd.read_csv(DETAILS_URL).rename(columns=lambda x: x.strip())
    df_events = pd.read_csv(EVENTS_URL).rename(columns=lambda x: x.strip())
    
    clean_val = lambda x: str(x).split('.')[0].strip()
    df_staff['SN'] = df_staff['SN'].apply(clean_val)
    df_events['SN'] = df_events['SN'].apply(clean_val)
    
    dur_col = next((c for c in df_events.columns if 'duration' in c.lower()), "Duration")
    loc_col = next((c for c in df_events.columns if 'location' in c.lower()), "Event Location")
    
    if dur_col in df_events.columns:
        df_events[dur_col] = pd.to_numeric(df_events[dur_col], errors='coerce').fillna(0)

    return df_staff, df_events, dur_col, loc_col

df_staff, df_events, dur_col, loc_col = load_data()

# Use standard tabs but wrap them to maintain state
t1, t2, t3, t4, t5 = st.tabs(["📊 Dashboard", "👤 Staff Details", "➕ Add Data", "🗓️ Event Logs", "🏆 Leaderboard"])

# --- TAB 1: DASHBOARD ---
with t1:
    st.title("📊 Strategic Overview")
    # ... Dashboard Metrics ...

# --- TAB 2: STAFF DETAILS ---
with t2:
    st.title("👤 Staff Profiles")
    search_sn = st.text_input("🔍 Search SN", key="staff_search_unique")
    # ... Staff Profile Logic ...

# --- TAB 3: ADD DATA ---
with t3:
    st.title("➕ Data Management")
    st.link_button("Edit Google Sheet", SHEET_EDIT_URL)

# --- TAB 4: EVENT LOGS ---
with t4:
    st.title("🗓️ Event Logs")
    search_loc = st.text_input("🔍 Search Location", key="loc_search_unique")
    # ... Event Log Logic ...

# --- TAB 5: LEADERBOARD (UPDATED WITH SN) ---
with t5:
    st.title("🏆 Top 5 Performance Leaderboard")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔥 Top 5 by Engagements")
        # Top 5 by Count
        top_eng = df_events['SN'].value_counts().head(5).reset_index()
        top_eng.columns = ['SN', 'Events']
        # Merge to get Name and Rank
        res_eng = pd.merge(top_eng, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
        # Displaying SN first
        st.dataframe(res_eng[['SN', 'Rank', 'Name', 'Events']], use_container_width=True, hide_index=True)

    with col2:
        st.subheader("⏳ Top 5 by Total Duration")
        # Top 5 by Summed Duration
        top_dur = df_events.groupby('SN')[dur_col].sum().sort_values(ascending=False).head(5).reset_index()
        top_dur.columns = ['SN', 'Total Mins']
        # Merge to get Name and Rank
        res_dur = pd.merge(top_dur, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
        # Displaying SN first
        st.dataframe(res_dur[['SN', 'Rank', 'Name', 'Total Mins']], use_container_width=True, hide_index=True)

    st.balloons()
