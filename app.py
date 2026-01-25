import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=10)
def load_data():
    # Load and clean whitespace
    df_staff = pd.read_csv(DETAILS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df_events = pd.read_csv(EVENTS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    # Validation: Remove rows where SN is empty to get true counts
    df_staff = df_staff.dropna(subset=['SN'])
    df_events = df_events.dropna(subset=['SN'])
    
    # Ensure SN is string
    df_staff['SN'] = df_staff['SN'].astype(str)
    df_events['SN'] = df_events['SN'].astype(str)
    
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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "👤 Staff Details", "🗓️ Event Logs", "🏆 Leaderboard", "⚙️ Admin"])

with tab1:
    st.title("📊 System Dashboard")
    
    # --- 1. THE STAFF REGISTERED SECTION ---
    st.subheader("Total Registered Staff")
    s1, s2, s3 = st.columns(3)
    
    # Rule: Column F (Leader Badge) == "Driver" -> Assist. Technician
    drivers = df_staff[df_staff['Leader Badge'].str.contains('Driver', case=False, na=False)]
    t_leaders = df_staff[~df_staff['Leader Badge'].str.contains('Driver', case=False, na=False)]
    
    s1.metric("Total Staff", len(df_staff))
    s2.metric("Team Leaders", len(t_leaders))
    s3.metric("Assist. Technicians", len(drivers))

    st.write("---")

    # --- 2. THE EVENT ENGAGEMENT SECTION (WITH LOCATION) ---
    st.subheader("Event Engagements & Locations")
    
    # Filters: Location -> Master Category -> Sub Category
    c_loc, c_mast, c_sub = st.columns(3)
    
    with c_loc:
        locations = sorted(df_events['Event Location'].dropna().unique())
        sel_loc = st.selectbox("1. Select Location", ["All Locations"] + locations)
    
    # Filter by Location first
    work_df = df_events.copy()
    if sel_loc != "All Locations":
        work_df = work_df[work_df['Event Location'] == sel_loc]
        
    with c_mast:
        master_groups = sorted(work_df['Master Group'].dropna().unique())
        sel_mast = st.selectbox("2. Select Category", ["All Categories"] + master_groups)
        
    if sel_mast != "All Categories":
        work_df = work_df[work_df['Master Group'] == sel_mast]
        
    with c_sub:
        sub_events = sorted(work_df['Event Name'].dropna().unique())
        sel_sub = st.selectbox("3. Select Sub-Category", ["All Sub-Events"] + sub_events)

    if sel_sub != "All Sub-Events":
        work_df = work_df[work_df['Event Name'] == sel_sub]

    # Metrics for the current selection
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Engagements", len(work_df))
    m2.metric("Unique Staff", work_df['SN'].nunique())
    m3.metric("Filtered Location", sel_loc if sel_loc != "All Locations" else "Global")

    st.write("#### Resulting Data")
    st.dataframe(work_df, use_container_width=True, hide_index=True)

with tab4:
    st.title("🏆 Filtered Leaderboard")
    st.write(f"Showing top performers for: **{sel_loc}** | **{sel_mast}**")
    
    # Top 5 based on the active filters in Tab 1
    leader_counts = work_df['SN'].value_counts().head(5).reset_index()
    leader_counts.columns = ['SN', 'Count']
    
    # Join with names
    leader_final = pd.merge(leader_counts, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.table(leader_final[['Name', 'Rank', 'Count']])
