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
    # Load and immediately strip whitespace from column names
    df_staff = pd.read_csv(DETAILS_URL).rename(columns=lambda x: x.strip())
    df_events = pd.read_csv(EVENTS_URL).rename(columns=lambda x: x.strip())
    
    # Fix 'None' and matching errors: Standardize SNs as clean strings
    for df in [df_staff, df_events]:
        df['SN'] = df['SN'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    # Ensure Duration is numeric for profile math
    dur_col = 'Event duration(Mins)' if 'Event duration(Mins)' in df_events.columns else 'Duration'
    if dur_col in df_events.columns:
        df_events[dur_col] = pd.to_numeric(df_events[dur_col], errors='coerce').fillna(0)

    # UPDATED CATEGORIZATION logic
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
    # Using 'Event Name' for deduplication to avoid KeyError on missing 'Date' column
    unique_events = df_events.drop_duplicates(subset=['Event Name', 'Event Location'])
    
    col_chart, col_table = st.columns([1, 1])
    with col_table:
        cat_counts = unique_events['Master Group'].value_counts().reset_index()
        cat_counts.columns = ['Event Category', 'Count']
        st.dataframe(cat_counts, use_container_width=True, hide_index=True)
    with col_chart:
        st.bar_chart(unique_events['Master Group'].value_counts(), color="#0072B2")

# --- TAB 2: STAFF DETAILS (SEARCH & PROFILES) ---
with tab2:
    st.title("👤 Staff Details & History")
    
    # SN Search Bar
    search_sn = st.text_input("🔍 Search by Serial Number (SN)", placeholder="Enter SN (e.g., 101)...")
    
    if search_sn:
        person = df_staff[df_staff['SN'] == search_sn]
        if not person.empty:
            p = person.iloc[0]
            st.header(f"Profile: {p['Name']}")
            
            # Row 1: Info Cards
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Rank", p['Rank'])
            m2.metric("Unit", p['Unit'])
            m3.metric("Contact", p['Contact'])
            m4.metric("Role", p['Category'])
            
            # Row 2: Performance Metrics
            history = df_events[df_events['SN'] == search_sn]
            total_events = len(history)
            total_mins = history[dur_col].sum()
            
            st.write("---")
            e1, e2 = st.columns(2)
            e1.metric("Total Events Attended", total_events)
            e2.metric("Total Duration", f"{total_mins} Mins")
            
            st.subheader("Personal Event History")
            # Display relevant event columns - adjust names if they differ in your sheet
            display_cols = [c for c in ['Event Date', 'Event Name', 'Event Location', dur_col] if c in history.columns]
            st.dataframe(history[display_cols], use_container_width=True, hide_index=True)
        else:
            st.warning("No staff member found with that SN. Please check the directory below.")

    st.write("---")
    st.subheader("All Registered Staff")
    st.dataframe(df_staff[['SN', 'Rank', 'Name', 'Unit', 'Contact', 'Leader Badge']], 
                 use_container_width=True, hide_index=True)

# --- TAB 3: ADD DATA (FORMS) ---
with tab3:
    st.title("➕ Data Management")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Add Staff Info")
        with st.form("staff_form"):
            sn = st.text_input("SN")
            name = st.text_input("Full Name")
            rank = st.text_input("Rank")
            unit = st.text_input("Unit")
            contact = st.text_input("Contact")
            badge = st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
            if st.form_submit_button("Save Staff"):
                st.link_button("Open Sheet to Paste", SHEET_EDIT_URL)

    with col_b:
        st.subheader("Log New Event")
        with st.form("event_form"):
            e_name = st.text_input("Event Name")
            e_loc = st.text_input("Event Location")
            e_date = st.date_input("Event Date")
            e_dur = st.number_input("Event duration(Mins)", min_value=1)
            e_staff = st.multiselect("Select Staff Members", options=df_staff['Name'].tolist())
            if st.form_submit_button("Log Event"):
                st.link_button("Open Sheet to Paste", SHEET_EDIT_URL)

# --- TABS 4 & 5: RESTORED LOGS & LEADERBOARD ---
with tab4:
    st.title("🗓️ Master Event Logs")
    st.dataframe(df_events, use_container_width=True, hide_index=True)

with tab5:
    st.title("🏆 Leaderboard")
    top = df_events['SN'].value_counts().head(10).reset_index()
    top.columns = ['SN', 'Engagements']
    top_detailed = pd.merge(top, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.dataframe(top_detailed[['Name', 'Rank', 'Engagements']], use_container_width=True, hide_index=True)
