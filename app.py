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
st.set_page_config(page_title="Amjey Staff Intelligence", layout="wide", page_icon="🎯")

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
            df = pd.DataFrame(raw[1:], columns=headers)
            return df.dropna(how='all')

        df_s = clean_sheet("Details")
        df_e = clean_sheet("Event Details")

        if not df_s.empty: 
            df_s['SN'] = df_s['SN'].astype(str).str.strip()
        
        if not df_e.empty: 
            if 'SN' in df_e.columns: df_e['SN'] = df_e['SN'].astype(str).str.strip()
            # Math conversion for duration
            dur_col = next((c for c in df_e.columns if "Duration" in c), None)
            if dur_col:
                df_e['Dur_Math'] = pd.to_numeric(df_e[dur_col].astype(str).str.extract('(\d+)')[0], errors='coerce').fillna(0)
            
            # UNIQUE EVENT IDENTIFICATION
            df_e['Unique_Event_ID'] = df_e['Event Location'] + df_e['Event Name'] + df_e['Event Date'].astype(str)
            
        return df_s, df_e
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_staff, df_events = load_and_scrub_data()
badge_col = next((c for c in df_staff.columns if "Badge" in c), "Leader Badge") if not df_staff.empty else "Badge"

# --- 4. ACCESS CONTROL & NAVIGATION ---
st.sidebar.title("🔐 Amjey Intelligence")

access_type = st.sidebar.radio("Access Level", ["Guest/Viewer", "Admin"])
nav_options = ["📊 Strategic Overview", "👤 Staff Search & History", "🗓️ Event Logs", "🏆 Leaderboard", "📈 Event Statistics"]

if access_type == "Admin":
    # Replace 'YourSecret123' with your chosen password
    admin_pw = st.sidebar.text_input("Admin Password", type="password")
    if admin_pw == "YourSecret123":
        st.sidebar.success("Logged in as Admin")
        nav_options += ["🖨️ Report Center", "⚙️ Data Management"]
    elif admin_pw != "":
        st.sidebar.error("Incorrect Password")

page = st.sidebar.radio("Navigation", nav_options)

# --- 5. PAGE LOGIC ---

if page == "📊 Strategic Overview":
    st.title("🎯 Amjey Staff Intelligence")
    st.subheader("Operations Dashboard")
    
    if not df_staff.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Registered Staff", len(df_staff))
        
        unique_count = df_events['Unique_Event_ID'].nunique() if not df_events.empty else 0
        c2.metric("Total Unique Events", unique_count)
        
        tl_list = ["Team Leader", "Pro in Fireworks", "Master in Fireworks"]
        tls = len(df_staff[df_staff[badge_col].isin(tl_list)]) if badge_col in df_staff.columns else 0
        c3.metric("Total Team Leaders", tls)
        
        st.divider()
        st.subheader("Event Distribution (Unique Deployments)")
        if not df_events.empty:
            unique_df = df_events.drop_duplicates(subset=['Unique_Event_ID'])
            group_col = next((c for c in df_events.columns if "Group" in c), None)
            if group_col:
                st.bar_chart(unique_df[group_col].value_counts())

elif page == "👤 Staff Search & History":
    st.title("👤 Staff Search & History")
    if not df_staff.empty:
        st.subheader("Full Staff Registry")
        st.dataframe(df_staff, use_container_width=True, hide_index=True)
        st.divider()
        sel_sn = st.selectbox("Select Staff SN", df_staff['SN'].unique())
        person = df_staff[df_staff['SN'] == sel_sn].iloc[0]
        staff_events = df_events[df_events['SN'] == sel_sn] if not df_events.empty else pd.DataFrame()
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Name", person['Name'])
        k2.metric("Rank", person['Rank'])
        k3.metric("Events Attended", len(staff_events))
        k4.metric("Total Minutes", int(staff_events['Dur_Math'].sum()) if 'Dur_Math' in staff_events.columns else 0)
        
        if not staff_events.empty:
            st.dataframe(staff_events.drop(columns=['Dur_Math', 'Unique_Event_ID'], errors='ignore'), use_container_width=True, hide_index=True)

