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
    
    # Standardize SN formatting to ensure matches
    for df in [df_staff, df_events]:
        df['SN'] = df['SN'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    # Ensure Duration is numeric for calculations
    if 'Duration' in df_events.columns:
        df_events['Duration'] = pd.to_numeric(df_events['Duration'], errors='coerce').fillna(0)

    # Logic for Role Totals
    def categorize_staff(badge):
        badge_str = str(badge).strip()
        if badge_str in ["Assist.Technician", "Driver"]:
            return "Assist.Technician"
        elif badge_str in ["Master in Fireworks", "Pro in Fireworks", "Team Leader"]:
            return "Team Leader"
        return "Unassigned"

    df_staff['Category'] = df_staff['Leader Badge'].apply(categorize_staff)
    return df_staff, df_events

# --- SECURITY ---
if "auth" not in st.session_state:
    st.title("🔒 Admin Login")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if pwd == "Admin@2026":
            st.session_state.auth = True
            st.rerun()
    st.stop()

df_staff, df_events = load_data()

# --- TABS NAVIGATION ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard", "👤 Staff Details", "➕ Add Data", "🗓️ Event Logs", "🏆 Leaderboard"
])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.title("📊 System Analytics")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Registered", len(df_staff[df_staff['SN'] != 'nan']))
    c2.metric("Team Leaders", len(df_staff[df_staff['Category'] == "Team Leader"]))
    c3.metric("Assist. Technicians", len(df_staff[df_staff['Category'] == "Assist.Technician"]))

    st.write("---")
    st.subheader("Events by Category")
    unique_events_df = df_events.drop_duplicates(subset=['Event Name', 'Event Location', 'Date'])
    
    col_chart, col_table = st.columns([1, 1])
    with col_table:
        cat_counts = unique_events_df['Master Group'].value_counts().reset_index()
        cat_counts.columns = ['Event Category', 'Count']
        st.dataframe(cat_counts, use_container_width=True, hide_index=True)
    with col_chart:
        st.bar_chart(unique_events_df['Master Group'].value_counts(), color="#0072B2")

# --- TAB 2: STAFF DETAILS (NEW PROFILE VIEW) ---
with tab2:
    st.title("👤 Staff Directory & Profiles")
    
    # Search Bar
    search_sn = st.text_input("🔍 Search Staff by Serial Number (SN)", placeholder="Enter SN here...")
    
    if search_sn:
        # Filter profile
        profile = df_staff[df_staff['SN'] == search_sn]
        
        if not profile.empty:
            p = profile.iloc[0]
            st.markdown(f"### Profile: {p['Name']}")
            
            # Personal Details Cards
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Rank", p['Rank'])
            m2.metric("Unit", p['Unit'])
            m3.metric("Contact", p['Contact'])
            m4.metric("Badge", p['Leader Badge'])
            
            # Engagement Metrics
            staff_events = df_events[df_events['SN'] == search_sn]
            total_events = len(staff_events)
            total_mins = staff_events['Duration'].sum() if 'Duration' in staff_events.columns else 0
            
            st.write("---")
            e1, e2 = st.columns(2)
            e1.metric("Total Events Attended", total_events)
            e2.metric("Total Duration (Mins)", f"{total_mins} mins")
            
            st.subheader("Event History")
            if total_events > 0:
                st.dataframe(staff_events[['Date', 'Event Name', 'Event Location', 'Duration']], 
                             use_container_width=True, hide_index=True)
            else:
                st.info("No event history found for this staff member.")
        else:
            st.error("No staff member found with that SN.")
    
    st.write("---")
    st.subheader("All Staff Directory")
    st.dataframe(df_staff[['SN', 'Rank', 'Name', 'Unit', 'Contact', 'Leader Badge']], 
                 use_container_width=True, hide_index=True)

# --- TAB 3: ADD DATA (FORMS) ---
with tab3:
    st.title("➕ Data Entry")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Add Staff Info")
        with st.form("staff_form"):
            s_sn = st.text_input("SN")
            s_name = st.text_input("Full Name")
            s_rank = st.text_input("Rank")
            s_unit = st.text_input("Unit")
            s_contact = st.text_input("Contact")
            s_badge = st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
            if st.form_submit_button("Submit"):
                st.link_button("Paste to Sheet", SHEET_EDIT_URL)

    with col_b:
        st.subheader("Log New Event")
        with st.form("event_form"):
            e_name = st.text_input("Event Name")
            e_loc = st.text_input("Event Location")
            e_date = st.date_input("Event Date", datetime.now())
            e_dur = st.number_input("Duration (Mins)", min_value=1)
            e_staff = st.multiselect("Select Staff", options=df_staff['Name'].tolist())
            if st.form_submit_button("Log Event"):
                st.link_button("Paste to Sheet", SHEET_EDIT_URL)

# --- TAB 4 & 5: LOGS & LEADERBOARD ---
with tab4:
    st.title("🗓️ Master Event Logs")
    st.dataframe(df_events, use_container_width=True, hide_index=True)

with tab5:
    st.title("🏆 Leaderboard")
    top_staff = df_events['SN'].value_counts().head(10).reset_index()
    top_staff.columns = ['SN', 'Engagements']
    top_staff = pd.merge(top_staff, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.dataframe(top_staff[['Name', 'Rank', 'Engagements']], use_container_width=True, hide_index=True)
