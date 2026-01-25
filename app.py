import streamlit as st
import pandas as pd

# --- CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=10)
def load_data():
    # Load and force strip whitespaces from column headers and data
    df_staff = pd.read_csv(DETAILS_URL)
    df_staff.columns = df_staff.columns.str.strip()
    df_staff = df_staff.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    df_events = pd.read_csv(EVENTS_URL)
    df_events.columns = df_events.columns.str.strip()
    df_events = df_events.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    # Validation: Only count rows that have a Serial Number
    df_staff = df_staff.dropna(subset=['SN'])
    df_events = df_events.dropna(subset=['SN'])
    
    # Logic for Category (Column F: Leader Badge)
    # This fixes the 151/731 count issue
    df_staff['Category'] = df_staff['Leader Badge'].apply(
        lambda x: "Assist.Technician" if str(x).lower() == "driver" else "Team Leader"
    )
    
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

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "👤 Staff Details", "🏆 Leaderboard"])

with tab1:
    st.title("📊 Event Location Dashboard")

    # --- 1. STAFF TOTALS (Fixes the 878/4 error) ---
    st.subheader("Staff Totals")
    s1, s2, s3 = st.columns(3)
    
    total_reg = len(df_staff)
    assist_techs = len(df_staff[df_staff['Category'] == "Assist.Technician"])
    team_leaders = total_reg - assist_techs
    
    s1.metric("Total Registered", total_reg)
    s2.metric("Team Leaders", team_leaders)
    s3.metric("Assist. Technicians", assist_techs)

    st.write("---")

    # --- 2. UNIQUE EVENTS BY LOCATION ---
    st.subheader("Events by Location")
    
    # We identify a unique event by its Name and Location
    # This prevents counting all 1735 staff engagements as separate events
    event_cols = ['Event Name', 'Event Location']
    # Check if 'Date' exists to make the count even more accurate
    if 'Date' in df_events.columns:
        event_cols.append('Date')
        
    unique_events_df = df_events.drop_duplicates(subset=event_cols)
    
    m1, m2 = st.columns(2)
    m1.metric("Total Unique Events", len(unique_events_df))
    m2.metric("Total Staff Engagements", len(df_events))

    # Visual Breakdown
    loc_counts = unique_events_df['Event Location'].value_counts()
    st.bar_chart(loc_counts)

    # --- 3. NESTED FILTERING (SUB-CATEGORIES) ---
    st.write("---")
    st.subheader("Location Deep-Dive")
    
    sel_loc = st.selectbox("Select Location", sorted(df_events['Event Location'].unique()))
    
    # Filter by Location
    loc_data = df_events[df_events['Event Location'] == sel_loc]
    
    # Show Sub-Categories (Event Names) for that location
    sel_sub = st.selectbox(f"Select Event at {sel_loc}", sorted(loc_data['Event Name'].unique()))
    
    final_view = loc_data[loc_data['Event Name'] == sel_sub]
    st.write(f"**Staff Present ({len(final_view)}):**")
    st.dataframe(final_view[['SN', 'Name', 'Rank']], use_container_width=True, hide_index=True)

with tab3:
    st.title("🏆 Leaderboard")
    # Top 5 by row count (Engagements)
    top_staff = df_events['SN'].value_counts().head(5).reset_index()
    top_staff.columns = ['SN', 'Engagements']
    top_staff = pd.merge(top_staff, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.table(top_staff[['Name', 'Rank', 'Engagements']])
