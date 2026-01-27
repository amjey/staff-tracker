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

# --- 3. DATA LOADING (WITH AUTO-CLEANING) ---
def load_live_data():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
        
        # Load and Clean Staff Data
        staff_raw = sh.worksheet("Details").get_all_values()
        if len(staff_raw) > 1:
            df_s = pd.DataFrame(staff_raw[1:], columns=staff_raw[0])
            # REMOVE COMPLETELY EMPTY ROWS (Prevents ValueError)
            df_s = df_s.replace('', pd.NA).dropna(how='all').fillna('')
        else:
            df_s = pd.DataFrame()
        
        # Load and Clean Event Data
        event_raw = sh.worksheet("Event Details").get_all_values()
        if len(event_raw) > 1:
            df_e = pd.DataFrame(event_raw[1:], columns=event_raw[0])
            df_e = df_e.replace('', pd.NA).dropna(how='all').fillna('')
        else:
            df_e = pd.DataFrame()

        # Clean IDs for matching
        clean_fn = lambda x: str(x).split('.')[0].strip()
        if not df_s.empty and 'SN' in df_s.columns:
            df_s['SN'] = df_s['SN'].apply(clean_fn)
        if not df_e.empty and 'Event ID' in df_e.columns:
            df_e['Event ID'] = df_e['Event ID'].apply(clean_fn)

        return df_s, df_e
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_staff, df_events = load_live_data()

# --- 4. NAVIGATION & FORCE REFRESH ---
with st.sidebar:
    st.title("Main Menu")
    page = st.radio("Go to:", ["📊 Dashboard", "👤 Staff Profiles", "🗓️ Event Logs", "🏆 Leaderboard", "➕ Add Data"])
    if st.button("🔄 Force Data Refresh"):
        st.cache_data.clear()
        st.rerun()

# --- 5. DASHBOARD ---
if page == "📊 Dashboard":
    st.title("📊 Strategic Overview")
    if not df_staff.empty:
        # Metrics Grouping Logic
        tl_group = ["Team Leader", "Pro in Fireworks", "Master in Fireworks"]
        at_group = ["Assist.Technician", "Driver"]
        
        # Determine Badge column (usually last)
        badge_col = df_staff.columns[-1]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Registered Staff", len(df_staff))
        c2.metric("Total Team Leaders", len(df_staff[df_staff[badge_col].isin(tl_group)]))
        c3.metric("Total Assist.Technician", len(df_staff[df_staff[badge_col].isin(at_group)]))
        
        st.subheader("📋 Registered Staff Directory")
        # Using a list to convert to clean table format
        st.dataframe(df_staff, use_container_width=True, hide_index=True)
    else:
        st.warning("No data found in 'Details' sheet.")

# --- 6. PROFILES ---
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
                st.info("No activity logs for this user.")
        else:
            st.error("SN not found.")

# --- 7. EVENT LOGS ---
elif page == "🗓️ Event Logs":
    st.title("🗓️ Master Event Logs")
    if not df_events.empty:
        # Match your 7-column spreadsheet
        cols = ["SN", "Event ID", "Event Location", "Event Name", "Event Date", "Event Duration (Mins)", "Master Group"]
        available = [c for c in cols if c in df_events.columns]
        st.dataframe(df_events[available], use_container_width=True, hide_index=True)

# --- 8. LEADERBOARD ---
elif page == "🏆 Leaderboard":
    st.title("🏆 Top Performers")
    if not df_events.empty:
        counts = df_events['Event ID'].value_counts().reset_index()
        counts.columns = ['SN', 'Total Events']
        if not df_staff.empty:
            lb = pd.merge(counts, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
            st.table(lb[['Rank', 'Name', 'Total Events']].head(10))

# --- 9. ADD DATA (LOCKED FORMS) ---
elif page == "➕ Add Data":
    st.title("➕ Data Management")
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📋 Register Staff")
        with st.form("f1", clear_on_submit=True):
            s_sn = st.text_input("SN")
            s_rk = st.text_input("Rank")
            s_nm = st.text_input("Name")
            s_un = st.text_input("Unit")
            s_ct = st.text_input("Contact")
            s_bd = st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
            if st.form_submit_button("Save Staff"):
                sh.worksheet("Details").append_row([s_sn, s_rk, s_nm, s_un, s_ct, s_bd])
                st.success("Staff Saved!")
                st.rerun()

    with col2:
        st.subheader("🔥 Log New Event")
        with st.form("f2", clear_on_submit=True):
            e_sn = st.text_input("Sheet SN")
            e_id = st.text_input("Staff SN (Event ID)")
            e_lc = st.text_input("Event Location")
            e_nm = st.text_input("Event Name")
            e_dt = st.date_input("Event Date")
            e_dr = st.text_input("Duration (Mins)")
            e_gr = st.selectbox("Master Group", ["New Year", "Eid", "National Day", "Other Events"])
            if st.form_submit_button("Save Event"):
                sh.worksheet("Event Details").append_row([e_sn, e_id, e_lc, e_nm, str(e_dt), e_dr, e_gr])
                st.success("Event Logged!")
                st.rerun()
