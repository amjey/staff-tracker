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
    
    # --- UPDATED CATEGORIZATION (Column F - Leader Badge) ---
    # We strictly look at Column F. If it says "Driver", they are Assist.Technician. 
    # Everything else in Column F is counted as Team Leader.
    df_staff['Category'] = df_staff['Leader Badge'].apply(
        lambda x: "Assist.Technician" if str(x).lower() == "driver" else "Team Leader"
    )
    
    # Force SN to string for both sheets to ensure the link works
    df_staff['SN'] = df_staff['SN'].astype(str)
    df_events['SN'] = df_events['SN'].astype(str)
    
    # Create Display Name for selectors
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

df_staff, df_events = load_data()

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "➕ Add Data", "👤 Staff Details", "🗓️ Event Logs", "🏆 Leaderboard"])

with tab1:
    st.title("📊 Dashboard Overview")
    
    # 1. Staff Statistics based on Column F
    st.subheader("Staff by Categories")
    c1, c2, c3 = st.columns(3)
    
    total_staff = len(df_staff)
    # Correcting counts based on your specific logic for Column F
    assist_techs = len(df_staff[df_staff['Category'] == "Assist.Technician"])
    team_leaders = len(df_staff[df_staff['Category'] == "Team Leader"])
    
    c1.metric("Total Registered", total_staff)
    c2.metric("Team Leaders", team_leaders)
    c3.metric("Assist. Technicians (Drivers)", assist_techs)

    # 2. FIXING EVENT DATA VISIBILITY
    st.write("---")
    st.subheader("Events by Category")
    
    # Merging event SNs with staff Categories to ensure counts aren't "empty"
    event_with_cat = pd.merge(df_events, df_staff[['SN', 'Category']], on='SN', how='left')
    
    # Filter out events where the SN might not be in the staff list
    valid_events = event_with_cat.dropna(subset=['Category'])
    cat_event_counts = valid_events['Category'].value_counts()
    
    col_chart, col_table = st.columns(2)
    with col_chart:
        if not cat_event_counts.empty:
            st.bar_chart(cat_event_counts)
        else:
            st.info("No events found for registered staff categories.")
            
    with col_table:
        st.write("**Category Breakdown**")
        if not cat_event_counts.empty:
            # Reshape for display
            display_counts = cat_event_counts.reset_index()
            display_counts.columns = ['Category', 'Event Count']
            st.dataframe(display_counts, use_container_width=True, hide_index=True)
        else:
            st.warning("Event list is empty or SNs do not match staff details.")

# [Rest of your tabs (tab2-tab5) remain here as they were previously defined]
