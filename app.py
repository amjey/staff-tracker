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
            df = df.loc[:, ~df.columns.str.contains('^Col_')]
            return df.dropna(how='all')

        df_s = clean_sheet("Details")
        df_e = clean_sheet("Event Details")

        if not df_s.empty: 
            df_s['SN'] = df_s['SN'].astype(str).str.strip()
        if not df_e.empty: 
            if 'SN' in df_e.columns: df_e['SN'] = df_e['SN'].astype(str).str.strip()
            dur_col = next((c for c in df_e.columns if "Duration" in c), None)
            if dur_col:
                df_e['Dur_Math'] = pd.to_numeric(df_e[dur_col].astype(str).str.extract('(\d+)')[0], errors='coerce').fillna(0)
        
        return df_s, df_e
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_staff, df_events = load_and_scrub_data()
badge_col = next((c for c in df_staff.columns if "Badge" in c), "Leader Badge") if not df_staff.empty else "Badge"

# --- 4. NAVIGATION ---
page = st.sidebar.radio("Navigation", ["📊 Strategic Overview", "👤 Staff Search & History", "🗓️ Event Logs", "🏆 Leaderboard", "🖨️ Report Center", "⚙️ Data Management"])

# --- 5. STRATEGIC OVERVIEW (PERFECT - UNCHANGED) ---
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
        group_col = next((c for c in df_events.columns if "Group" in c), None)
        if not df_events.empty and group_col:
            st.bar_chart(df_events[group_col].value_counts())

