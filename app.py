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
    # Load and clean staff data
    df_staff = pd.read_csv(DETAILS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df_events = pd.read_csv(EVENTS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    # --- CATEGORIZATION LOGIC ---
    # Logic: "Driver" in Leader Badge -> Assist.Technician, else Team Leader
    df_staff['Category'] = df_staff['Leader Badge'].apply(
        lambda x: "Assist.Technician" if str(x).lower() == "driver" else "Team Leader"
    )
    
    # Ensure SN is string for matching and fix search logic
    df_staff['SN'] = df_staff['SN'].astype(str)
    df_events['SN'] = df_events['SN'].astype(str)
    
    # Create Display Name for selectors (SN - Name - Rank)
    df_staff['Display'] = df_staff['SN'] + " - " + df_staff['Name'] + " (" + df_staff['Rank'] + ")"
    return df_staff, df_events

# --- SECURITY ---
if "auth" not in st.session_state:
    st.title("🔒 Staff Management Login")
    if st.text_input("Password", type="password") == "Admin@2026":
        if st.button("Login"):
            st.session_state.auth = True
            st.rerun()
    st.stop()

# Load data after login
df_staff, df_events = load_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("🔍 Global Search")
search_sn = st.sidebar.text_input("Search by SN")
category_filter = st.sidebar.multiselect("Filter by Category", options=["Team Leader", "Assist.Technician"])

# Apply Global Filters to the staff list
filtered_staff = df_staff
if search_sn:
    # Uses .str.contains to prevent the AttributeError from image_f9a8f5
    filtered_staff = filtered_staff[filtered_staff['SN'].str.contains(search_sn, na=False)]
if category_filter:
    filtered_staff = filtered_staff[filtered_staff['Category'].isin(category_filter)]

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "➕ Add Data", "👤 Staff Details", "🗓️ Event Logs", "🏆 Leaderboard"])

with tab1:
    st.title("📊 Dashboard Overview")
    
    # 1. Staff Statistics
    st.subheader("Staff by Categories")
    c1, c2, c3 = st.columns(3)
    
    # Calculate totals
    total_staff = len(df_staff)
    assist_techs = len(df_staff[df_staff['Category'] == "Assist.Technician"])
    team_leaders = len(df_staff[df_staff['Category'] == "Team Leader"])
    
    c1.metric("Total Registered", total_staff)
    c2.metric("Team Leaders", team_leaders)
    c3.metric("Assist. Technicians (Drivers)", assist_techs)

    # 2. Event Statistics by Category
    st.write("---")
    st.subheader("Events by Category")
    
    # Link events to staff categories
    event_summary = pd.merge(df_events, df_staff[['SN', 'Category']], on='SN', how='left')
    category_event_counts = event_summary['Category'].value_counts()
    
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.write("**Event Distribution Count**")
        st.bar_chart(category_event_counts)
    with chart_col2:
        st.write("**Category Breakdown**")
        st.dataframe(category_event_counts, use_container_width=True)

with tab2: # UPDATED FORMS
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("➕ Add New Staff")
        with st.form("staff_form"):
            n_sn = st.text_input("SN")
            n_name = st.text_input("Full Name")
            n_rank = st.text_input("Rank")
            n_unit = st.text_input("Unit")
            n_badge = st.selectbox("Leader Badge", ["Team Leader", "Driver", "Staff"])
            if st.form_submit_button("Generate Staff Entry"):
                st.info(f"Add to Sheet: {n_sn}, {n_name}, {n_rank}, {n_unit}, {n_badge}")
                st.link_button("Go to Google Sheets", SHEET_EDIT_URL)

    with col_b:
        st.subheader("➕ Add New Event")
        with st.form("event_form"):
            e_name = st.text_input("Event Name")
            e_loc = st.text_input("Location")
            e_dur = st.number_input("Event Duration (Mins)", min_value=0)
            e_staff = st.multiselect("Select Staff (SN - Name - Rank)", options=df_staff['Display'].tolist())
            if st.form_submit_button("Generate Event Log"):
                st.success(f"Log {e_name} ({e_dur}m) for {len(e_staff)} staff.")
                st.link_button("Go to Google Sheets", SHEET_EDIT_URL)

with tab3: # STAFF HISTORY
    st.title("👤 Staff Insight")
    choice = st.selectbox("Search Staff Member", options=df_staff['Display'].tolist())
    sel_sn = choice.split(" - ")[0]
    
    s_info = df_staff[df_staff['SN'] == sel_sn].iloc[0]
    st.write(f"### Profile: {s_info['Name']}")
    st.write(f"**Category:** {s_info['Category']} | **Rank:** {s_info['Rank']} | **Unit:** {s_info['Unit']}")
    
    st.write("#### All Attended Events")
    history = df_events[df_events['SN'] == sel_sn]
    st.dataframe(history, use_container_width=True, hide_index=True)

with tab5: # UPGRADED LEADERBOARD
    st.title("🏆 Leaderboard (Top 5)")
    
    # Calculate Leaderboard using Events and Duration
    e_stats = df_events.groupby('SN').size().reset_index(name='Events')
    
    # Use 'Event Duration (Mins)' matching your sheet header
    if 'Event Duration (Mins)' in df_events.columns:
        dur_stats = df_events.groupby('SN')['Event Duration (Mins)'].sum().reset_index(name='Total Duration')
        leader_df = pd.merge(e_stats, dur_stats, on='SN')
    else:
        leader_df = e_stats
        
    leader_df = pd.merge(leader_df, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    
    l1, l2 = st.columns(2)
    with l1:
        st.subheader("🔥 Top 5 by Events")
        st.table(leader_df.sort_values('Events', ascending=False).head(5)[['Name', 'Rank', 'Events']])
    with l2:
        st.subheader("⏳ Top 5 by Duration")
        if 'Total Duration' in leader_df.columns:
            st.table(leader_df.sort_values('Total Duration', ascending=False).head(5)[['Name', 'Rank', 'Total Duration']])
