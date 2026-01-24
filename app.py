import streamlit as st
import pandas as pd

# --- CONFIGURATION ---
SHEET_ID = "1S33Dk_p9V1Xl2k7v_YkP_Y3x_9-u-W_06y298pIidAg" # Your Sheet ID
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"

st.set_page_config(page_title="Staff Tracking Dashboard", layout="wide")

@st.cache_data(ttl=30)
def load_data():
    # Load Details
    df_details = pd.read_csv(DETAILS_URL)
    df_details.columns = df_details.columns.str.strip()  # Removes hidden spaces
    
    # Load Events
    df_events = pd.read_csv(EVENTS_URL)
    df_events.columns = df_events.columns.str.strip()    # Removes hidden spaces
    
    return df_details, df_events

# --- SECURITY ---
def check_password():
    """Returns True if the user had the correct password."""
    if "password_correct" not in st.session_state:
        st.title("🔒 Security Access")
        password = st.text_input("Enter Dashboard Password", type="password")
        if st.button("Login"):
            if password == "Admin@2026": # You can change this
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("😕 Password incorrect")
        return False
    return True

if check_password():
    # --- MAIN DASHBOARD ---
    try:
        details, events = load_data()
        
        st.title("📊 Staff Activity Dashboard")
        
        # Merge data on SN
        combined_data = pd.merge(details, events, on="SN", how="inner")
        
        # Display Data
        st.write("### Current Staff Activities")
        st.dataframe(combined_data, use_container_width=True)
        
        # Simple Metrics
        col1, col2 = st.columns(2)
        col1.metric("Total Staff", len(details))
        col2.metric("Total Events", len(events))

    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.info("Check that your Google Sheet headers are exactly 'SN', 'Name', etc.")
