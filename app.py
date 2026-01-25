import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=10)
def load_data():
    # Load and clean data
    df_staff = pd.read_csv(DETAILS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df_events = pd.read_csv(EVENTS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    # Force SN to string to ensure matching works
    df_staff['SN'] = df_staff['SN'].astype(str)
    df_events['SN'] = df_events['SN'].astype(str)
    
    # Create Display Name
    df_staff['Display'] = df_staff['SN'] + " - " + df_staff['Name'] + " (" + df_staff['Rank'] + ")"
    return df_staff, df_events

# --- SECURITY ---
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

df_staff, df_events = load_data()

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "➕ Add Data", "👤 Staff Details", "🗓️ Event Logs", "🏆 Leaderboard"])

with tab1:
    st.title("📊 System Overview")
    
    # --- SECTION 1: STAFF REGISTERED (From Details Sheet) ---
    st.subheader("Staff Registered (Details Sheet)")
    s1, s2, s3 = st.columns(3)
    
    # STRICT COUNT: Column F (Leader Badge)
    total_reg = len(df_staff)
    # Count rows where Column F is exactly "Driver"
    drivers = len(df_staff[df_staff['Leader Badge'].str.contains('Driver', case=False, na=False)])
    # Team Leaders are everyone else in that sheet
    t_leaders = total_reg - drivers
    
    s1.metric("Total Registered Staff", total_reg)
    s2.metric("Team Leaders", t_leaders)
    s3.metric("Assist. Technicians (Drivers)", drivers)

    st.write("---")

    # --- SECTION 2: STAFF ENGAGED (From Event Details Sheet) ---
    st.subheader("Staff Engagements (Event Details Sheet)")
    e1, e2 = st.columns([1, 2])
    
    # COUNT EVERY ROW in Event Details as an engagement (1735)
    total_engagements = len(df_events)
    e1.metric("Total Staff Engaged", total_engagements, help="Counts every staff entry across all events")
    
    with e2:
        st.write("**Engagements by Master Group (Column G)**")
        # This counts how many rows (staff engagements) belong to each group
        group_counts = df_events['Master Group'].value_counts()
        if not group_counts.empty:
            st.bar_chart(group_counts)

    # Breakdown Table for Engagements
    st.write("#### Master Group Breakdown")
    if not group_counts.empty:
        summary_df = group_counts.reset_index()
        summary_df.columns = ['Master Group', 'Total Engagements']
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

# --- TAB 2: ADD DATA ---
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
            if st.form_submit_button("Generate Entry"):
                st.link_button("Go to Google Sheets", SHEET_EDIT_URL)
    with col_b:
        st.subheader("➕ New Event Entry")
        with st.form("event_form"):
            st.text_input("Event Name")
            st.number_input("Duration (Mins)", min_value=0)
            st.multiselect("Select Staff Members", options=df_staff['Display'].tolist())
            if st.form_submit_button("Log Event"):
                st.link_button("Go to Google Sheets", SHEET_EDIT_URL)

# --- TAB 3: STAFF HISTORY ---
with tab3:
    st.title("👤 Staff History")
    choice = st.selectbox("Select Staff", options=df_staff['Display'].tolist())
    sel_sn = choice.split(" - ")[0]
    
    # Filter event sheet for this specific SN
    personal_history = df_events[df_events['SN'] == sel_sn]
    st.write(f"### Activity for SN: {sel_sn}")
    st.metric("Total Events Attended", len(personal_history))
    st.dataframe(personal_history, use_container_width=True, hide_index=True)

# --- TAB 5: LEADERBOARD ---
with tab5:
    st.title("🏆 Leaderboard")
    # Top 5 by row count in Event Details
    top_staff = df_events['SN'].value_counts().head(5).reset_index()
    top_staff.columns = ['SN', 'Engagement Count']
    # Merge to get Names
    top_staff = pd.merge(top_staff, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.table(top_staff[['Name', 'Rank', 'Engagement Count']])
