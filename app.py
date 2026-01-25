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
    # Loading with low_memory=False to ensure data types are consistent
    df_staff = pd.read_csv(DETAILS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df_events = pd.read_csv(EVENTS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    # Ensure SN is treated as a string across both sheets
    df_staff['SN'] = df_staff['SN'].astype(str)
    df_events['SN'] = df_events['SN'].astype(str)
    
    # Create Display Name for staff selection
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
    
    # --- SECTION 1: STAFF REGISTERED (Details Sheet) ---
    st.subheader("Registered Staff (Details Sheet)")
    s1, s2, s3 = st.columns(3)
    
    # Precise Count Logic
    # We remove any empty rows first to get an accurate total
    clean_staff_df = df_staff.dropna(subset=['SN'])
    total_reg = len(clean_staff_df)
    
    # Count "Drivers" (Assist.Technician) in Column F (Leader Badge)
    drivers_mask = clean_staff_df['Leader Badge'].str.contains('Driver', case=False, na=False)
    drivers_count = len(clean_staff_df[drivers_mask])
    
    # Team Leaders are the remainder
    team_leaders_count = total_reg - drivers_count
    
    s1.metric("Total Registered Staff", total_reg)
    s2.metric("Team Leaders", team_leaders_count)
    s3.metric("Assist. Technicians (Drivers)", drivers_count)

    st.write("---")

    # --- SECTION 2: STAFF ENGAGED & SUB-CATEGORIES ---
    st.subheader("Event Engagements (Event Details Sheet)")
    
    # Selection for Category (Master Group)
    master_groups = sorted(df_events['Master Group'].dropna().unique())
    selected_master = st.selectbox("Select Category (Master Group)", ["All"] + master_groups)
    
    # Filter data based on selection
    if selected_master != "All":
        filtered_events = df_events[df_events['Master Group'] == selected_master]
        
        # Selection for Sub-Category (Event Name) based on Master Group
        sub_events = sorted(filtered_events['Event Name'].dropna().unique())
        selected_sub = st.selectbox(f"Select Sub-Category for {selected_master}", ["All"] + sub_events)
        
        if selected_sub != "All":
            final_display_df = filtered_events[filtered_events['Event Name'] == selected_sub]
        else:
            final_display_df = filtered_events
    else:
        final_display_df = df_events

    # Display Metrics for Filtered Data
    m1, m2 = st.columns(2)
    m1.metric("Total Engagements", len(final_display_df))
    m2.metric("Unique Staff Involved", final_display_df['SN'].nunique())

    st.write(f"#### Showing Data for: {selected_master} > {selected_sub if selected_master != 'All' else ''}")
    st.dataframe(final_display_df, use_container_width=True, hide_index=True)

# --- TAB 5: LEADERBOARD (DYNAMIC BASED ON FILTERS) ---
with tab5:
    st.title("🏆 Engagement Leaderboard")
    st.write("Top 5 Staff based on the filters selected in the Dashboard.")
    
    # Use the 'final_display_df' from Tab 1 filters for a dynamic leaderboard
    try:
        top_staff = final_display_df['SN'].value_counts().head(5).reset_index()
        top_staff.columns = ['SN', 'Engagements']
        top_staff = pd.merge(top_staff, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
        st.table(top_staff[['Name', 'Rank', 'Engagements']])
    except:
        st.warning("No engagement data available for this selection.")
