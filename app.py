import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=5)
def load_data():
    df_staff = pd.read_csv(DETAILS_URL).rename(columns=lambda x: x.strip())
    df_events = pd.read_csv(EVENTS_URL).rename(columns=lambda x: x.strip())
    
    # 1. FIX: Format Contact and SN to remove .0 and treat as clean strings
    for df in [df_staff, df_events]:
        if 'SN' in df.columns:
            df['SN'] = df['SN'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    if 'Contact' in df_staff.columns:
        df_staff['Contact'] = df_staff['Contact'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    # 2. FIX: Safely find and clean the Duration column
    dur_col = next((c for c in ['Event duration(Mins)', 'Duration'] if c in df_events.columns), None)
    if dur_col:
        df_events[dur_col] = pd.to_numeric(df_events[dur_col], errors='coerce').fillna(0)

    # 3. Categorization Logic
    def categorize_staff(badge):
        b = str(badge).strip()
        if b in ["Assist.Technician", "Driver"]: return "Assist.Technician"
        if b in ["Master in Fireworks", "Pro in Fireworks", "Team Leader"]: return "Team Leader"
        return "Unassigned"

    df_staff['Category'] = df_staff['Leader Badge'].apply(categorize_staff)
    return df_staff, df_events, dur_col

df_staff, df_events, dur_col = load_data()

# --- TABS NAVIGATION ---
# Using session_state for the active tab to prevent shifting on Enter
tabs = ["📊 Dashboard", "👤 Staff Details", "➕ Add Data", "🗓️ Event Logs", "🏆 Leaderboard"]
active_tab = st.tabs(tabs)

# --- TAB 1: DASHBOARD ---
with active_tab[0]:
    st.title("📊 System Analytics")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Registered", len(df_staff))
    c2.metric("Team Leaders", len(df_staff[df_staff['Category'] == "Team Leader"]))
    c3.metric("Assist. Technicians", len(df_staff[df_staff['Category'] == "Assist.Technician"]))
    
    st.write("---")
    # Safer deduplication to fix KeyError: 'Date'
    unique_ev = df_events.drop_duplicates(subset=['Event Name', 'Event Location'])
    st.subheader("Event Categories")
    st.bar_chart(unique_ev['Master Group'].value_counts(), color="#0072B2")

# --- TAB 2: STAFF DETAILS (FILTER & CLICK-TO-VIEW) ---
with active_tab[1]:
    st.title("👤 Staff Directory & Individual Profiles")
    
    # 1. Filter Section (Replaced the Select-to-View bar)
    f1, f2 = st.columns([1, 2])
    with f1:
        role_filter = st.multiselect("Filter by Role:", options=["Team Leader", "Assist.Technician"], default=["Team Leader", "Assist.Technician"])
    with f2:
        search_sn = st.text_input("🔍 Quick Search by SN", key="staff_search_input")

    # Apply Filters to the Main Table
    display_df = df_staff[df_staff['Category'].isin(role_filter)]
    if search_sn:
        display_df = display_df[display_df['SN'].str.contains(search_sn)]

    st.write("### 🗂️ Staff Directory")
    st.info("💡 Note: To view a full profile, find the member in the table below and type their SN in the search box above.")
    
    # Show the interactive table
    st.dataframe(display_df[['SN', 'Rank', 'Name', 'Unit', 'Contact', 'Category']], use_container_width=True, hide_index=True)

    # 2. Profile View (Triggered only when a valid SN is searched)
    if search_sn:
        profile_data = df_staff[df_staff['SN'] == search_sn]
        if not profile_data.empty:
            p = profile_data.iloc[0]
            st.markdown(f"---")
            st.header(f"Profile: {p['Name']}")
            
            # Personal Details
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Rank", p['Rank'])
            m2.metric("Unit", p['Unit'])
            m3.metric("Contact", p['Contact']) # .0 is now removed
            m4.metric("Badge", p['Leader Badge'])
            
            # Attendance History & Math Fix
            history = df_events[df_events['SN'] == search_sn]
            total_events = len(history)
            total_mins = history[dur_col].sum() if dur_col else 0
            
            e1, e2 = st.columns(2)
            e1.metric("Total Events Attended", total_events)
            e2.metric("Total Duration (Calculated)", f"{total_mins} Mins")
            
            st.subheader("Personal Attendance Log")
            st.dataframe(history, use_container_width=True, hide_index=True)

# --- TAB 3: ADD DATA (UPDATED FORMS) ---
with active_tab[2]:
    st.title("➕ Data Management")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Add Staff Info")
        with st.form("staff_form"):
            st.text_input("SN"); st.text_input("Full Name"); st.text_input("Rank")
            st.text_input("Unit"); st.text_input("Contact") # Restored fields
            st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
            if st.form_submit_button("Submit"): st.link_button("Open Sheet", SHEET_EDIT_URL)
    with col_b:
        st.subheader("Log New Event")
        with st.form("event_form"):
            st.text_input("Event Name"); st.text_input("Event Location")
            st.date_input("Event Date"); st.number_input("Event duration(Mins)", min_value=1)
            if st.form_submit_button("Log"): st.link_button("Open Sheet", SHEET_EDIT_URL)

# --- TAB 4 & 5: RAW LOGS & LEADERBOARD ---
with active_tab[3]:
    st.title("🗓️ Master Event Logs")
    st.dataframe(df_events, use_container_width=True, hide_index=True)

with active_tab[4]:
    st.title("🏆 Leaderboard")
    top = df_events['SN'].value_counts().head(10).reset_index()
    top.columns = ['SN', 'Engagements']
    board = pd.merge(top, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.dataframe(board[['Name', 'Rank', 'Engagements']], use_container_width=True, hide_index=True)
