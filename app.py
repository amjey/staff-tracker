import streamlit as st
import pandas as pd

# --- CONFIGURATION ---
# Fixed Sheet ID from your shared link
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"

st.set_page_config(page_title="Staff Management System", layout="wide")

@st.cache_data(ttl=30)
def load_data():
    try:
        # Load and clean Details
        df_details = pd.read_csv(DETAILS_URL)
        df_details.columns = df_details.columns.str.strip()
        
        # Load and clean Events
        df_events = pd.read_csv(EVENTS_URL)
        df_events.columns = df_events.columns.str.strip()
        
        return df_details, df_events
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None

# --- SECURITY ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔒 Security Access")
        pwd = st.text_input("Enter Dashboard Password", type="password")
        if st.button("Login"):
            if pwd == "Admin@2026": 
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("😕 Password incorrect")
        return False
    return True

if check_password():
    # --- MAIN DASHBOARD ---
    details, events = load_data()
    
    if details is not None and events is not None:
        st.title("📊 Staff Activity Dashboard")
        
        # Check if 'SN' exists before merging to avoid the 'SN' error
        if 'SN' in details.columns and 'SN' in events.columns:
            combined_data = pd.merge(details, events, on="SN", how="inner")
            
            # Display Summary Metrics
            c1, c2 = st.columns(2)
            c1.metric("Total Staff", len(details))
            c2.metric("Total Events", len(events))
            
            st.write("### Integrated Staff Data")
            st.dataframe(combined_data, use_container_width=True)
        else:
            st.warning("Could not find 'SN' column. Check your Google Sheet headers.")
