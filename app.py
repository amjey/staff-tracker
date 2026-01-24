import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"

st.set_page_config(page_title="Staff Management System", layout="wide")

@st.cache_data(ttl=30)
def load_data():
    # Load data and strip spaces from all text columns
    df_staff = pd.read_csv(DETAILS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df_events = pd.read_csv(EVENTS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    # Ensure SN is string for reliable matching
    df_staff['SN'] = df_staff['SN'].astype(str)
    df_events['SN'] = df_events['SN'].astype(str)
    return df_staff, df_events

# --- SECURITY ---
if "auth" not in st.session_state:
    st.title("🔒 Staff System Login")
    pwd = st.text_input("Enter Admin Password", type="password")
    if st.button("Login"):
        if pwd == "Admin@2026":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Invalid Password")
    st.stop()

# --- LOAD DATA ---
df_staff, df_events = load_data()

# --- RESTORED TABBED NAVIGATION ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "👤 Staff Details", "🗓️ Event Logs"])

with tab1:
    st.title("📊 System Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Staff", len(df_staff))
    col2.metric("Total Events", len(df_events))
    col3.metric("Last Sync", datetime.now().strftime("%H:%M"))
    
    # Quick View of merged data
    st.write("### Recent Activity")
    combined = pd.merge(df_staff, df_events, on="SN", how="left")
    st.dataframe(combined.head(10), use_container_width=True, hide_index=True)

with tab2:
    st.title("👤 Staff Management")
    search = st.text_input("🔍 Search Staff by Name or SN")
    
    display_staff = df_staff
    if search:
        display_staff = df_staff[df_staff['Name'].str.contains(search, case=False, na=False) | 
                                 df_staff['SN'].str.contains(search, case=False, na=False)]
    
    st.dataframe(display_staff, use_container_width=True, hide_index=True)

with tab3:
    st.title("🗓️ Event Records")
    event_search = st.text_input("🔍 Search Events by Location or Name")
    
    display_events = df_events
    if event_search:
        display_events = df_events[df_events['Event Location'].str.contains(event_search, case=False, na=False) | 
                                   df_events['Event Name'].str.contains(event_search, case=False, na=False)]
    
    st.dataframe(display_events, use_container_width=True, hide_index=True)

# Sidebar Refresh
if st.sidebar.button("🔄 Force Refresh Data"):
    st.cache_data.clear()
    st.rerun()
