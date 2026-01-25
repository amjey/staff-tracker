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
    # Load and immediately strip whitespace from headers
    df_staff = pd.read_csv(DETAILS_URL).rename(columns=lambda x: x.strip())
    df_events = pd.read_csv(EVENTS_URL).rename(columns=lambda x: x.strip())
    
    # Aggressive SN Cleaning
    def clean_val(val):
        return str(val).split('.')[0].strip()

    df_staff['SN'] = df_staff['SN'].apply(clean_val)
    df_events['SN'] = df_events['SN'].apply(clean_val)
    
    if 'Contact' in df_staff.columns:
        df_staff['Contact'] = df_staff['Contact'].apply(clean_val)
    
    # Duration Column Finder
    dur_col = None
    for col in df_events.columns:
        if 'duration' in col.lower():
            dur_col = col
            df_events[dur_col] = pd.to_numeric(df_events[dur_col], errors='coerce').fillna(0)
            break

    # Categorization logic for Dashboard metrics
    def categorize_staff(badge):
        b = str(badge).strip()
        if b in ["Assist.Technician", "Driver"]: return "Assist.Technician"
        if b in ["Master in Fireworks", "Pro in Fireworks", "Team Leader"]: return "Team Leader"
        return "Unassigned"

    df_staff['Category'] = df_staff['Leader Badge'].apply(categorize_staff)
    return df_staff, df_events, dur_col

# Load data ONCE at the start
df_staff, df_events, dur_col = load_data()

# --- STABLE TAB NAVIGATION ---
# This is the industry standard way to prevent Streamlit from jumping tabs on input
t1, t2, t3, t4, t5 = st.tabs(["📊 Dashboard", "👤 Staff Details", "➕ Add Data", "🗓️ Event Logs", "🏆 Leaderboard"])

# --- TAB 1: DASHBOARD ---
with t1:
    st.title("📊 Strategic Overview")
    
    # Top Row Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Registered", len(df_staff))
    m2.metric("Team Leaders", len(df_staff[df_staff['Category'] == "Team Leader"]))
    m3.metric("Assist. Technicians", len(df_staff[df_staff['Category'] == "Assist.Technician"]))
    
    st.write("---")
    
    # Distribution Charts
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Events by Master Group")
        # Check if column exists before plotting to avoid empty tab
        group_col = 'Master Group' if 'Master Group' in df_events.columns else None
        if group_col:
            unique_ev = df_events.drop_duplicates(subset=['Event Name', 'Event Location'])
            counts = unique_ev[group_col].value_counts()
            st.bar_chart(counts, color="#0072B2")
        else:
            st.info("Column 'Master Group' not found in Event Details.")

    with c2:
        st.subheader("Staff by Role")
        role_counts = df_staff['Leader Badge'].value_counts()
        st.bar_chart(role_counts, color="#009E73")

# --- TAB 2: STAFF DETAILS ---
with t2:
    st.title("👤 Staff Profiles")
    
    # 1. Filter and Search UI
    f1, f2 = st.columns([1, 2])
    with f1:
        all_opts = ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"]
        role_filter = st.multiselect("Filter Directory:", options=all_opts, default=all_opts)
    with f2:
        # Search Box with persistent key
        search_sn = st.text_input("🔍 Search by SN and press Enter", key="staff_search_persisted")

    # 2. Main Directory Table
    filtered_df = df_staff[df_staff['Leader Badge'].isin(role_filter)]
    st.write("### 🗂️ Staff Directory")
    st.dataframe(filtered_df[['SN', 'Rank', 'Name', 'Unit', 'Contact', 'Leader Badge']], 
                 use_container_width=True, hide_index=True)

    # 3. Individual Profile View
    if search_sn:
        clean_sn = str(search_sn).strip()
        match = df_staff[df_staff['SN'] == clean_sn]
        
        if not match.empty:
            p = match.iloc[0]
            st.markdown("---")
            st.header(f"Profile: {p['Name']}")
            
            # Metrics
            cols = st.columns(4)
            cols[0].metric("Rank", p['Rank'])
            cols[1].metric("Unit", p['Unit'])
            cols[2].metric("Contact", p['Contact'])
            cols[3].metric("Badge", p['Leader Badge'])
            
            # Performance Calc
            personal_ev = df_events[df_events['SN'] == clean_sn]
            total_events = len(personal_ev)
            total_mins = personal_ev[dur_col].sum() if dur_col else 0
            
            st.write("---")
            res1, res2 = st.columns(2)
            res1.metric("Total Events Attended", total_events)
            res2.metric("Total Duration", f"{int(total_mins)} Mins")
            
            st.subheader("Detailed Attendance Log")
            st.dataframe(personal_ev, use_container_width=True, hide_index=True)
        else:
            st.warning(f"No match found for SN: {search_sn}")

# --- TAB 3: ADD DATA ---
with t3:
    st.title("➕ Data Management")
    st.write("Use the forms below to prepare data for Google Sheets.")
    st.link_button("Open Master Google Sheet", SHEET_EDIT_URL)
    # (Form code here as per previous working versions)

# --- TAB 4 & 5: LOGS & LEADERBOARD ---
with t4:
    st.title("🗓️ Event Logs")
    st.dataframe(df_events, use_container_width=True, hide_index=True)

with t5:
    st.title("🏆 Leaderboard")
    top_n = df_events['SN'].value_counts().head(10).reset_index()
    top_n.columns = ['SN', 'Engagements']
    leaderboard = pd.merge(top_n, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.dataframe(leaderboard[['Name', 'Rank', 'Engagements']], use_container_width=True, hide_index=True)
