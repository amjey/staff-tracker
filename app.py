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

# --- 3. DATA LOADING (FIXES DUPLICATES & MATCHING) ---
def load_and_scrub_data():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
        
        # --- Process Staff ---
        staff_data = sh.worksheet("Details").get_all_values()
        if len(staff_data) > 1:
            df_s = pd.DataFrame(staff_data[1:], columns=staff_data[0])
            # FIX: Remove duplicate columns that cause the ValueError
            df_s = df_s.loc[:, ~df_s.columns.duplicated()].copy()
            df_s.columns = [c.strip() for c in df_s.columns]
            # Ensure SN is a clean string for matching
            df_s['SN'] = df_s['SN'].astype(str).str.strip()
        else:
            df_s = pd.DataFrame()
            
        # --- Process Events ---
        event_data = sh.worksheet("Event Details").get_all_values()
        if len(event_data) > 1:
            df_e = pd.DataFrame(event_data[1:], columns=event_data[0])
            # FIX: Remove duplicate columns
            df_e = df_e.loc[:, ~df_e.columns.duplicated()].copy()
            df_e.columns = [c.strip() for c in df_e.columns]
            # Ensure Event ID is a clean string for matching
            df_e['Event ID'] = df_e['Event ID'].astype(str).str.strip()
        else:
            df_e = pd.DataFrame()

        return df_s, df_e
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_staff, df_events = load_and_scrub_data()

# --- 4. NAVIGATION ---
page = st.sidebar.radio("Navigation", ["📊 Strategic Overview", "👤 Staff Profiles", "🗓️ Event Logs", "🏆 Leaderboard", "➕ Add Data"])

# --- 5. DASHBOARD ---
if page == "📊 Strategic Overview":
    st.title("📊 Strategic Overview")
    if not df_staff.empty:
        # Categorization logic
        tl_list = ["Team Leader", "Pro in Fireworks", "Master in Fireworks"]
        at_list = ["Assist.Technician", "Driver"]
        badge_col = 'Leader Badge' if 'Leader Badge' in df_staff.columns else df_staff.columns[5]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Staff", len(df_staff))
        c2.metric("Total Team Leaders", len(df_staff[df_staff[badge_col].isin(tl_list)]))
        c3.metric("Total Assistants", len(df_staff[df_staff[badge_col].isin(at_list)]))
        
        st.divider()
        if not df_events.empty and 'Master Group' in df_events.columns:
            st.subheader("Events Distribution")
            st.bar_chart(df_events['Master Group'].value_counts())

# --- 6. PROFILES (Registry + Fixed Search) ---
elif page == "👤 Staff Profiles":
    st.title("👤 Staff Profiles")
    if not df_staff.empty:
        st.subheader("All Registered Staff")
        st.dataframe(df_staff, use_container_width=True, hide_index=True)
        st.divider()
        
        search_id = st.text_input("🔍 Search Activity by Staff SN").strip()
        if search_id:
            person = df_staff[df_staff['SN'] == search_id]
            if not person.empty:
                st.success(f"History for: {person.iloc[0]['Name']}")
                # MATCHING FIX: Ensure we search for the ID as a clean string
                logs = df_events[df_events['Event ID'] == search_id]
                if not logs.empty:
                    st.dataframe(logs, use_container_width=True, hide_index=True)
                else:
                    st.warning(f"No events found in 'Event Details' for SN: {search_id}")
            else:
                st.error("SN Not Found in Registry.")

# --- 7. EVENT LOGS ---
elif page == "🗓️ Event Logs":
    st.title("🗓️ Event Logs")
    st.dataframe(df_events, use_container_width=True, hide_index=True)

# --- 8. LEADERBOARD ---
elif page == "🏆 Leaderboard":
    st.title("🏆 Leaderboard")
    if not df_events.empty:
        counts = df_events['Event ID'].value_counts().reset_index()
        counts.columns = ['SN', 'Events']
        if not df_staff.empty:
            merged = pd.merge(counts, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
            st.table(merged[['Rank', 'Name', 'Events']].head(15))

# --- 9. ADD DATA ---
elif page == "➕ Add Data":
    st.title("➕ Data Entry")
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)

    ca, cb = st.columns(2)
    with ca:
        st.subheader("📋 Register Staff")
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
        st.subheader("🔥 Log Event")
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
