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

# --- 3. THE "BULLETPROOF" DATA ENGINE ---
def load_and_scrub_data():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
        
        def clean_sheet(sheet_name):
            raw_data = sh.worksheet(sheet_name).get_all_values()
            if len(raw_data) <= 1: return pd.DataFrame()
            
            # Get headers and handle duplicates immediately
            headers = [h.strip() if h.strip() else f"Empty_{i}" for i, h in enumerate(raw_data[0])]
            
            # Rebuild headers to ensure NO duplicates
            final_headers = []
            counts = {}
            for h in headers:
                if h in counts:
                    counts[h] += 1
                    final_headers.append(f"{h}_{counts[h]}")
                else:
                    counts[h] = 0
                    final_headers.append(h)
            
            df = pd.DataFrame(raw_data[1:], columns=final_headers)
            # Remove any entirely empty rows or columns
            df = df.dropna(how='all').loc[:, (df != "").any(axis=0)]
            return df

        df_s = clean_sheet("Details")
        df_e = clean_sheet("Event Details")

        # Normalize the SN column for matching
        if not df_s.empty: df_s['SN'] = df_s['SN'].astype(str).str.strip()
        if not df_e.empty: 
            # Ensure the SN column exists in Event Details
            if 'SN' in df_e.columns:
                df_e['SN'] = df_e['SN'].astype(str).str.strip()
            # Math for Duration
            dur_col = 'Event Duration (Mins)'
            if dur_col in df_e.columns:
                df_e['Dur_Math'] = pd.to_numeric(df_e[dur_col].astype(str).str.extract('(\d+)')[0], errors='coerce').fillna(0)

        return df_s, df_e
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_staff, df_events = load_and_scrub_data()

# --- 4. NAVIGATION ---
page = st.sidebar.radio("Navigation", ["📊 Strategic Overview", "👤 Staff Profiles", "🗓️ Event Logs", "🏆 Leaderboard", "🖨️ Reports", "➕ Data Management"])

# --- 5. STRATEGIC OVERVIEW ---
if page == "📊 Strategic Overview":
    st.title("📊 Strategic Overview")
    if not df_staff.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Staff", len(df_staff))
        
        # Flexibly find columns even if they were renamed by the cleaner
        badge_col = next((c for c in df_staff.columns if "Badge" in c), df_staff.columns[min(5, len(df_staff.columns)-1)])
        tl_list = ["Team Leader", "Pro in Fireworks", "Master in Fireworks"]
        
        c2.metric("Team Leaders", len(df_staff[df_staff[badge_col].isin(tl_list)]))
        c3.metric("Assistants", len(df_staff) - len(df_staff[df_staff[badge_col].isin(tl_list)]))
        
        st.divider()
        st.subheader("📋 Registered Staff Directory")
        st.dataframe(df_staff, use_container_width=True, hide_index=True)

# --- 6. STAFF PROFILES ---
elif page == "👤 Staff Profiles":
    st.title("👤 Staff Registry & Search")
    if not df_staff.empty:
        search_sn = st.text_input("🔍 Enter Staff SN to view History").strip()
        if search_sn:
            person = df_staff[df_staff['SN'] == search_sn]
            if not person.empty:
                st.success(f"History for: {person.iloc[0]['Name']}")
                history = df_events[df_events['SN'] == search_sn] if 'SN' in df_events.columns else pd.DataFrame()
                if not history.empty:
                    st.dataframe(history, use_container_width=True, hide_index=True)
                else:
                    st.info("No recorded events for this SN.")
            else:
                st.error("SN not found.")

# --- 7. EVENT LOGS ---
elif page == "🗓️ Event Logs":
    st.title("🗓️ Event Logs")
    if not df_events.empty:
        search_loc = st.text_input("🔍 Search by Location").strip()
        filtered = df_events[df_events['Event Location'].str.contains(search_loc, case=False, na=False)] if search_loc and 'Event Location' in df_events.columns else df_events
        st.dataframe(filtered, use_container_width=True, hide_index=True)

# --- 8. LEADERBOARD ---
elif page == "🏆 Leaderboard":
    st.title("🏆 Leaderboard (Top 5)")
    if not df_events.empty and 'SN' in df_events.columns:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🔥 Most Events")
            counts = df_events['SN'].value_counts().reset_index().head(5)
            counts.columns = ['SN', 'Events']
            st.dataframe(pd.merge(counts, df_staff[['SN', 'Name']], on='SN', how='left'), hide_index=True)
        with c2:
            st.subheader("⏳ Most Minutes")
            if 'Dur_Math' in df_events.columns:
                m_counts = df_events.groupby('SN')['Dur_Math'].sum().reset_index().sort_values('Dur_Math', ascending=False).head(5)
                st.dataframe(pd.merge(m_counts, df_staff[['SN', 'Name']], on='SN', how='left'), hide_index=True)

# --- 9. REPORTS ---
elif page == "🖨️ Reports":
    st.title("🖨️ Report Generator")
    c1, col2 = st.columns(2)
    with c1:
        if st.button("Download Staff Excel"):
            towrite = BytesIO()
            df_staff.to_excel(towrite, index=False, engine='openpyxl')
            st.download_button("📥 Save Staff.xlsx", data=towrite.getvalue(), file_name="Staff_Registry.xlsx")
    with col2:
        if not df_events.empty and 'Event Location' in df_events.columns:
            loc = st.selectbox("Location Report", df_events['Event Location'].unique())
            if st.button(f"Download {loc} Report"):
                report = df_events[df_events['Event Location'] == loc]
                towrite = BytesIO()
                report.to_excel(towrite, index=False, engine='openpyxl')
                st.download_button("📥 Save Report.xlsx", data=towrite.getvalue(), file_name=f"{loc}_Report.xlsx")

# --- 10. DATA MANAGEMENT ---
elif page == "➕ Data Management":
    st.title("➕ Data Management")
    t1, t2 = st.tabs(["Add", "Delete"])
    with t1:
        st.write("Use form to add new data.")
    with t2:
        st.write("Use dropdown to remove data.")
