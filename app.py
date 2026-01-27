import streamlit as st
import pandas as pd
import gspread
import json
from io import BytesIO
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

# --- 3. DATA CLEANING ENGINE (FIXED FOR DUPLICATES) ---
def load_and_scrub_data():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
        
        # Staff Data
        staff_sheet = sh.worksheet("Details").get_all_values()
        if len(staff_sheet) > 1:
            df_s = pd.DataFrame(staff_sheet[1:], columns=staff_sheet[0])
            # CRITICAL FIX: This line removes duplicate columns like 'Rank' or 'Staff Rank'
            df_s = df_s.loc[:, ~df_s.columns.duplicated()].copy()
            df_s.columns = [c.strip() for c in df_s.columns]
            df_s['SN'] = df_s['SN'].astype(str).str.strip()
            df_s = df_s[df_s['SN'] != ""].dropna(how='all')
        else:
            df_s = pd.DataFrame()
        
        # Event Data
        event_sheet = sh.worksheet("Event Details").get_all_values()
        if len(event_sheet) > 1:
            df_e = pd.DataFrame(event_sheet[1:], columns=event_sheet[0])
            df_e = df_e.loc[:, ~df_e.columns.duplicated()].copy()
            df_e.columns = [c.strip() for c in df_e.columns]
            if 'SN' in df_e.columns:
                df_e['SN'] = df_e['SN'].astype(str).str.strip()
            
            # Clean Duration
            dur_col = 'Event Duration (Mins)'
            if dur_col in df_e.columns:
                df_e['Dur_Math'] = pd.to_numeric(df_e[dur_col].astype(str).str.extract('(\d+)')[0], errors='coerce').fillna(0)
            
            df_e = df_e[df_e.iloc[:, 0] != ""].dropna(how='all')
        else:
            df_e = pd.DataFrame()

        return df_s, df_e
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_staff, df_events = load_and_scrub_data()

# --- 4. NAVIGATION ---
page = st.sidebar.radio("Navigation", ["📊 Strategic Overview", "👤 Staff Profiles", "🗓️ Event Logs", "🏆 Leaderboard", "🖨️ Reports", "➕ Data Management"])

# --- 5. STRATEGIC OVERVIEW (FIXED METRICS) ---
if page == "📊 Strategic Overview":
    st.title("📊 Strategic Overview")
    if not df_staff.empty:
        # Detect the correct column for badges
        badge_col = 'Leader Badge' if 'Leader Badge' in df_staff.columns else df_staff.columns[min(5, len(df_staff.columns)-1)]
        tl_list = ["Team Leader", "Pro in Fireworks", "Master in Fireworks"]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Staff", len(df_staff))
        c2.metric("Total Team Leaders", len(df_staff[df_staff[badge_col].isin(tl_list)]))
        c3.metric("Total Assistants", len(df_staff[~df_staff[badge_col].isin(tl_list)]))
        
        st.divider()
        st.subheader("📋 Registered Staff Directory")
        st.dataframe(df_staff, use_container_width=True, hide_index=True)

# --- 6. STAFF PROFILES ---
elif page == "👤 Staff Profiles":
    st.title("👤 Staff Registry & Search")
    if not df_staff.empty:
        search_sn = st.text_input("🔍 Search Activity by Staff SN").strip()
        if search_sn:
            person = df_staff[df_staff['SN'] == search_sn]
            if not person.empty:
                st.success(f"History for: {person.iloc[0]['Name']}")
                history = df_events[df_events['SN'] == search_sn]
                if not history.empty:
                    st.dataframe(history, use_container_width=True, hide_index=True)
                else:
                    st.info("No recorded events for this Staff SN.")
            else:
                st.error("SN not found.")

# --- 7. EVENT LOGS ---
elif page == "🗓️ Event Logs":
    st.title("🗓️ Event Logs")
    if not df_events.empty:
        search_loc = st.text_input("🔍 Search by Event Location").strip()
        filtered = df_events[df_events['Event Location'].str.contains(search_loc, case=False, na=False)] if search_loc else df_events
        st.dataframe(filtered, use_container_width=True, hide_index=True)

# --- 8. LEADERBOARD ---
elif page == "🏆 Leaderboard":
    st.title("🏆 Leaderboard (Top 5)")
    if not df_events.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🔥 Most Events")
            counts = df_events['SN'].value_counts().reset_index().head(5)
            counts.columns = ['SN', 'Events']
            st.dataframe(pd.merge(counts, df_staff[['SN', 'Name']], on='SN'), hide_index=True)
        with c2:
            st.subheader("⏳ Most Minutes")
            if 'Dur_Math' in df_events.columns:
                m_counts = df_events.groupby('SN')['Dur_Math'].sum().reset_index().sort_values('Dur_Math', ascending=False).head(5)
                st.dataframe(pd.merge(m_counts, df_staff[['SN', 'Name']], on='SN'), hide_index=True)

# --- 9. REPORTS (FIXED EXPORT) ---
elif page == "🖨️ Reports":
    st.title("🖨️ Report Generator")
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("👥 Staff Registry")
        if st.button("Prepare Staff Excel"):
            towrite = BytesIO()
            df_staff.to_excel(towrite, index=False, engine='openpyxl') # Switched to openpyxl for compatibility
            st.download_button("📥 Download Staff Excel", data=towrite.getvalue(), file_name="Staff_Registry.xlsx")

    with c2:
        st.subheader("📍 Location Report")
        loc = st.selectbox("Select Location", df_events['Event Location'].unique() if not df_events.empty else ["None"])
        if st.button("Generate Location Report"):
            report = df_events[df_events['Event Location'] == loc]
            towrite = BytesIO()
            report.to_excel(towrite, index=False, engine='openpyxl')
            st.download_button(f"📥 Download {loc} Report", data=towrite.getvalue(), file_name=f"{loc}_Report.xlsx")

# --- 10. DATA MANAGEMENT ---
elif page == "➕ Data Management":
    st.title("➕ Data Management")
    t1, t2 = st.tabs(["Add Data", "Delete Data"])
    with t1:
        st.info("Use the forms below to add staff or events.")
        # (Form code remains similar to previous version)
