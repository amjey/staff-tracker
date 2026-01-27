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

# --- 3. DATA CLEANING ENGINE ---
def load_and_scrub_data():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
        
        staff_sheet = sh.worksheet("Details").get_all_values()
        if len(staff_sheet) > 1:
            df_s = pd.DataFrame(staff_sheet[1:], columns=staff_sheet[0])
            df_s = df_s.loc[:, ~df_s.columns.duplicated()].copy()
            df_s.columns = [c.strip() for c in df_s.columns]
            df_s['SN'] = df_s['SN'].astype(str).str.strip()
            df_s = df_s[df_s['SN'] != ""].dropna(how='all')
        else:
            df_s = pd.DataFrame()
        
        event_sheet = sh.worksheet("Event Details").get_all_values()
        if len(event_sheet) > 1:
            df_e = pd.DataFrame(event_sheet[1:], columns=event_sheet[0])
            df_e = df_e.loc[:, ~df_e.columns.duplicated()].copy()
            df_e.columns = [c.strip() for c in df_e.columns]
            if 'SN' in df_e.columns:
                df_e['SN'] = df_e['SN'].astype(str).str.strip()
            
            if 'Event Duration (Mins)' in df_e.columns:
                df_e['Dur_Math'] = pd.to_numeric(df_e['Event Duration (Mins)'].astype(str).str.extract('(\d+)')[0], errors='coerce').fillna(0)
            
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

