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
            # Remove ghost columns
            df = df.loc[:, df.columns != '']
            return df

        df_staff = get_df("Details")
        df_events = get_df("Event Details")

        if df_staff.empty or df_events.empty:
            return df_staff, df_events

        # Clean SN
        clean_val = lambda x: str(x).split('.')[0].strip()
        df_staff['SN'] = df_staff['SN'].apply(clean_val)
        df_events['SN'] = df_events['SN'].apply(clean_val)
        
        # Clean Contact
        if 'Contact' in df_staff.columns:
            df_staff['Contact'] = df_staff['Contact'].astype(str).apply(lambda x: x.split('.')[0])

        # Convert Duration to Numeric
        if 'Duration' in df_events.columns:
            df_events['Duration'] = pd.to_numeric(df_events['Duration'], errors='coerce').fillna(0)

        return df_staff, df_events
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_staff, df_events = load_data_via_api()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("Main Menu")
    page = st.radio("Go to:", ["📊 Dashboard", "👤 Staff Details", "🗓️ Event Logs", "🏆 Leaderboard", "➕ Add Data"])
    if st.button("🔄 Sync with Sheet"):
        st.cache_data.clear()
        st.rerun()

# --- 5. PAGE LOGIC ---

if page == "📊 Dashboard":
    st.title("📊 Strategic Overview")
    if not df_staff.empty:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Staff", len(df_staff))
        if 'Leader Badge' in df_staff.columns:
            tl_count = len(df_staff[df_staff['Leader Badge'].str.contains("Team Leader|Master|Pro", na=False)])
            at_count = len(df_staff[df_staff['Leader Badge'].str.contains("Assist|Driver", na=False)])
            m2.metric("Leaders/Pros", tl_count)
            m3.metric("Assistants/Drivers", at_count)
        
        st.divider()
        if 'Master Group' in df_events.columns:
            st.subheader("Event Distribution")
            st.bar_chart(df_events['Master Group'].value_counts())

elif page == "👤 Staff Details":
    st.title("👤 Staff Profiles")
    search_sn = st.text_input("🔍 Search by SN")
    if search_sn:
        res = df_staff[df_staff['SN'] == search_sn.strip()]
        if not res.empty:
            p = res.iloc[0]
            st.header(f"Profile: {p['Name']}")
            hist = df_events[df_events['SN'] == p['SN']]
            c1, c2 = st.columns(2)
            c1.metric("Total Events", len(hist))
            if 'Duration' in hist.columns:
                c2.metric("Total Mins", f"{int(hist['Duration'].sum())}")
            st.dataframe(hist, use_container_width=True, hide_index=True)
        else: st.warning("Staff SN not found.")
    else:
        st.dataframe(df_staff, use_container_width=True, hide_index=True)

elif page == "🗓️ Event Logs":
    st.title("🗓️ Event Logs")
    # Forces column order for display to prevent Date/Name confusion
    cols_to_show = ["SN", "Event Name", "Location", "Date", "Duration", "Master Group"]
    existing_cols = [c for c in cols_to_show if c in df_events.columns]
    st.dataframe(df_events[existing_cols], use_container_width=True, hide_index=True)

elif page == "🏆 Leaderboard":
    st.title("🏆 Leaderboard")
    if not df_events.empty:
        top_e = df_events['SN'].value_counts().head(5).reset_index()
        top_e.columns = ['SN', 'Events']
        merged = pd.merge(top_e, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
        st.table(merged[['Rank', 'Name', 'Events']])

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
        st.subheader("🔥 New Event")
        with st.form("event_f", clear_on_submit=True):
            e_sn = st.text_input("Staff SN")
            e_nm = st.text_input("Event Name")
            e_lc = st.text_input("Location")
            e_dt = st.date_input("Date")
            e_dr = st.number_input("Duration (Mins)", min_value=1)
            e_gr = st.selectbox("Group", ["New Year", "Eid Celebrations", "National Day", "Other"])
            if st.form_submit_button("Save Event"):
                # Append strictly in this order: SN, Event Name, Location, Date, Duration, Master Group
                sh.worksheet("Event Details").append_row([e_sn, e_nm, e_lc, str(e_dt), e_dr, e_gr])
                st.cache_data.clear()
                st.success("Event logged!")
                st.rerun()
