import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials

# --- 1. SECURE GOOGLE SHEETS CONNECTION ---
@st.cache_resource
def get_gspread_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        # Reads from your triple-quoted Secrets [gcp_service_account]
        creds_info = json.loads(st.secrets["gcp_service_account"]["service_account_info"])
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Secret Configuration Error: {e}")
        st.stop()

# --- 2. GLOBAL CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
st.set_page_config(page_title="Staff Management Pro", layout="wide")

# --- 3. DATA LOADING ---
@st.cache_data(ttl=2)
def load_data_via_api():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
        
        def get_df(worksheet_name):
            data = sh.worksheet(worksheet_name).get_all_values()
            if not data: return pd.DataFrame()
            headers = [h.strip() for h in data[0] if h.strip()]
            # Ensure we only take the columns we have headers for
            df = pd.DataFrame(data[1:], columns=data[0])
            return df

        df_staff = get_df("Details")
        df_events = get_df("Event Details")

        # Clean IDs for searching (removes decimals/spaces)
        clean_fn = lambda x: str(x).split('.')[0].strip()
        if not df_staff.empty and 'SN' in df_staff.columns:
            df_staff['SN'] = df_staff['SN'].apply(clean_fn)
        if not df_events.empty and 'Event ID' in df_events.columns:
            df_events['Event ID'] = df_events['Event ID'].apply(clean_fn)

        return df_staff, df_events
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_staff, df_events = load_data_via_api()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("Main Menu")
    page = st.radio("Go to:", ["📊 Dashboard", "👤 Staff Profiles", "🗓️ Event Logs", "🏆 Leaderboard", "➕ Add Data"])
    if st.button("🔄 Sync Live Data"):
        st.cache_data.clear()
        st.rerun()

# --- 5. PAGE LOGIC ---

if page == "🗓️ Event Logs":
    st.title("🗓️ Event Logs")
    if not df_events.empty:
        # We explicitly select these to match your green header image
        cols = ["SN", "Event ID", "Event Location", "Event Name", "Event Date", "Event Duration (Mins)", "Master Group"]
        available_cols = [c for c in cols if c in df_events.columns]
        st.dataframe(df_events[available_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No logs found.")

elif page == "👤 Staff Profiles":
    st.title("👤 Staff Profile Search")
    # This searches the "Event ID" column using the Staff "SN"
    search_id = st.text_input("🔍 Enter Staff SN (e.g., 1)")
    
    if search_id:
        # Show basic staff info
        staff_info = df_staff[df_staff['SN'] == search_id.strip()]
        if not staff_info.empty:
            st.header(f"Staff: {staff_info.iloc[0]['Name']}")
            
            # Show their specific event logs
            personal_logs = df_events[df_events['Event ID'] == search_id.strip()]
            if not personal_logs.empty:
                st.subheader("Activity History")
                st.dataframe(personal_logs, use_container_width=True, hide_index=True)
            else:
                st.warning("No events found for this Staff SN.")
        else:
            st.error("Staff SN not found in Details sheet.")

elif page == "➕ Add Data":
    st.title("➕ Data Management")
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📋 New Staff")
        with st.form("staff_f", clear_on_submit=True):
            s_sn = st.text_input("SN")
            s_rk = st.text_input("Rank")
            s_nm = st.text_input("Name")
            s_un = st.text_input("Unit")
            s_ct = st.text_input("Contact")
            s_bd = st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
            if st.form_submit_button("Save Staff"):
                sh.worksheet("Details").append_row([s_sn, s_rk, s_nm, s_un, s_ct, s_bd])
                st.cache_data.clear()
                st.success("Staff saved!")
                st.rerun()

    with c2:
        st.subheader("🔥 Log New Event")
        with st.form("event_f", clear_on_submit=True):
            e_sn_internal = st.text_input("Serial No (SN)")
            e_id = st.text_input("Staff SN (Event ID)")
            e_lc = st.text_input("Location")
            e_nm = st.text_input("Event Name")
            e_dt = st.date_input("Date")
            e_dr = st.text_input("Duration")
            e_gr = st.selectbox("Master Group", ["New Year", "Eid", "National Day", "Other"])
            
            if st.form_submit_button("Save Event"):
                # Matches your Google Sheet: SN, Event ID, Location, Name, Date, Duration, Group
                sh.worksheet("Event Details").append_row([e_sn_internal, e_id, e_lc, e_nm, str(e_dt), e_dr, e_gr])
                st.cache_data.clear()
                st.success("Event Logged!")
                st.rerun()

elif page == "📊 Dashboard":
    st.title("📊 Overview")
    if not df_staff.empty:
        st.metric("Total Registered", len(df_staff))
        st.divider()
        if 'Master Group' in df_events.columns:
            st.bar_chart(df_events['Master Group'].value_counts())

elif page == "🏆 Leaderboard":
    st.title("🏆 Leaderboard")
    if not df_events.empty:
        top = df_events['Event ID'].value_counts().head(5).reset_index()
        top.columns = ['SN', 'Total Events']
        st.table(top)
