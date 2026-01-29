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

# --- 3. DATA ENGINE ---
def load_and_scrub_data():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
        
        def clean_sheet(sheet_name):
            ws = sh.worksheet(sheet_name)
            raw = ws.get_all_values()
            if len(raw) <= 1: return pd.DataFrame()
            
            # Clean headers and handle empty/deleted columns
            headers = [h.strip() if h.strip() else f"Col_{i}" for i, h in enumerate(raw[0])]
            final_headers = []
            counts = {}
            for h in headers:
                if h in counts:
                    counts[h] += 1
                    final_headers.append(f"{h}_{counts[h]}")
                else: 
                    counts[h] = 0
                    final_headers.append(h)
            
            df = pd.DataFrame(raw[1:], columns=final_headers)
            # Drop phantom columns from your screenshot (Col_10, etc)
            df = df.loc[:, ~df.columns.str.contains('^Col_')]
            return df.dropna(how='all')

        df_s = clean_sheet("Details")
        df_e = clean_sheet("Event Details")

        if not df_s.empty: 
            df_s['SN'] = df_s['SN'].astype(str).str.strip()
        if not df_e.empty: 
            if 'SN' in df_e.columns: df_e['SN'] = df_e['SN'].astype(str).str.strip()
            # Find duration column for math
            dur_col = next((c for c in df_e.columns if "Duration" in c), None)
            if dur_col:
                df_e['Dur_Math'] = pd.to_numeric(df_e[dur_col].astype(str).str.extract('(\d+)')[0], errors='coerce').fillna(0)
        
        return df_s, df_e
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_staff, df_events = load_and_scrub_data()

# Identify Badge Column Globally (Fixes NameError)
badge_col = next((c for c in df_staff.columns if "Badge" in c), "Leader Badge") if not df_staff.empty else "Badge"

# --- 4. NAVIGATION ---
page = st.sidebar.radio("Navigation", ["📊 Strategic Overview", "👤 Staff Search & History", "🗓️ Event Logs", "🏆 Leaderboard", "🖨️ Report Center", "⚙️ Data Management"])

# --- 5. STRATEGIC OVERVIEW ---
if page == "📊 Strategic Overview":
    st.title("📊 Strategic Overview")
    if not df_staff.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Registered Staff", len(df_staff))
        tl_list = ["Team Leader", "Pro in Fireworks", "Master in Fireworks"]
        tls = len(df_staff[df_staff[badge_col].isin(tl_list)]) if badge_col in df_staff.columns else 0
        c2.metric("Total Team Leaders", tls)
        c3.metric("Assistants / Technicians", len(df_staff) - tls)
        
        st.divider()
        st.subheader("Event Distribution by Group")
        # Find group column for charting
        group_col = next((c for c in df_events.columns if "Group" in c), None)
        if not df_events.empty and group_col:
            st.bar_chart(df_events[group_col].value_counts())
        else:
            st.info("No Event Group data found to display chart.")

