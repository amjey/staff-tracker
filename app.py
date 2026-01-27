import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials

# --- 1. CONNECTION (REBOOTED) ---
@st.cache_resource
def connection_provider_v3():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_info = json.loads(st.secrets["gcp_service_account"]["service_account_info"])
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Credentials Error: {e}")
        st.stop()

# --- 2. CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
st.set_page_config(page_title="Staff Management Pro", layout="wide")

# --- 3. DATA PULL (CACHING REMOVED COMPLETELY) ---
def fetch_raw_data_now():
    try:
        client = connection_provider_v3()
        sheet = client.open_by_key(SHEET_ID)
        
        # Pull Staff
        s_data = sheet.worksheet("Details").get_all_values()
        if len(s_data) > 1:
            df_s = pd.DataFrame(s_data[1:], columns=s_data[0])
            df_s = df_s.loc[:, ~df_s.columns.duplicated()].copy() # Remove duplicate columns
            df_s = df_s[df_s.iloc[:, 0] != ""].reset_index(drop=True) # Remove empty rows
        else:
            df_s = pd.DataFrame()
            
        # Pull Events
        e_data = sheet.worksheet("Event Details").get_all_values()
        if len(e_data) > 1:
            df_e = pd.DataFrame(e_data[1:], columns=e_data[0])
            df_e = df_e.loc[:, ~df_e.columns.duplicated()].copy()
            df_e = df_e[df_e.iloc[:, 0] != ""].reset_index(drop=True)
        else:
            df_e = pd.DataFrame()

        # Simple ID Cleaning
        if not df_s.empty: df_s['SN'] = df_s['SN'].astype(str).str.strip()
        if not df_e.empty: df_e['Event ID'] = df_e['Event ID'].astype(str).str.strip()

        return df_s, df_e
    except Exception as e:
        st.error(f"Fetch Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

# Load data at start of script
df_staff, df_events = fetch_raw_data_now()

# --- 4. NAVIGATION ---
page = st.sidebar.radio("Navigation", ["📊 Dashboard", "👤 Staff Profiles", "🗓️ Event Logs", "🏆 Leaderboard", "➕ Add Data"])

# --- 5. DASHBOARD (TABLE INCLUDED) ---
if page == "📊 Dashboard":
    st.title("📊 Strategic Overview")
    if not df_staff.empty:
        # Categorization logic
        tl_list = ["Team Leader", "Pro in Fireworks", "Master in Fireworks"]
        at_list = ["Assist.Technician", "Driver"]
        
        # Check last column for badge (usually 'Leader Badge')
        badge_col = df_staff.columns[-1]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Staff", len(df_staff))
        c2.metric("Total Team Leaders", len(df_staff[df_staff[badge_col].isin(tl_list)]))
        c3.metric("Total Assistants", len(df_staff[df_staff[badge_col].isin(at_list)]))
        
        st.divider()
        st.subheader("📋 Registered Staff Directory")
        st.table(df_staff) # Using st.table to force it to show every row
    else:
        st.warning("No staff found in Google Sheets.")

# --- 6. PROFILES ---
elif page == "👤 Staff Profiles":
    st.title("👤 Staff Activity Search")
    sid = st.text_input("🔍 Enter Staff SN")
    if sid:
        p = df_staff[df_staff['SN'] == sid.strip()]
        if not p.empty:
            st.header(f"Profile: {p.iloc[0]['Name']}")
            l = df_events[df_events['Event ID'] == sid.strip()]
            st.dataframe(l, use_container_width=True, hide_index=True)
        else:
            st.error("SN Not Found")

# --- 7. EVENT LOGS ---
elif page == "🗓️ Event Logs":
    st.title("🗓️ Event Logs")
    if not df_events.empty:
        st.dataframe(df_events, use_container_width=True, hide_index=True)

# --- 8. LEADERBOARD ---
elif page == "🏆 Leaderboard":
    st.title("🏆 Leaderboard")
    if not df_events.empty:
        cnts = df_events['Event ID'].value_counts().reset_index()
        cnts.columns = ['SN', 'Events']
        if not df_staff.empty:
            m = pd.merge(cnts, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
            st.table(m[['Rank', 'Name', 'Events']].head(10))

# --- 9. ADD DATA (FORMS LOCKED) ---
elif page == "➕ Add Data":
    st.title("➕ Data Entry")
    client = connection_provider_v3()
    sh = client.open_by_key(SHEET_ID)

    ca, cb = st.columns(2)
    with ca:
        st.subheader("📋 Staff Registration")
        with st.form("staff_f", clear_on_submit=True):
            s_sn = st.text_input("SN")
            s_rk = st.text_input("Rank")
            s_nm = st.text_input("Name")
            s_un = st.text_input("Unit")
            s_ct = st.text_input("Contact")
            s_bd = st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
            if st.form_submit_button("Save Staff"):
                sh.worksheet("Details").append_row([s_sn, s_rk, s_nm, s_un, s_ct, s_bd])
                st.rerun()

    with cb:
        st.subheader("🔥 Event Logging")
        with st.form("event_f", clear_on_submit=True):
            e_sn = st.text_input("Sheet SN")
            e_id = st.text_input("Staff SN (Event ID)")
            e_lc = st.text_input("Location")
            e_nm = st.text_input("Event Name")
            e_dt = st.date_input("Date")
            e_dr = st.text_input("Duration")
            e_gr = st.selectbox("Group", ["New Year", "Eid", "National Day", "Other"])
            if st.form_submit_button("Save Event"):
                sh.worksheet("Event Details").append_row([e_sn, e_id, e_lc, e_nm, str(e_dt), e_dr, e_gr])
                st.rerun()