# --- 6. STAFF SEARCH & HISTORY (PERFECT - UNCHANGED) ---
elif page == "👤 Staff Search & History":
    st.title("👤 Staff Search & History")
    if not df_staff.empty:
        st.subheader("Full Staff Registry")
        st.dataframe(df_staff, use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("Individual Staff Activity")
        sel_sn = st.selectbox("Select Staff SN", df_staff['SN'].unique())
        person = df_staff[df_staff['SN'] == sel_sn].iloc[0]
        staff_events = df_events[df_events['SN'] == sel_sn] if not df_events.empty else pd.DataFrame()
        total_ev = len(staff_events)
        total_mins = staff_events['Dur_Math'].sum() if 'Dur_Math' in staff_events.columns else 0
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Name", person['Name'])
        k2.metric("Rank", person['Rank'])
        k3.metric("Total Events", total_ev)
        k4.metric("Total Duration", f"{int(total_mins)} min")
        st.write(f"**Unit:** {person.get('Unit', 'N/A')} | **Badge:** {person.get(badge_col, 'N/A')}")
        if not staff_events.empty:
            st.dataframe(staff_events.drop(columns=['Dur_Math'], errors='ignore'), use_container_width=True, hide_index=True)

# --- 7. EVENT LOGS (SEARCH + TABLE - UNCHANGED) ---
elif page == "🗓️ Event Logs":
    st.title("🗓️ Event Logs")
    if not df_events.empty:
        st.subheader("🔍 Detailed Search")
        search_term = st.text_input("Enter Location or Event Name to see Staff Attendees", "").strip()
        if search_term:
            filtered_df = df_events[df_events['Event Location'].str.contains(search_term, case=False, na=False) | df_events['Event Name'].str.contains(search_term, case=False, na=False)]
            if not filtered_df.empty:
                for (loc, name, date), group in filtered_df.groupby(['Event Location', 'Event Name', 'Event Date']):
                    with st.expander(f"📍 {loc} | 🏷️ {name} | 📅 {date}"):
                        attendees = pd.merge(group[['SN']], df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
                        st.dataframe(attendees[['SN', 'Rank', 'Name']], use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("📋 All Event History")
        st.dataframe(df_events.drop(columns=['Dur_Math'], errors='ignore'), use_container_width=True, hide_index=True)

# --- 8. LEADERBOARD ---
elif page == "🏆 Leaderboard":
    st.title("🏆 Leaderboard")
    if not df_events.empty and not df_staff.empty:
        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("🎖️ Most Events Attended")
            ev_counts = df_events['SN'].value_counts().reset_index(); ev_counts.columns = ['SN', 'Events Count']
            lb_ev = pd.merge(ev_counts, df_staff[['SN', 'Name', 'Rank']], on='SN').head(15)
            st.dataframe(lb_ev[['Rank', 'Name', 'Events Count']], use_container_width=True, hide_index=True)
        with col_right:
            st.subheader("⏳ Highest Total Duration")
            if 'Dur_Math' in df_events.columns:
                dur_sum = df_events.groupby('SN')['Dur_Math'].sum().sort_values(ascending=False).reset_index(); dur_sum.columns = ['SN', 'Total Mins']
                lb_dur = pd.merge(dur_sum, df_staff[['SN', 'Name', 'Rank']], on='SN').head(15)
                st.dataframe(lb_dur[['Rank', 'Name', 'Total Mins']], use_container_width=True, hide_index=True)

# --- 9. REPORT CENTER (UPDATED FOR PROFILE EVENTS) ---
elif page == "🖨️ Report Center":
    st.title("🖨️ Report Center")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("### Staff Registry")
        buf1 = BytesIO(); df_staff.to_excel(buf1, index=False)
        st.download_button("📥 Download Staff Excel", buf1.getvalue(), "Full_Staff_List.xlsx")
    with c2:
        st.success("### Event Logs")
        buf2 = BytesIO(); df_events.drop(columns=['Dur_Math'], errors='ignore').to_excel(buf2, index=False)
        st.download_button("📥 Download All Events Excel", buf2.getvalue(), "Event_History.xlsx")
    with c3:
        st.warning("### Individual Profile")
        p_sn = st.selectbox("Select SN for Detailed Report", df_staff['SN'].unique())
        if st.button("Prepare Profile Excel"):
            buf3 = BytesIO()
            # Creating Excel with 2 Sheets: Profile Data and Event History
            with pd.ExcelWriter(buf3, engine='openpyxl') as writer:
                # Sheet 1: Basic Info
                df_staff[df_staff['SN'] == p_sn].to_excel(writer, sheet_name='Staff_Details', index=False)
                # Sheet 2: Event History (The Requested Feature)
                if not df_events.empty:
                    p_events = df_events[df_events['SN'] == p_sn].drop(columns=['Dur_Math'], errors='ignore')
                    p_events.to_excel(writer, sheet_name='Event_History', index=False)
            
            st.download_button(f"📥 Download Profile (SN: {p_sn})", buf3.getvalue(), f"Profile_Report_{p_sn}.xlsx")

# --- 10. DATA MANAGEMENT ---
elif page == "⚙️ Data Management":
    st.title("⚙️ Data Management")
    gc = get_gspread_client(); sh = gc.open_by_key(SHEET_ID)
    tab_add, tab_del = st.tabs(["➕ Add Entry", "🗑️ Delete Record"])
    with tab_add:
        choice = st.radio("Entry Type", ["New Staff Member", "New Event Log"], horizontal=True)
        if choice == "New Staff Member":
            with st.form("staff_form"):
                sn, rk, nm = st.text_input("SN"), st.text_input("Rank"), st.text_input("Name")
                un, ct = st.text_input("Unit"), st.text_input("Contact")
                bd = st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
                if st.form_submit_button("Save Staff"):
                    sh.worksheet("Details").append_row([sn, rk, nm, un, ct, bd])
                    st.success("Staff added!"); st.rerun()
        else:
            with st.form("event_form"):
                e_ref = st.text_input("Reference/ID"); e_sn = st.selectbox("Staff SN", df_staff['SN'].unique())
                e_loc, e_name = st.text_input("Event Location"), st.text_input("Event Name")
                e_date, e_dur = st.date_input("Event Date"), st.number_input("Duration (Minutes)", min_value=1, step=1)
                e_grp = st.selectbox("Group", ["New Year", "Eid", "National Day", "Opening", "Other"])
                if st.form_submit_button("Log Event"):
                    sh.worksheet("Event Details").append_row([e_ref, e_sn, e_loc, e_name, str(e_date), str(e_dur), e_grp])
                    st.success("Event Logged!"); st.rerun()