# --- 6. STAFF SEARCH & HISTORY ---
elif page == "👤 Staff Search & History":
    st.title("👤 Staff Search & History")
    if not df_staff.empty:
        # 1. Full Registry Table
        st.subheader("Full Staff Registry")
        st.dataframe(df_staff, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # 2. Individual Search Area
        st.subheader("Individual Staff Activity")
        sel_sn = st.selectbox("Select Staff SN", df_staff['SN'].unique())
        person = df_staff[df_staff['SN'] == sel_sn].iloc[0]
        
        # Pull stats from event sheet
        staff_events = df_events[df_events['SN'] == sel_sn] if not df_events.empty else pd.DataFrame()
        total_ev = len(staff_events)
        total_mins = staff_events['Dur_Math'].sum() if 'Dur_Math' in staff_events.columns else 0
        
        # Dashboard for individual
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Name", person['Name'])
        k2.metric("Rank", person['Rank'])
        k3.metric("Total Events", total_ev)
        k4.metric("Total Duration (Mins)", f"{int(total_mins)} min")
        
        st.write(f"**Unit:** {person.get('Unit', 'N/A')} | **Badge:** {person.get(badge_col, 'N/A')}")
        
        st.write("### Detailed Activity Log")
        if not staff_events.empty:
            st.dataframe(staff_events.drop(columns=['Dur_Math'], errors='ignore'), use_container_width=True, hide_index=True)
        else:
            st.info("No recorded events for this staff member.")

# --- 7. LEADERBOARD ---
elif page == "🏆 Leaderboard":
    st.title("🏆 Leaderboard")
    if not df_events.empty:
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("🎖️ Most Events Attended")
            ev_counts = df_events['SN'].value_counts().reset_index()
            ev_counts.columns = ['SN', 'Events']
            lb_ev = pd.merge(ev_counts, df_staff[['SN', 'Name', 'Rank']], on='SN').head(10)
            st.table(lb_ev[['Rank', 'Name', 'Events']])
            
        with col_right:
            st.subheader("⏳ Most Active (Minutes)")
            if 'Dur_Math' in df_events.columns:
                dur_counts = df_events.groupby('SN')['Dur_Math'].sum().sort_values(ascending=False).reset_index()
                dur_counts.columns = ['SN', 'Total Minutes']
                lb_dur = pd.merge(dur_counts, df_staff[['SN', 'Name', 'Rank']], on='SN').head(10)
                st.table(lb_dur[['Rank', 'Name', 'Total Minutes']])

# --- 8. REPORT CENTER ---
elif page == "🖨️ Report Center":
    st.title("🖨️ Report Center")
    t1, t2 = st.tabs(["📥 Excel Reports", "📄 PDF View"])
    
    with t1:
        c1, c2 = st.columns(2)
        with c1:
            st.write("### Staff Registry")
            buffer = BytesIO()
            df_staff.to_excel(buffer, index=False)
            st.download_button("Download All Staff Excel", buffer.getvalue(), "Staff_Registry.xlsx", "application/vnd.ms-excel")
            
        with c2:
            st.write("### Event Details Registry")
            buffer_e = BytesIO()
            df_events.to_excel(buffer_e, index=False)
            st.download_button("Download All Events Excel", buffer_e.getvalue(), "Event_Details.xlsx", "application/vnd.ms-excel")

# --- 9. DATA MANAGEMENT ---
elif page == "⚙️ Data Management":
    st.title("⚙️ Data Management")
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    
    tab_a, tab_b = st.tabs(["➕ Add New", "🗑️ Delete Record"])
    
    with tab_a:
        mode = st.radio("Choose Entry Type", ["New Staff Member", "New Event Log"], horizontal=True)
        
        if mode == "New Staff Member":
            with st.form("staff_form"):
                f_sn, f_rk, f_nm = st.text_input("SN"), st.text_input("Rank"), st.text_input("Name")
                f_un, f_ct = st.text_input("Unit"), st.text_input("Contact")
                f_bd = st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
                if st.form_submit_button("Save Staff"):
                    sh.worksheet("Details").append_row([f_sn, f_rk, f_nm, f_un, f_ct, f_bd])
                    st.success("Staff added!"); st.rerun()
        else:
            with st.form("event_form"):
                e_ref, e_sn = st.text_input("Sheet Reference"), st.text_input("Staff SN")
                e_loc, e_name = st.text_input("Event Location"), st.text_input("Event Name")
                e_date = st.date_input("Event Date")
                e_dur = st.text_input("Duration (Mins)")
                e_grp = st.selectbox("Group", ["New Year", "Eid", "National Day", "Other"])
                if st.form_submit_button("Log Event"):
                    sh.worksheet("Event Details").append_row([e_ref, e_sn, e_loc, e_name, str(e_date), e_dur, e_grp])
                    st.success("Event logged!"); st.rerun()
