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

# --- 3. DATA LOADING ---
@st.cache_data(ttl=2)
def load_data():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
        
        # Load Staff Details
        staff_raw = sh.worksheet("Details").get_all_values()
        df_staff = pd.DataFrame(staff_raw[1:], columns=staff_raw[0]) if len(staff_raw) > 1 else pd.DataFrame()
        
        # Load Event Logs
        event_raw = sh.worksheet("Event Details").get_all_values()
        df_events = pd.DataFrame(event_raw[1:], columns=event_raw[0]) if len(event_raw) > 1 else pd.DataFrame()

        # Standardize IDs for searching/logic
        clean_fn = lambda x: str(x).split('.')[0].strip()
        if not df_staff.empty and 'SN' in df_staff.columns:
            df_staff['SN'] = df_staff['SN'].apply(clean_fn)
        if not df_events.empty and 'Event ID' in df_events.columns:
            df_events['Event ID'] = df_events['Event ID'].apply(clean_fn)

        return df_staff, df_events
    except Exception as e:
        st.error(f"Load Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_staff, df_events = load_data()

# --- 4. NAVIGATION ---
page = st.sidebar.radio("Navigation", ["📊 Dashboard", "👤 Staff Profiles", "🗓️ Event Logs", "🏆 Leaderboard", "➕ Add Data"])

# --- 5. PAGE LOGIC ---

if page == "📊 Dashboard":
    st.title("📊 Strategic Overview")
    if not df_staff.empty:
        # Define Badge Column (Usually 'Leader Badge' or the last column)
        badge_col = 'Leader Badge' if 'Leader Badge' in df_staff.columns else df_staff.columns[-1]
        
        # Calculate Grouped Metrics
        total_registered = len(df_staff)
        tl_group = ["Team Leader", "Pro in Fireworks", "Master in Fireworks"]
        at_group = ["Assist.Technician", "Driver"]
        
        team_leaders = len(df_staff[df_staff[badge_col].isin(tl_group)])
        assist_techs = len(df_staff[df_staff[badge_col].isin(at_group)])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Registered Staff", total_registered)
        m2.metric("Total Team Leaders", team_leaders)
        m3.metric("Total Assist.Technician", assist_techs)
        
        st.divider()
        st.subheader("📋 Staff Directory")
        st.dataframe(df_staff, use_container_width=True, hide_index=True)
    else:
        st.info("No staff data found.")

elif page == "👤 Staff Profiles":
    st.title("👤 Staff Activity Search")
    search_id = st.text_input("🔍 Enter Staff SN")
    if search_id:
        person = df_staff[df_staff['SN'] == search_id.strip()]
        if not person.empty:
            st.header(f"Staff: {person.iloc[0]['Name']}")
            logs = df_events[df_events['Event ID'] == search_id.strip()]
            if not logs.empty:
                st.dataframe(logs, use_container_width=True, hide_index=True)
            else:
                st.warning("No events found for this specific Staff SN.")
        else:
            st.error("Staff SN not found.")

elif page == "🗓️ Event Logs":
    st.title("🗓️ Master Event Logs")
    if not df_events.empty:
        # Table View
        cols = ["SN", "Event ID", "Event Location", "Event Name", "Event Date", "Event Duration (Mins)", "Master Group"]
        available_cols = [c for c in cols if c in df_events.columns]
        st.dataframe(df_events[available_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No logs found.")

elif page == "🏆 Leaderboard":
    st.title("🏆 Leaderboard")
    if not df_events.empty:
        # Count events per Staff SN (Event ID)
        counts = df_events['Event ID'].value_counts().reset_index()
        counts.columns = ['SN', 'Total Events']
        
        # Bring in Names for the Table
        if not df_staff.empty:
            leaderboard = pd.merge(counts, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
            st.table(leaderboard[['Rank', 'Name', 'Total Events']].head(10))
        else:
            st.table(counts.head(10))

elif page == "➕ Add Data":
    st.title("➕ Data Management")
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📋 Register Staff")
        with st.form("staff_reg", clear_on_submit=True):
            s_sn = st.text_input("SN")
            s_rk = st.text_input("Rank")
            s_nm = st.text_input("Name")
            s_un = st.text_input("Unit")
            s_ct = st.text_input("Contact")
            s_bd = st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
            if st.form_submit_button("Save Staff"):
                sh.worksheet("Details").append_row([s_sn, s_rk, s_nm, s_un, s_ct, s_bd])
                st.cache_data.clear()
                st.success(f"Registered {s_nm}!")
                st.rerun()

    with c2:
        st.subheader("🔥 Log New Event")
        with st.form("event_log", clear_on_submit=True):
            e_sn_auto = st.text_input("Sheet SN")
            e_id = st.text_input("Staff SN (Event ID)")
            e_lc = st.text_input("Event Location")
            e_nm = st.text_input("Event Name")
            e_dt = st.date_input("Event Date")
            e_dr = st.text_input("Duration (Mins)")
            e_gr = st.selectbox("Master Group", ["New Year", "Eid", "National Day", "Other Events"])
            if st.form_submit_button("Save Event"):
                sh.worksheet("Event Details").append_row([e_sn_auto, e_id, e_lc, e_nm, str(e_dt), e_dr, e_gr])
                st.cache_data.clear()
                st.success("Event Logged!")
                st.rerun()
