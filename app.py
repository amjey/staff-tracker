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
        creds_info = json.loads(st.secrets["gcp_service_account"]["service_account_info"])
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Secret Configuration Error: {e}")
        st.stop()

# --- 2. GLOBAL CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
st.set_page_config(page_title="Staff Management Pro", layout="wide")

# --- 3. DATA LOADING (FORGIVING VERSION) ---
@st.cache_data(ttl=5)
def load_data_via_api():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
        
        # Helper to convert sheet values to DataFrame safely
        def get_df(worksheet_name):
            data = sh.worksheet(worksheet_name).get_all_values()
            if not data:
                return pd.DataFrame()
            # Use the first row as headers, and handle duplicates/empty headers
            df = pd.DataFrame(data[1:], columns=data[0])
            # Remove any columns that have empty names
            df = df.loc[:, df.columns != '']
            return df

        df_staff = get_df("Details")
        df_events = get_df("Event Details")

        if df_staff.empty or df_events.empty:
            return df_staff, df_events, "", "", ""

        # Clean column names (strip spaces)
        df_staff.columns = df_staff.columns.str.strip()
        df_events.columns = df_events.columns.str.strip()

        # Data Cleaning
        clean_val = lambda x: str(x).split('.')[0].strip()
        df_staff['SN'] = df_staff['SN'].apply(clean_val)
        df_events['SN'] = df_events['SN'].apply(clean_val)
        
        if 'Contact' in df_staff.columns:
            df_staff['Contact'] = df_staff['Contact'].astype(str).apply(lambda x: x.split('.')[0])

        # Column Discovery
        dur_col = next((c for c in df_events.columns if 'duration' in c.lower()), "Duration")
        loc_col = next((c for c in df_events.columns if 'location' in c.lower()), "Location")
        cat_col = next((c for c in df_events.columns if 'group' in c.lower() or 'category' in c.lower()), "Master Group")

        df_events[dur_col] = pd.to_numeric(df_events[dur_col], errors='coerce').fillna(0)

        # Mapping for Dashboard
        def get_cat(b):
            b = str(b).strip()
            if b in ["Assist.Technician", "Driver"]: return "AT"
            if b in ["Master in Fireworks", "Pro in Fireworks", "Team Leader"]: return "TL"
            return "Other"
        df_staff['Category_Group'] = df_staff['Leader Badge'].apply(get_cat)

        return df_staff, df_events, dur_col, loc_col, cat_col
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), "", "", ""

df_staff, df_events, dur_col, loc_col, cat_col = load_data_via_api()

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("Main Menu")
    page = st.radio("Go to:", ["📊 Dashboard", "👤 Staff Details", "🗓️ Event Logs", "🏆 Leaderboard", "➕ Add Data"])
    st.divider()
    if st.button("🔄 Sync with Sheet"):
        st.cache_data.clear()
        st.rerun()

# --- 5. PAGE LOGIC ---
if page == "➕ Add Data":
    st.title("➕ Data Management")
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)

    ca, cb = st.columns(2)
    with ca:
        st.subheader("📋 New Staff")
        with st.form("staff_f", clear_on_submit=True):
            f_sn = st.text_input("SN")
            f_rk = st.text_input("Rank")
            f_nm = st.text_input("Name")
            f_un = st.text_input("Unit")
            f_ct = st.text_input("Contact")
            f_bd = st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
            if st.form_submit_button("Save Staff Member"):
                sh.worksheet("Details").append_row([f_sn, f_rk, f_nm, f_un, f_ct, f_bd])
                st.cache_data.clear()
                st.rerun()

    with cb:
        st.subheader("🔥 New Event")
        with st.form("event_f", clear_on_submit=True):
            e_sn = st.text_input("Staff SN")
            e_nm = st.text_input("Event Name")
            e_lc = st.text_input("Location")
            e_dt = st.date_input("Date")
            e_dr = st.number_input("Duration (Mins)", min_value=1)
            e_gr = st.selectbox("Group", ["New Year", "Eid Celebrations", "National Day", "Other"])
            if st.form_submit_button("Save Event Data"):
                sh.worksheet("Event Details").append_row([e_sn, e_nm, e_lc, str(e_dt), e_dr, e_gr])
                st.cache_data.clear()
                st.rerun()

    st.divider()
    st.subheader("👀 Last 5 Entries (Live View)")
    st.dataframe(df_events.tail(5), use_container_width=True, hide_index=True)

# (Dashboard, Staff Details, Event Logs, Leaderboard logic remains same as previous version)
elif page == "📊 Dashboard":
    st.title("📊 Strategic Overview")
    if not df_staff.empty:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Registered", len(df_staff))
        m2.metric("Team Leaders", len(df_staff[df_staff['Category_Group'] == "TL"]))
        m3.metric("Assist. Technicians", len(df_staff[df_staff['Category_Group'] == "AT"]))
        st.bar_chart(df_events[cat_col].value_counts())

elif page == "👤 Staff Details":
    st.title("👤 Staff Profiles")
    search_sn = st.text_input("🔍 Search SN")
    if search_sn:
        res = df_staff[df_staff['SN'] == search_sn.strip()]
        if not res.empty:
            p = res.iloc[0]
            st.header(f"Profile: {p['Name']}")
            hist = df_events[df_events['SN'] == p['SN']]
            st.dataframe(hist, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df_staff, use_container_width=True, hide_index=True)

elif page == "🗓️ Event Logs":
    st.title("🗓️ Event Logs")
    st.dataframe(df_events, use_container_width=True, hide_index=True)

elif page == "🏆 Leaderboard":
    st.title("🏆 Leaderboard")
    top_e = df_events['SN'].value_counts().head(5).reset_index()
    top_e.columns = ['SN', 'Events']
    merged = pd.merge(top_e, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.dataframe(merged, hide_index=True)
