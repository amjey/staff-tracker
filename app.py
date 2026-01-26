import streamlit as st
import pandas as pd

# --- 1. GLOBAL CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

# --- 2. TAB LOCKING LOGIC (Fixes Shifting) ---
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "📊 Dashboard"

# Custom CSS to make the radio buttons look like a menu
st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] { background-color: #0e1117; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Navigation Menu
tabs = ["📊 Dashboard", "👤 Staff Details", "➕ Add Data", "🗓️ Event Logs", "🏆 Leaderboard"]
st.session_state.active_tab = st.segmented_control("Navigation", tabs, default=st.session_state.active_tab)

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

# --- 3. TAB CONTENT LOGIC ---

if st.session_state.active_tab == "📊 Dashboard":
    st.title("📊 Dashboard")
    # ... (Your existing metrics code)

elif st.session_state.active_tab == "👤 Staff Details":
    st.title("👤 Staff Details")
    search_sn = st.text_input("🔍 Search SN", key="staff_search")
    # ... (Your existing profile code)

elif st.session_state.active_tab == "➕ Add Data":
    st.title("➕ Add Data")
    st.link_button("Edit Google Sheet", SHEET_EDIT_URL)

elif st.session_state.active_tab == "🗓️ Event Logs":
    st.title("🗓️ Event Logs")
    search_loc = st.text_input("🔍 Search Location", key="loc_search")
    # ... (Your existing location search code)

elif st.session_state.active_tab == "🏆 Leaderboard":
    st.title("🏆 Top 5 Performance Leaderboard")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔥 Top 5 by Engagements")
        # Count events per SN
        top_eng = df_events['SN'].value_counts().head(5).reset_index()
        top_eng.columns = ['SN', 'Events']
        # Merge with staff info
        res_eng = pd.merge(top_eng, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
        st.dataframe(res_eng[['Rank', 'Name', 'Events']], use_container_width=True, hide_index=True)

    with col2:
        st.subheader("⏳ Top 5 by Total Duration")
        # Sum duration per SN
        top_dur = df_events.groupby('SN')[dur_col].sum().sort_values(ascending=False).head(5).reset_index()
        top_dur.columns = ['SN', 'Total Mins']
        # Merge with staff info
        res_dur = pd.merge(top_dur, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
        st.dataframe(res_dur[['Rank', 'Name', 'Total Mins']], use_container_width=True, hide_index=True)

    st.balloons()
