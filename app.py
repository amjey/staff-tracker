import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=10)
def load_data():
    df_staff = pd.read_csv(DETAILS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df_events = pd.read_csv(EVENTS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    # Categorization Logic: "Driver" -> Assist.Technician, else Team Leader
    df_staff['Category'] = df_staff['Leader Badge'].apply(
        lambda x: "Assist.Technician" if str(x).lower() == "driver" else "Team Leader"
    )
    
    df_staff['SN'] = df_staff['SN'].astype(str)
    df_events['SN'] = df_events['SN'].astype(str)
    return df_staff, df_events

# --- SECURITY ---
if "auth" not in st.session_state:
    st.title("🔒 Staff Management Login")
    if st.text_input("Password", type="password") == "Admin@2026":
        if st.button("Login"):
            st.session_state.auth = True
            st.rerun()
    st.stop()

df_staff, df_events = load_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("🔍 Global Filters")
search_sn = st.sidebar.text_input("Search by SN")
category_filter = st.sidebar.multiselect("Category", options=df_staff['Category'].unique())

# Filter Logic
filtered_staff = df_staff
if search_sn:
    filtered_staff = filtered_staff[filtered_staff['SN'].contains(search_sn)]
if category_filter:
    filtered_staff = filtered_staff[filtered_staff['Category'].isin(category_filter)]

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard", "➕ Add Data", "👤 Staff Details", "🗓️ Event Logs", "🏆 Leaderboard"
])

with tab1:
    st.title("📊 Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Staff", len(df_staff))
    c2.metric("Total Events", len(df_events))
    c3.metric("Assist. Techs", len(df_staff[df_staff['Category'] == "Assist.Technician"]))

with tab2:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("➕ Add New Staff")
        with st.form("staff_form"):
            new_sn = st.text_input("SN")
            new_name = st.text_input("Full Name")
            new_badge = st.selectbox("Role", ["Team Leader", "Driver", "Staff"])
            if st.form_submit_button("Generate Entry"):
                st.info(f"Copy this to Google Sheets: {new_sn}, {new_name}, {new_badge}")
                st.link_button("Go to Google Sheets", SHEET_EDIT_URL)

    with col_b:
        st.subheader("➕ Add New Event")
        with st.form("event_form"):
            event_name = st.text_input("Event Name")
            # Multiple Staff Selection
            selected_staff = st.multiselect("Select Staff (SN)", options=df_staff['SN'].tolist())
            event_date = st.date_input("Event Date")
            if st.form_submit_button("Log Event"):
                st.success(f"Log {event_name} for SNs: {', '.join(selected_staff)}")
                st.link_button("Open Event Details Tab", SHEET_EDIT_URL)

with tab3:
    st.title("👤 Staff Insight")
    selected_staff_sn = st.selectbox("Select Staff to view History", options=df_staff['SN'].unique())
    
    staff_info = df_staff[df_staff['SN'] == selected_staff_sn].iloc[0]
    st.write(f"### Profile: {staff_info['Name']} ({staff_info['Category']})")
    
    # Show individual attendance
    attendance = df_events[df_events['SN'] == selected_staff_sn]
    st.write("#### Attended Events")
    st.dataframe(attendance, use_container_width=True, hide_index=True)

with tab4:
    st.title("🗓️ Master Logs")
    st.dataframe(df_events, use_container_width=True)

with tab5:
    st.title("🏆 Leaderboard")
    
    # Calculate Leaderboard
    leader_stats = df_events.groupby('SN').size().reset_index(name='Total Events')
    # Assuming "Event Duration (Mins)" exists in your sheet
    if 'Event Duration (Mins)' in df_events.columns:
        duration_stats = df_events.groupby('SN')['Event Duration (Mins)'].sum().reset_index(name='Total Duration')
        leader_stats = pd.merge(leader_stats, duration_stats, on='SN')
    
    leader_stats = pd.merge(leader_stats, df_staff[['SN', 'Name']], on='SN', how='left')
    
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.subheader("🔥 Top 5 by Events")
        st.table(leader_stats.sort_values(by='Total Events', ascending=False).head(5)[['Name', 'Total Events']])
        
    with col_l2:
        st.subheader("⏳ Top 5 by Duration")
        if 'Total Duration' in leader_stats.columns:
            st.table(leader_stats.sort_values(by='Total Duration', ascending=False).head(5)[['Name', 'Total Duration']])
