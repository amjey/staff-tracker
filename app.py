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
        # Reads the triple-quoted JSON string from your Streamlit Secrets [gcp_service_account]
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
@st.cache_data(ttl=5)
def load_data_via_api():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
        
        def get_df(worksheet_name):
            data = sh.worksheet(worksheet_name).get_all_values()
            if not data: return pd.DataFrame()
            headers = [h.strip() for h in data[0]]
            df = pd.DataFrame(data[1:], columns=headers)
            return df

        df_staff = get_df("Details")
        df_events = get_df("Event Details")

        # Clean SN/ID for matching
        if not df_events.empty:
            # We use 'Event ID' as the staff identifier based on your screenshot
            df_events['Event ID'] = df_events['Event ID'].astype(str).apply(lambda x: x.split('.')[0].strip())
        if not df_staff.empty:
            df_staff['SN'] = df_staff['SN'].astype(str).apply(lambda x: x.split('.')[0].strip())

        return df_staff, df_events
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_staff, df_events = load_data_via_api()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("Staff & Events")
    page = st.radio("Go to:", ["📊 Dashboard", "👤 Staff Profiles", "🗓️ Event Logs", "🏆 Leaderboard", "➕ Add Data"])
    if st.button("🔄 Sync with Sheet"):
        st.cache_data.clear()
        st.rerun()

# --- 5. PAGE LOGIC ---

if page == "🗓️ Event Logs":
    st.title("🗓️ Event Logs")
    if not df_events.empty:
        # Match your screenshot columns exactly
        display_cols = ["Event ID", "Event Location", "Event Name", "Event Date", "Event Duration (Mins)", "Master Group"]
        st.dataframe(df_events[display_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No events found.")

elif page == "➕ Add Data":
    st.title("➕ Data Management")
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📋 New Staff")
        with st.form("staff_f", clear_on_submit=True):
            f_sn = st.text_input("SN")
            f_rk = st.text_input("Rank")
            f_nm = st.text_input("Name")
            f_un = st.text_input("Unit")
            f_ct = st.text_input("Contact")
            f_bd = st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
            if st.form_submit_button("Save Staff"):
                sh.worksheet("Details").append_row([f_sn, f_rk, f_nm, f_un, f_ct, f_bd])
                st.cache_data.clear()
                st.success("Staff saved!")
                st.rerun()

    with col_b:
        st.subheader("🔥 Log New Event")
        with st.form("event_f", clear_on_submit=True):
            e_id = st.text_input("Staff SN (Event ID)")
            e_lc = st.text_input("Event Location")
            e_nm = st.text_input("Event Name")
            e_dt = st.date_input("Event Date")
            e_dr = st.text_input("Duration (e.g. 120 Mins)")
            e_gr = st.selectbox("Master Group", ["New Year", "Eid", "National Day", "Other Events"])
            
            if st.form_submit_button("Save Event"):
                # CRITICAL: This order matches your headers: 
                # ID, Location, Name, Date, Duration, Group
                new_row = [e_id, e_lc, e_nm, str(e_dt), e_dr, e_gr]
                sh.worksheet("Event Details").append_row(new_row)
                st.cache_data.clear()
                st.success("Event Aligned & Saved!")
                st.rerun()

elif page == "📊 Dashboard":
    st.title("📊 Overview")
    if not df_staff.empty:
        st.metric("Total Registered Staff", len(df_staff))
        st.divider()
        if 'Master Group' in df_events.columns:
            st.bar_chart(df_events['Master Group'].value_counts())

elif page == "👤 Staff Profiles":
    st.title("👤 Search Profiles")
    sel_sn = st.text_input("Enter SN to view history")
    if sel_sn:
        staff_data = df_staff[df_staff['SN'] == sel_sn.strip()]
        if not staff_data.empty:
            st.header(staff_data.iloc[0]['Name'])
            # Filter events where Event ID matches Staff SN
            history = df_events[df_events['Event ID'] == sel_sn.strip()]
            st.dataframe(history, use_container_width=True, hide_index=True)

elif page == "🏆 Leaderboard":
    st.title("🏆 Leaderboard")
    if not df_events.empty:
        counts = df_events['Event ID'].value_counts().head(5).reset_index()
        counts.columns = ['SN', 'Events']
        st.table(counts)
