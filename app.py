import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials

# --- 1. CONNECTION ---
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

# --- 3. DATA SCRUBBING (FIXES THE "0" AND "VALUEERROR" ISSUES) ---
def load_and_fix_data():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
        
        # Load Staff
        staff_data = sh.worksheet("Details").get_all_values()
        if len(staff_data) > 1:
            df_s = pd.DataFrame(staff_data[1:], columns=staff_data[0])
            # Clean headers and remove empty rows
            df_s.columns = [c.strip() for c in df_s.columns]
            df_s = df_s[df_s['SN'] != ""].dropna(how='all')
        else:
            df_s = pd.DataFrame()
            
        # Load Events
        event_data = sh.worksheet("Event Details").get_all_values()
        if len(event_data) > 1:
            df_e = pd.DataFrame(event_data[1:], columns=event_data[0])
            df_e.columns = [c.strip() for c in df_e.columns]
            df_e = df_e[df_e['Event ID'] != ""].dropna(how='all')
        else:
            df_e = pd.DataFrame()

        return df_s, df_e
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_staff, df_events = load_and_fix_data()

# --- 4. NAVIGATION ---
page = st.sidebar.radio("Navigation", ["📊 Strategic Overview", "👤 Staff Profiles", "🗓️ Event Logs", "🏆 Leaderboard", "➕ Add Data"])

# --- 5. STRATEGIC OVERVIEW (METRICS ONLY) ---
if page == "📊 Strategic Overview":
    st.title("📊 Strategic Overview")
    
    if not df_staff.empty:
        # Grouping Logic
        # Team Leaders = Team Leader, Pro in Fireworks, Master in Fireworks
        # Assistants = Assist.Technician, Driver
        badge_col = 'Leader Badge' if 'Leader Badge' in df_staff.columns else df_staff.columns[5]
        
        tl_list = ["Team Leader", "Pro in Fireworks", "Master in Fireworks"]
        at_list = ["Assist.Technician", "Driver"]
        
        count_tl = len(df_staff[df_staff[badge_col].isin(tl_list)])
        count_at = len(df_staff[df_staff[badge_col].isin(at_list)])
        
        # Display Only the 3 Metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Registered Staff", len(df_staff))
        c2.metric("Total Team Leaders", count_tl)
        c3.metric("Total Assist.Technician", count_at)
        
        st.divider()
        
        # Event Chart
        if not df_events.empty and 'Master Group' in df_events.columns:
            st.subheader("Events Distribution")
            st.bar_chart(df_events['Master Group'].value_counts())
    else:
        st.warning("No staff found. Please check your Google Sheet.")

# --- 6. STAFF PROFILES (TABLE MOVED HERE) ---
elif page == "👤 Staff Profiles":
    st.title("👤 Staff Registry & Search")
    
    if not df_staff.empty:
        # SHOW REGISTRY HERE
        st.subheader("All Registered Staff")
        st.dataframe(df_staff, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # SEARCH ACTIVITY
        search_id = st.text_input("🔍 Search Activity by Staff SN")
        if search_id:
            person = df_staff[df_staff['SN'] == search_id.strip()]
            if not person.empty:
                st.success(f"History for: {person.iloc[0]['Name']}")
                logs = df_events[df_events['Event ID'] == search_id.strip()]
                if not logs.empty:
                    st.dataframe(logs, use_container_width=True, hide_index=True)
                else:
                    st.info("No events recorded for this SN.")
            else:
                st.error("Staff SN not found.")

# --- 7. REMAINING TABS (UNCHANGED) ---
elif page == "🗓️ Event Logs":
    st.title("🗓️ Event Logs")
    st.dataframe(df_events, use_container_width=True, hide_index=True)

elif page == "🏆 Leaderboard":
    st.title("🏆 Leaderboard")
    if not df_events.empty:
        counts = df_events['Event ID'].value_counts().reset_index()
        counts.columns = ['SN', 'Events']
        if not df_staff.empty:
            merged = pd.merge(counts, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
            st.table(merged[['Rank', 'Name', 'Events']].head(15))

elif page == "➕ Add Data":
    st.title("➕ Data Management")
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)

    c1, c2 = st.columns(2)
    with c1:
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
                st.rerun()

    with c2:
        st.subheader("🔥 Log Event")
        with st.form("f2", clear_on_submit=True):
            e_sn = st.text_input("Sheet SN")
            e_id = st.text_input("Staff SN")
            e_lc = st.text_input("Location")
            e_nm = st.text_input("Event Name")
            e_dt = st.date_input("Date")
            e_dr = st.text_input("Duration")
            e_gr = st.selectbox("Group", ["New Year", "Eid", "National Day", "Other"])
            if st.form_submit_button("Save Event"):
                sh.worksheet("Event Details").append_row([e_sn, e_id, e_lc, e_nm, str(e_dt), e_dr, e_gr])
                st.rerun()
