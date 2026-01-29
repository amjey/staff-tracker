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

# --- 3. BULLETPROOF DATA ENGINE ---
def load_and_scrub_data():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
        
        def clean_sheet(sheet_name):
            ws = sh.worksheet(sheet_name)
            raw = ws.get_all_values()
            if len(raw) <= 1: return pd.DataFrame()
            
            headers = [h.strip() if h.strip() else f"Col_{i}" for i, h in enumerate(raw[0])]
            final_headers = []
            counts = {}
            for h in headers:
                if h in counts:
                    counts[h] += 1
                    final_headers.append(f"{h}_{counts[h]}")
                else: counts[h] = 0; final_headers.append(h)
            
            df = pd.DataFrame(raw[1:], columns=final_headers)
            df = df.loc[:, ~df.columns.str.contains('^Col_10|^Col_11|^Col_12')]
            return df.dropna(how='all')

        df_s = clean_sheet("Details")
        df_e = clean_sheet("Event Details")

        if not df_s.empty: df_s['SN'] = df_s['SN'].astype(str).str.strip()
        if not df_e.empty: 
            if 'SN' in df_e.columns: df_e['SN'] = df_e['SN'].astype(str).str.strip()
            # Find the duration column regardless of exact name
            dur_col = next((c for c in df_e.columns if "Duration" in c), None)
            if dur_col:
                df_e['Dur_Math'] = pd.to_numeric(df_e[dur_col].astype(str).str.extract('(\d+)')[0], errors='coerce').fillna(0)
        
        return df_s, df_e
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_staff, df_events = load_and_scrub_data()

# Global Badge Column Logic
badge_col = next((c for c in df_staff.columns if "Badge" in c), "Leader Badge") if not df_staff.empty else "Badge"

# --- 4. NAVIGATION ---
page = st.sidebar.radio("Navigation", ["📊 Strategic Overview", "👤 Staff Profiles", "🗓️ Event Logs", "🏆 Leaderboard", "🖨️ Report Center", "⚙️ Data Management"])

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
        st.subheader("Events Distribution Chart")
        group_col = next((c for c in df_events.columns if "Group" in c or "Master" in c), None)
        if not df_events.empty and group_col:
            st.bar_chart(df_events[group_col].value_counts())
        else:
            st.info("Log events with a 'Group' or 'Master Group' to see the chart.")

# --- 6. STAFF PROFILES ---
elif page == "👤 Staff Profiles":
    st.title("👤 Staff Registry & Search")
    if not df_staff.empty:
        st.subheader("Full Registry (Details Sheet)")
        st.dataframe(df_staff, use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("Individual Search")
        sel_sn = st.selectbox("Select Staff SN to view History", df_staff['SN'].unique())
        person = df_staff[df_staff['SN'] == sel_sn].iloc[0]
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Name:** {person['Name']}")
            st.write(f"**Rank:** {person['Rank']}")
        with col2:
            st.write(f"**Unit:** {person.get('Unit', 'N/A')}")
            st.write(f"**Badge:** {person.get(badge_col, 'N/A')}")
        
        st.write("---")
        st.subheader(f"Activity History for {person['Name']}")
        history = df_events[df_events['SN'] == sel_sn] if not df_events.empty else pd.DataFrame()
        if not history.empty:
            st.dataframe(history, use_container_width=True, hide_index=True)
        else:
            st.info("No recorded events for this staff member.")

# --- 7. LEADERBOARD ---
elif page == "🏆 Leaderboard":
    st.title("🏆 Top Performers")
    if not df_events.empty:
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("🔥 Most Events")
            counts = df_events['SN'].value_counts().reset_index()
            counts.columns = ['SN', 'Events']
            lb = pd.merge(counts, df_staff[['SN', 'Name', 'Rank']], on='SN').head(10)
            st.table(lb[['Rank', 'Name', 'Events']])
        
        with col_b:
            st.subheader("⏳ Most Minutes")
            if 'Dur_Math' in df_events.columns:
                dur = df_events.groupby('SN')['Dur_Math'].sum().sort_values(ascending=False).reset_index()
                dur.columns = ['SN', 'Total Mins']
                lb_d = pd.merge(dur, df_staff[['SN', 'Name', 'Rank']], on='SN').head(10)
                st.table(lb_d[['Rank', 'Name', 'Total Mins']])

# --- 8. REPORT CENTER ---
elif page == "🖨️ Report Center":
    st.title("🖨️ Report Center")
    t_ex, t_pdf = st.tabs(["📊 Excel Exports", "📄 PDF Print View"])
    
    with t_ex:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.subheader("Staff Registry")
            out = BytesIO()
            df_staff.to_excel(out, index=False, engine='xlsxwriter')
            st.download_button("📥 Download Staff Excel", out.getvalue(), "Staff_Registry.xlsx")
        with c2:
            st.subheader("All Event Details")
            out_e = BytesIO()
            df_events.to_excel(out_e, index=False, engine='xlsxwriter')
            st.download_button("📥 Download Events Excel", out_e.getvalue(), "Event_Logs.xlsx")
        with c3:
            st.subheader("Staff Profile Excel")
            p_sn = st.selectbox("Select SN", df_staff['SN'].unique(), key="rep_sn")
            if st.button("Prepare Profile"):
                p_out = BytesIO()
                with pd.ExcelWriter(p_out, engine='xlsxwriter') as writer:
                    df_staff[df_staff['SN'] == p_sn].to_excel(writer, sheet_name='Info', index=False)
                    df_events[df_events['SN'] == p_sn].to_excel(writer, sheet_name='Events', index=False)
                st.download_button("📥 Download Profile", p_out.getvalue(), f"Profile_{p_sn}.xlsx")

# --- 9. DATA MANAGEMENT ---
elif page == "⚙️ Data Management":
    st.title("⚙️ Data Management")
    gc = get_gspread_client(); sh = gc.open_by_key(SHEET_ID)
    m_add, m_edit, m_del = st.tabs(["➕ Add Entry", "✏️ Edit Existing", "🗑️ Delete Record"])
    
    with m_add:
        sub_type = st.radio("What are you adding?", ["New Staff", "New Event Log"], horizontal=True)
        if sub_type == "New Staff":
            with st.form("add_staff"):
                f_sn, f_rk, f_nm = st.text_input("SN"), st.text_input("Rank"), st.text_input("Name")
                f_un, f_ct = st.text_input("Unit"), st.text_input("Contact")
                f_bd = st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
                if st.form_submit_button("Save Staff"):
                    sh.worksheet("Details").append_row([f_sn, f_rk, f_nm, f_un, f_ct, f_bd])
                    st.success("Staff Saved!"); st.rerun()
        else:
            with st.form("add_event"):
                e_ref, e_sn = st.text_input("Sheet Ref"), st.text_input("Staff SN")
                e_lc, e_nm = st.text_input("Location"), st.text_input("Event Name")
                e_dt, e_dr = st.date_input("Date"), st.text_input("Duration (Mins)")
                e_gr = st.selectbox("Group", ["New Year", "Eid", "National Day", "Other"])
                if st.form_submit_button("Log Event"):
                    sh.worksheet("Event Details").append_row([e_ref, e_sn, e_lc, e_nm, str(e_dt), e_dr, e_gr])
                    st.success("Event Logged!"); st.rerun()
