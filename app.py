import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
# Your exact Google Sheet ID
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=10)
def load_data():
    # Load and clean data (removing extra spaces)
    df_staff = pd.read_csv(DETAILS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df_events = pd.read_csv(EVENTS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    # Ensure Serial Numbers (SN) are strings to prevent errors
    df_staff['SN'] = df_staff['SN'].astype(str)
    df_events['SN'] = df_events['SN'].astype(str)
    
    # Create a unique display name for dropdowns
    df_staff['Display'] = df_staff['SN'] + " - " + df_staff['Name'] + " (" + df_staff['Rank'] + ")"
    return df_staff, df_events

# --- 1. SECURITY LOGIN ---
if "auth" not in st.session_state:
    st.title("🔒 Staff Management Login")
    pwd = st.text_input("Enter Admin Password", type="password")
    if st.button("Login"):
        if pwd == "Admin@2026":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Invalid Password")
    st.stop()

# Load data after login success
df_staff, df_events = load_data()

# --- 2. TABS NAVIGATION ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard", "➕ Add Data", "👤 Staff Details", "🗓️ Event Logs", "🏆 Leaderboard"
])

# --- TAB 1: DASHBOARD (FIXED CATEGORIZATION) ---
with tab1:
    st.title("📊 System Overview")
    
    # Staff Metrics: Based on Column F (Leader Badge)
    st.subheader("Staff Distribution (Column F)")
    s1, s2, s3 = st.columns(3)
    
    total_staff = len(df_staff)
    # Rule: "Driver" = Assist.Technician, anything else = Team Leader
    assist_techs = len(df_staff[df_staff['Leader Badge'].str.lower() == "driver"])
    team_leaders = total_staff - assist_techs
    
    s1.metric("Total Registered", total_staff)
    s2.metric("Team Leaders", team_leaders)
    s3.metric("Assist. Technicians", assist_techs)

    st.write("---")

    # Event Metrics: Based on Column D (Name) and Column G (Master Group)
    st.subheader("Event Activity")
    e1, e2 = st.columns([1, 2])
    
    total_events = len(df_events['Event Name'].dropna())
    e1.metric("Total Events Logged", total_events)
    
    with e2:
        st.write("**Events by Master Group (Column G)**")
        event_group_counts = df_events['Master Group'].value_counts()
        if not event_group_counts.empty:
            st.bar_chart(event_group_counts)
        else:
            st.info("No data in Column G")

# --- TAB 2: ADD DATA (EXPANDED FORMS) ---
with tab2:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("➕ New Staff Info")
        with st.form("staff_form"):
            st.text_input("SN")
            st.text_input("Full Name")
            st.text_input("Rank")
            st.text_input("Unit")
            st.selectbox("Leader Badge", ["Team Leader", "Driver", "Staff"])
            if st.form_submit_button("Generate Staff Data"):
                st.link_button("Paste into Google Sheets", SHEET_EDIT_URL)

    with col_b:
        st.subheader("➕ New Event Entry")
        with st.form("event_form"):
            st.text_input("Event Name")
            st.text_input("Location")
            st.number_input("Event Duration (Mins)", min_value=0)
            st.multiselect("Select Staff Members", options=df_staff['Display'].tolist())
            if st.form_submit_button("Generate Event Data"):
                st.link_button("Paste into Google Sheets", SHEET_EDIT_URL)

# --- TAB 3: STAFF DETAILS (EVENT HISTORY) ---
with tab3:
    st.title("👤 Staff History Search")
    selected_choice = st.selectbox("Search Staff Member", options=df_staff['Display'].tolist())
    sel_sn = selected_choice.split(" - ")[0]
    
    # Show Profile
    p_info = df_staff[df_staff['SN'] == sel_sn].iloc[0]
    st.write(f"### Profile: {p_info['Name']}")
    st.write(f"**Rank:** {p_info['Rank']} | **Unit:** {p_info['Unit']} | **Badge:** {p_info['Leader Badge']}")
    
    # Show all events for THIS staff member
    st.write("#### Events Attended")
    personal_history = df_events[df_events['SN'] == sel_sn]
    st.dataframe(personal_history, use_container_width=True, hide_index=True)

# --- TAB 4: EVENT LOGS (MASTER LIST) ---
with tab4:
    st.title("🗓️ Master Event Logs")
    st.dataframe(df_events, use_container_width=True, hide_index=True)

# --- TAB 5: LEADERBOARD (TOP 5) ---
with tab5:
    st.title("🏆 Leaderboard")
    
    # Group by SN to find totals
    e_counts = df_events.groupby('SN').size().reset_index(name='Total Events')
    
    # Check if Duration column exists
    if 'Event Duration (Mins)' in df_events.columns:
        d_counts = df_events.groupby('SN')['Event Duration (Mins)'].sum().reset_index(name='Total Duration')
        leaders = pd.merge(e_counts, d_counts, on='SN')
    else:
        leaders = e_counts
        
    # Merge with staff names for the table
    leaders = pd.merge(leaders, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    
    l1, l2 = st.columns(2)
    with l1:
        st.subheader("🔥 Top 5 by Events")
        st.table(leaders.sort_values('Total Events', ascending=False).head(5)[['Name', 'Total Events']])
    with l2:
        st.subheader("⏳ Top 5 by Duration")
        if 'Total Duration' in leaders.columns:
            st.table(leaders.sort_values('Total Duration', ascending=False).head(5)[['Name', 'Total Duration']])
