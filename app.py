import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials

# --- 1. SECURE CONNECTION ---
@st.cache_resource
def get_gspread_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_info = json.loads(st.secrets["gcp_service_account"]["service_account_info"])
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        st.stop()

# --- 2. CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
st.set_page_config(page_title="Staff Management Pro", layout="wide")

# --- 3. DATA LOADING (STRICT ALIGNMENT) ---
@st.cache_data(ttl=2)
def load_data():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
        
        # Load Staff Details
        staff_data = sh.worksheet("Details").get_all_values()
        df_staff = pd.DataFrame(staff_data[1:], columns=staff_data[0]) if len(staff_data) > 1 else pd.DataFrame()
        
        # Load Event Logs
        event_data = sh.worksheet("Event Details").get_all_values()
        df_events = pd.DataFrame(event_data[1:], columns=event_data[0]) if len(event_data) > 1 else pd.DataFrame()

        # Clean IDs for searching
        clean_fn = lambda x: str(x).split('.')[0].strip()
        if not df_staff.empty: df_staff['SN'] = df_staff['SN'].apply(clean_fn)
        if not df_events.empty: df_events['Event ID'] = df_events['Event ID'].apply(clean_fn)

        return df_staff, df_events
    except Exception as e:
        st.error(f"Load Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_staff, df_events = load_data()

# --- 4. NAVIGATION ---
page = st.sidebar.radio("Navigation", ["📊 Dashboard", "👤 Staff Profiles", "🗓️ Event Logs", "🏆 Leaderboard", "➕ Add Data"])

# --- 5. PAGE LOGIC ---

if page == "🗓️ Event Logs":
    st.title("🗓️ Master Event Logs")
    if not df_events.empty:
        # Displaying columns exactly as per your Sheet screenshot
        cols = ["SN", "Event ID", "Event Location", "Event Name", "Event Date", "Event Duration (Mins)", "Master Group"]
        st.dataframe(df_events[[c for c in cols if c in df_events.columns]], use_container_width=True, hide_index=True)
    else:
        st.info("No logs found in 'Event Details' sheet.")

elif page == "👤 Staff Profiles":
    st.title("👤 Staff Activity Search")
    search_id = st.text_input("🔍 Enter Staff SN (to see their logs)")
    if search_id:
        # Search staff database
        person = df_staff[df_staff['SN'] == search_id.strip()]
        if not person.empty:
            st.success(f"Found: {person.iloc[0]['Name']}")
            # Link to events using Event ID
            logs = df_events[df_events['Event ID'] == search_id.strip()]
            if not logs.empty:
                st.dataframe(logs, use_container_width=True, hide_index=True)
            else:
                st.warning("This staff member has no logged events yet.")
        else:
            st.error("Staff SN not found in Details.")

elif page == "➕ Add Data":
    st.title("➕ Data Management")
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Register Staff")
        with st.form("f1", clear_on_submit=True):
            s_sn = st.text_input("SN")
            s_nm = st.text_input("Name")
            if st.form_submit_button("Save Staff"):
                sh.worksheet("Details").append_row([s_sn, "", s_nm, "", "", ""]) # Simplified for test
                st.cache_data.clear()
                st.rerun()

    with c2:
        st.subheader("Log Event")
        with st.form("f2", clear_on_submit=True):
            e_sn = st.text_input("Auto SN (Leave blank or enter #)")
            e_id = st.text_input("Staff SN (Event ID)")
            e_lc = st.text_input("Location")
            e_nm = st.text_input("Event Name")
            e_dt = st.date_input("Date")
            e_dr = st.text_input("Duration")
            e_gr = st.selectbox("Group", ["New Year", "Eid", "National Day", "Other"])
            
            if st.form_submit_button("Save Event"):
                # Matches your 7 columns: SN, Event ID, Location, Name, Date, Duration, Group
                sh.worksheet("Event Details").append_row([e_sn, e_id, e_lc, e_nm, str(e_dt), e_dr, e_gr])
                st.cache_data.clear()
                st.success("Logged! Syncing...")
                st.rerun()

elif page == "📊 Dashboard":
    st.title("📊 Overview")
    if not df_staff.empty:
        st.metric("Total Staff Registered", len(df_staff))
    if not df_events.empty and 'Master Group' in df_events.columns:
        st.bar_chart(df_events['Master Group'].value_counts())

elif page == "🏆 Leaderboard":
    st.title("🏆 Leaderboard")
    if not df_events.empty:
        # Ranking by most events attended
        rank = df_events['Event ID'].value_counts().reset_index()
        rank.columns = ['Staff SN', 'Events Done']
        st.table(rank)