# --- 5. STRATEGIC OVERVIEW ---
if page == "📊 Strategic Overview":
    st.title("📊 Strategic Overview")
    if not df_staff.empty:
        badge_col = 'Leader Badge' if 'Leader Badge' in df_staff.columns else df_staff.columns[5]
        tl_list = ["Team Leader", "Pro in Fireworks", "Master in Fireworks"]
        at_list = ["Assist.Technician", "Driver"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Registered Staff", len(df_staff))
        c2.metric("Total Team Leaders", len(df_staff[df_staff[badge_col].isin(tl_list)]))
        c3.metric("Total Assistants", len(df_staff[df_staff[badge_col].isin(at_list)]))
        st.divider()
        if not df_events.empty and 'Master Group' in df_events.columns:
            st.subheader("Events Distribution")
            st.bar_chart(df_events['Master Group'].value_counts())

# --- 6. STAFF PROFILES ---
elif page == "👤 Staff Profiles":
    st.title("👤 Staff Registry")
    if not df_staff.empty:
        st.dataframe(df_staff, use_container_width=True, hide_index=True)
        st.divider()
        search_sn = st.text_input("🔍 Search History by Staff SN").strip()
        if search_sn:
            person = df_staff[df_staff['SN'] == search_sn]
            if not person.empty:
                st.success(f"History for: {person.iloc[0]['Name']}")
                st.dataframe(df_events[df_events['SN'] == search_sn], use_container_width=True, hide_index=True)

# --- 7. EVENT LOGS ---
elif page == "🗓️ Event Logs":
    st.title("🗓️ Event Logs")
    if not df_events.empty:
        search_loc = st.text_input("🔍 Filter by Location").strip()
        if search_loc:
            filtered = df_events[df_events['Event Location'].str.contains(search_loc, case=False, na=False)]
            for (loc, date, name, dur), group in filtered.groupby(['Event Location', 'Event Date', 'Event Name', 'Event Duration (Mins)']):
                with st.expander(f"📍 {loc} | 🗓️ {date} | 🔥 {name}"):
                    staff_details = pd.merge(group[['SN']], df_staff[['SN', 'Name', 'Rank', 'Contact']], on='SN', how='left')
                    st.dataframe(staff_details, hide_index=True, use_container_width=True)
        else:
            st.dataframe(df_events, use_container_width=True, hide_index=True)

# --- 8. LEADERBOARD ---
elif page == "🏆 Leaderboard":
    st.title("🏆 Top 5 Performers")
    if not df_events.empty:
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("🔥 Most Events")
            ev_counts = df_events['SN'].value_counts().reset_index()
            ev_counts.columns = ['SN', 'Total Events']
            st.dataframe(pd.merge(ev_counts, df_staff[['SN', 'Name', 'Rank']], on='SN').head(5), hide_index=True)
        with col_b:
            st.subheader("⏳ Most Minutes")
            dur_counts = df_events.groupby('SN')['Dur_Math'].sum().reset_index().sort_values('Dur_Math', ascending=False)
            st.dataframe(pd.merge(dur_counts, df_staff[['SN', 'Name', 'Rank']], on='SN').head(5), hide_index=True)

# --- 9. REPORTS (NEW TAB) ---
elif page == "🖨️ Reports":
    st.title("🖨️ Report Generator")
    st.write("Generate and download Excel reports for your records.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👥 Staff Registry Report")
        if st.button("Prepare Staff Excel"):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_staff.to_excel(writer, index=False, sheet_name='Staff_List')
            st.download_button(label="📥 Download Staff Excel", data=output.getvalue(), file_name="Staff_Registry.xlsx", mime="application/vnd.ms-excel")
            st.info("To save as PDF: Open the Excel and use 'Save as PDF'.")

    with col2:
        st.subheader("📍 Location Attendance Report")
        loc_choice = st.selectbox("Select Location", options=df_events['Event Location'].unique())
        if st.button("Generate Location Report"):
            loc_data = df_events[df_events['Event Location'] == loc_choice]
            report_data = pd.merge(loc_data, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                report_data.to_excel(writer, index=False, sheet_name='Location_Report')
            st.download_button(label=f"📥 Download {loc_choice} Report", data=output.getvalue(), file_name=f"Report_{loc_choice}.xlsx", mime="application/vnd.ms-excel")

# --- 10. DATA MANAGEMENT ---
elif page == "➕ Data Management":
    st.title("⚙️ Data Management")
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    t1, t2 = st.tabs(["➕ Add New", "🗑️ Delete"])
    with t1:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📋 Staff")
            with st.form("as", clear_on_submit=True):
                s_sn, s_rk, s_nm, s_un, s_ct = st.text_input("SN"), st.text_input("Rank"), st.text_input("Name"), st.text_input("Unit"), st.text_input("Contact")
                s_bd = st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
                if st.form_submit_button("Save"):
                    sh.worksheet("Details").append_row([s_sn, s_rk, s_nm, s_un, s_ct, s_bd]); st.rerun()
        with c2:
            st.subheader("🔥 Event")
            with st.form("ae", clear_on_submit=True):
                e_ref, e_sn, e_lc, e_nm = st.text_input("Ref"), st.text_input("Staff SN"), st.text_input("Location"), st.text_input("Event Name")
                e_dt, e_dr = st.date_input("Date"), st.text_input("Duration")
                e_gr = st.selectbox("Group", ["New Year", "Eid", "National Day", "Other"])
                if st.form_submit_button("Save"):
                    sh.worksheet("Event Details").append_row([e_ref, e_sn, e_lc, e_nm, str(e_dt), e_dr, e_gr]); st.rerun()
    with t2:
        st.subheader("🗑️ Delete")
        d1, d2 = st.columns(2)
        with d1:
            if not df_staff.empty:
                s_del = st.selectbox("Delete Staff", options=df_staff['SN'] + " - " + df_staff['Name'])
                if st.button("Delete Staff"):
                    idx = df_staff[df_staff['SN'] == s_del.split(" - ")[0]].index[0] + 2
                    sh.worksheet("Details").delete_rows(int(idx)); st.rerun()
        with d2:
            if not df_events.empty:
                e_del = st.selectbox("Delete Event", options=df_events.index.astype(str) + " | " + df_events['Event Location'])
                if st.button("Delete Event"):
                    sh.worksheet("Event Details").delete_rows(int(e_del.split(" | ")[0]) + 2); st.rerun()
