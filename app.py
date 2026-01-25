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
    
    # Standardize SNs to avoid matching errors
    for df in [df_staff, df_events]:
        df['SN'] = df['SN'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    # Find the duration column safely to prevent KeyError
    dur_col = None
    possible_names = ['Event duration(Mins)', 'Duration', 'duration']
    for name in possible_names:
        if name in df_events.columns:
            dur_col = name
            df_events[dur_col] = pd.to_numeric(df_events[dur_col], errors='coerce').fillna(0)
            break

    # Your Specific Badge Rules
    def categorize_staff(badge):
        badge_str = str(badge).strip()
        if badge_str in ["Assist.Technician", "Driver"]:
            return "Assist.Technician"
        elif badge_str in ["Master in Fireworks", "Pro in Fireworks", "Team Leader"]:
            return "Team Leader"
        return "Unassigned"

    df_staff['Category'] = df_staff['Leader Badge'].apply(categorize_staff)
    return df_staff, df_events, dur_col

df_staff, df_events, dur_col = load_data()

# --- TABS ---
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
    # Safer deduplication to avoid KeyError: 'Date'
    subset_cols = [c for c in ['Event Name', 'Event Location', 'Date', 'Event Date'] if c in df_events.columns]
    unique_ev = df_events.drop_duplicates(subset=subset_cols)
    
    st.subheader("Event Distribution")
    if 'Master Group' in unique_ev.columns:
        st.bar_chart(unique_ev['Master Group'].value_counts(), color="#0072B2")

# --- TAB 2: STAFF DETAILS (SEARCH & SELECT) ---
with tab2:
    st.title("👤 Staff Directory & Individual Profiles")
    
    # Search by SN to narrow down the selection
    search_query = st.text_input("🔍 Search by SN", placeholder="Enter SN...")
    
    filtered_staff = df_staff
    if search_query:
        filtered_staff = df_staff[df_staff['SN'].str.contains(search_query)]

    # Selectbox for picking the specific staff member to view profile
    staff_list = filtered_staff['Name'].tolist()
    if staff_list:
        selected_name = st.selectbox("Select a Staff Member to view full details:", ["-- Choose --"] + staff_list)
        
        if selected_name != "-- Choose --":
            p = df_staff[df_staff['Name'] == selected_name].iloc[0]
            st.markdown(f"## Profile: {p['Name']}")
            
            # Personal Details
            col_info1, col_info2, col_info3, col_info4 = st.columns(4)
            col_info1.metric("Rank", p['Rank'])
            col_info2.metric("Unit", p['Unit'])
            col_info3.metric("Contact", p['Contact'])
            col_info4.metric("Badge", p['Leader Badge'])
            
            # Performance Stats
            history = df_events[df_events['SN'] == p['SN']]
            total_events = len(history)
            total_mins = history[dur_col].sum() if dur_col else 0
            
            st.write("---")
            m1, m2 = st.columns(2)
            m1.metric("Total Events Attended", total_events)
            m2.metric("Total Event Duration", f"{total_mins} Mins")
            
            st.subheader("Attendance History")
            st.dataframe(history, use_container_width=True, hide_index=True)
    else:
        st.warning("No staff found with that SN.")

    st.write("---")
    st.subheader("All Staff Directory")
    st.dataframe(df_staff[['SN', 'Rank', 'Name', 'Unit', 'Contact', 'Leader Badge']], 
                 use_container_width=True, hide_index=True)

# --- TAB 3: ADD DATA (UPDATED FORMS) ---
with tab3:
    st.title("➕ Data Management")
    c_a, c_b = st.columns(2)
    with c_a:
        st.subheader("Add Staff Info")
        with st.form("staff_f"):
            s_sn = st.text_input("SN")
            s_na = st.text_input("Full Name")
            s_ra = st.text_input("Rank")
            s_un = st.text_input("Unit") # missing field restored
            s_co = st.text_input("Contact") # missing field restored
            s_ba = st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
            if st.form_submit_button("Submit"): st.link_button("Paste to Sheet", SHEET_EDIT_URL)
    with c_b:
        st.subheader("Log New Event")
        with st.form("event_f"):
            e_na = st.text_input("Event Name")
            e_lo = st.text_input("Event Location")
            e_da = st.date_input("Event Date") # restored
            e_du = st.number_input("Event duration(Mins)", min_value=1) # restored
            if st.form_submit_button("Log"): st.link_button("Paste to Sheet", SHEET_EDIT_URL)

# --- TABS 4 & 5: LOGS & LEADERBOARD ---
with tab4:
    st.title("🗓️ Master Event Logs")
    st.dataframe(df_events, use_container_width=True, hide_index=True)

with tab5:
    st.title("🏆 Leaderboard")
    counts = df_events['SN'].value_counts().head(10).reset_index()
    counts.columns = ['SN', 'Engagements']
    board = pd.merge(counts, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.dataframe(board[['Name', 'Rank', 'Engagements']], use_container_width=True, hide_index=True)
