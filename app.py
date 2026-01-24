import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"

st.set_page_config(page_title="Staff Tracker Pro", layout="wide")

@st.cache_data(ttl=30)
def load_data():
    df_details = pd.read_csv(DETAILS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df_events = pd.read_csv(EVENTS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    # Ensure SN is treated as a string for perfect matching
    df_details['SN'] = df_details['SN'].astype(str)
    df_events['SN'] = df_events['SN'].astype(str)
    return df_details, df_events

# --- LOGIN ---
if "auth" not in st.session_state:
    st.title("🔒 Staff Portal Login")
    if st.text_input("Password", type="password") == "Admin@2026":
        if st.button("Access Dashboard"):
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- MAIN APP ---
df_staff, df_events = load_data()

st.title("📊 Staff Activity Dashboard")
st.caption(f"Last synced: {datetime.now().strftime('%H:%M:%S')}")

# Top Row Metrics
c1, c2, c3 = st.columns(3)
c1.metric("Registered Staff", len(df_staff))
c2.metric("Total Events Logged", len(df_events))
c3.metric("Data Source", "Google Sheets")

# Search and Filters
st.write("---")
search_query = st.text_input("🔍 Search by Name or SN", "")

# Merge Data (Left join shows ALL staff)
combined = pd.merge(df_staff, df_events, on="SN", how="left")

# Apply Search
if search_query:
    combined = combined[
        combined['Name'].str.contains(search_query, case=False, na=False) | 
        combined['SN'].str.contains(search_query, case=False, na=False)
    ]

st.write(f"### Displaying {len(combined)} records")
st.dataframe(combined, use_container_width=True, hide_index=True)

if st.button("🔄 Refresh Data Now"):
    st.cache_data.clear()
    st.rerun()