elif page == "🗓️ Event Logs":
    st.title("🗓️ Event Logs")
    if not df_events.empty:
        search_term = st.text_input("🔍 Search Location or Event Name", "").strip()
        if search_term:
            filtered = df_events[df_events['Event Location'].str.contains(search_term, case=False, na=False) | df_events['Event Name'].str.contains(search_term, case=False, na=False)]
            for (loc, name, date), group in filtered.groupby(['Event Location', 'Event Name', 'Event Date']):
                with st.expander(f"📍 {loc} | 🏷️ {name} | 📅 {date}"):
                    attendees = pd.merge(group[['SN']], df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
                    st.dataframe(attendees, use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("📋 Raw Data (All Entries)")
        st.dataframe(df_events.drop(columns=['Dur_Math', 'Unique_Event_ID'], errors='ignore'), use_container_width=True, hide_index=True)

elif page == "🏆 Leaderboard":
    st.title("🏆 Staff Leaderboard")
    if not df_events.empty and not df_staff.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🎖️ Most Events Attended")
            counts = df_events['SN'].value_counts().reset_index()
            counts.columns = ['SN', 'Count']
            merged = pd.merge(counts, df_staff[['SN', 'Name', 'Rank']], on='SN').head(15)
            st.dataframe(merged[['Rank', 'Name', 'Count']], use_container_width=True, hide_index=True)
        with c2:
            st.subheader("⏳ Total Time on Field")
            durs = df_events.groupby('SN')['Dur_Math'].sum().sort_values(ascending=False).reset_index()
            durs.columns = ['SN', 'Mins']
            merged_dur = pd.merge(durs, df_staff[['SN', 'Name', 'Rank']], on='SN').head(15)
            st.dataframe(merged_dur[['Rank', 'Name', 'Mins']], use_container_width=True, hide_index=True)

elif page == "📈 Event Statistics":
    st.title("📈 Unique Event Analytics")
    if not df_events.empty:
        unique_events_df = df_events.drop_duplicates(subset=['Unique_Event_ID'])
        st.write("### 📍 Unique Events by Location")
        loc_counts = unique_events_df['Event Location'].value_counts()
        st.bar_chart(loc_counts)
        c1, c2 = st.columns(2)
        with c1:
            st.write("#### Top 5 Locations")
            st.table(loc_counts.head(5))
        with c2:
            st.write("#### Top 5 Event Types")
            name_counts = unique_events_df['Event Name'].value_counts()
            st.table(name_counts.head(5))

elif page == "🖨️ Report Center":
    st.title("🖨️ Report Center")
    c1, c2 = st.columns(2)
    with c1:
        st.info("### 📋 Full Registry")
        buf1 = BytesIO(); df_staff.to_excel(buf1, index=False)
        st.download_button("📥 Download Staff Excel", buf1.getvalue(), "Staff_Registry.xlsx")
    with c2:
        st.success("### 🗓️ All Logs")
        buf2 = BytesIO(); df_events.drop(columns=['Dur_Math', 'Unique_Event_ID'], errors='ignore').to_excel(buf2, index=False)
        st.download_button("📥 Download All Event Logs", buf2.getvalue(), "Full_Event_Logs.xlsx")
    st.divider()
    c3, c4 = st.columns(2)
    with c3:
        st.warning("### 👤 Individual Staff Profile")
        p_sn = st.selectbox("Select SN", df_staff['SN'].unique())
        if st.button("Prepare Staff Report"):
            buf3 = BytesIO()
            with pd.ExcelWriter(buf3, engine='openpyxl') as writer:
                df_staff[df_staff['SN'] == p_sn].to_excel(writer, sheet_name='Profile', index=False)
                df_events[df_events['SN'] == p_sn].drop(columns=['Dur_Math', 'Unique_Event_ID'], errors='ignore').to_excel(writer, sheet_name='Attendance_History', index=False)
            st.download_button(f"📥 Download Profile {p_sn}", buf3.getvalue(), f"Profile_{p_sn}.xlsx")
    with c4:
        st.error("### 📍 Location Report")
        unique_list = df_events.drop_duplicates(subset=['Unique_Event_ID'])
        unique_list['Label'] = unique_list['Event Location'] + " | " + unique_list['Event Name'] + " (" + unique_list['Event Date'].astype(str) + ")"
        sel_label = st.selectbox("Select Specific Event", unique_list['Label'].unique())
        if st.button("Generate Attendee List"):
            match_id = unique_list[unique_list['Label'] == sel_label]['Unique_Event_ID'].iloc[0]
            attendees = df_events[df_events['Unique_Event_ID'] == match_id]
            final_rep = pd.merge(attendees[['SN', 'Event Location', 'Event Name', 'Event Date']], df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
            buf4 = BytesIO(); final_rep.to_excel(buf4, index=False)
            st.download_button("📥 Download Attendee Excel", buf4.getvalue(), "Event_Staff_List.xlsx")

elif page == "⚙️ Data Management":
    st.title("⚙️ Data Management")
    gc = get_gspread_client(); sh = gc.open_by_key(SHEET_ID)
    t_add, t_del = st.tabs(["Add Entry", "Delete Record"])
    with t_add:
        mode = st.radio("Type", ["Staff", "Event Log"], horizontal=True)
        if mode == "Staff":
            with st.form("s_form"):
                sn, rk, nm = st.text_input("SN"), st.text_input("Rank"), st.text_input("Name")
                un, ct = st.text_input("Unit"), st.text_input("Contact")
                bd = st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
                if st.form_submit_button("Save"):
                    sh.worksheet("Details").append_row([sn, rk, nm, un, ct, bd]); st.rerun()
        else:
            with st.form("e_form"):
                e_ref = st.text_input("Reference")
                e_sn = st.selectbox("Staff SN", df_staff['SN'].unique())
                e_loc, e_name = st.text_input("Location"), st.text_input("Event Name")
                e_date, e_dur = st.date_input("Date"), st.number_input("Mins", min_value=1)
                e_grp = st.selectbox("Group", ["New Year", "Eid", "National Day", "Opening", "Other"])
                if st.form_submit_button("Log"):
                    sh.worksheet("Event Details").append_row([e_ref, e_sn, e_loc, e_name, str(e_date), str(e_dur), e_grp]); st.rerun()
