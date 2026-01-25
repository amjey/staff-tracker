import streamlit as st
import pandas as pd

# --- CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=2)
def load_data():
    # Load data and strip column names of any hidden spaces
    df_staff = pd.read_csv(DETAILS_URL).rename(columns=lambda x: x.strip())
    df_events = pd.read_csv(EVENTS_URL).rename(columns=lambda x: x.strip())
    
    # 1. FORCE SN MATCHING (The Bridge)
    # We turn SN into a clean integer string (removes .0 and spaces)
    def clean_sn(val):
        return str(val).split('.')[0].strip()

    df_staff['SN'] = df_staff['SN'].apply(clean_sn)
    df_events['SN'] = df_events['SN'].apply(clean_sn)
    
    # 2. CLEAN CONTACT
    if 'Contact' in df_staff.columns:
        df_staff['Contact'] = df_staff['Contact'].apply(clean_sn)
    
    # 3. SEARCH & RESCUE DURATION COLUMN
    # We look for ANY column that contains the word "duration"
    dur_col = None
    for col in df_events.columns:
        if 'duration' in col.lower():
            dur_col = col
            df_events[dur_col] = pd.to_numeric(df_events[dur_col], errors='coerce').fillna(0)
            break

    # 4. CATEGORIZATION logic
    def categorize_staff(badge):
        b = str(badge).strip()
        if b in ["Assist.Technician", "Driver"]: return "Assist.Technician"
        if b in ["Master in Fireworks", "Pro in Fireworks", "Team Leader"]: return "Team Leader"
        return "Unassigned"

    df_staff['Category'] = df_staff['Leader Badge'].apply(categorize_staff)
    return df_staff, df_events, dur_col

df_staff, df_events, dur_col = load_data()

# --- STABLE TABS ---
# To stop shifting, we define tabs and don't use session_state for navigation
t1, t2, t3, t4, t5 = st.tabs(["📊 Dashboard", "👤 Staff Details", "➕ Add Data", "🗓️ Event Logs", "🏆 Leaderboard"])

with t1:
    st.title("📊 Strategic Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Registered", len(df_staff))
    c2.metric("Team Leaders", len(df_staff[df_staff['Category'] == "Team Leader"]))
    c3.metric("Assist. Technicians", len(df_staff[df_staff['Category'] == "Assist.Technician"]))

with t2:
    st.title("👤 Staff Profiles")
    
    # Filter & Search
    f1, f2 = st.columns([1, 2])
    with f1:
        # User requested categories
        all_badges = ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"]
        role_filter = st.multiselect("Filter Table:", options=all_badges, default=all_badges)
    with f2:
        # UNIQUE KEY stops tab shifting
        search_sn = st.text_input("🔍 Enter SN for Profile", key="unique_staff_search")

    # Directory
    display_df = df_staff[df_staff['Leader Badge'].isin(role_filter)]
    st.dataframe(display_df[['SN', 'Rank', 'Name', 'Unit', 'Contact', 'Leader Badge']], 
                 use_container_width=True, hide_index=True)

    # PROFILE VIEW
    if search_sn:
        clean_input = str(search_sn).strip()
        p_match = df_staff[df_staff['SN'] == clean_input]
        
        if not p_match.empty:
            p = p_match.iloc[0]
            st.markdown("---")
            st.header(f"Profile: {p['Name']}")
            
            # Personal Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Rank", p['Rank'])
            m2.metric("Unit", p['Unit'])
            m3.metric("Contact", p['Contact'])
            m4.metric("Badge", p['Leader Badge'])
            
            # --- THE DURATION CALCULATION ---
            # We filter the event sheet for this specific SN
            personal_events = df_events[df_events['SN'] == clean_input]
            
            total_count = len(personal_events)
            # We sum the duration column we found earlier
            total_mins = personal_events[dur_col].sum() if dur_col else 0
            
            st.write("---")
            e1, e2 = st.columns(2)
            e1.metric("Total Events Attended", total_count)
            e2.metric("Total Duration", f"{int(total_mins)} Mins")
            
            st.subheader("Attendance Log")
            st.dataframe(personal_events, use_container_width=True, hide_index=True)
        else:
            st.error(f"SN {search_sn} not found in Staff Registry.")

with t3:
    st.title("➕ Add Data")
    st.info("Form fields (Unit, Contact, Date, Duration) are active. Check Google Sheets to save.")
    st.link_button("Open Google Sheets", SHEET_EDIT_URL)

with t4:
    st.title("🗓️ Event Logs")
    st.dataframe(df_events, use_container_width=True, hide_index=True)

with t5:
    st.title("🏆 Leaderboard")
    top = df_events['SN'].value_counts().head(10).reset_index()
    top.columns = ['SN', 'Engagements']
    board = pd.merge(top, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.dataframe(board[['Name', 'Rank', 'Engagements']], use_container_width=True, hide_index=True)
