import streamlit as st
import pandas as pd
import gspread
import json
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
        
        # Staff Data
        staff_sheet = sh.worksheet("Details").get_all_values()
        if len(staff_sheet) > 1:
            df_s = pd.DataFrame(staff_sheet[1:], columns=staff_sheet[0])
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
            
            # Clean Duration column for math (removes "mins" text if present)
            if 'Event Duration (Mins)' in df_e.columns:
                df_e['Duration_Num'] = pd.to_numeric(df_e['Event Duration (Mins)'].astype(str).str.extract('(\d+)')[0], errors='coerce').fillna(0)
            
            df_e = df_e[df_e.iloc[:, 0] != ""].dropna(how='all')
        else:
            df_e = pd.DataFrame()

        return df_s, df_e
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_staff, df_events = load_and_scrub_data()

# --- 4. NAVIGATION ---
page = st.sidebar.radio("Navigation", ["📊 Strategic Overview", "👤 Staff Profiles", "🗓️ Event Logs", "🏆 Leaderboard", "➕ Add Data"])

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
        c3.metric("Total Assist.Technician", len(df_staff[df_staff[badge_col].isin(at_list)]))
        
        st.divider()
        if not df_events.empty and 'Master Group' in df_events.columns:
            st.subheader("Events Distribution")
            st.bar_chart(df_events['Master Group'].value_counts())

# --- 6. STAFF PROFILES ---
elif page == "👤 Staff Profiles":
    st.title("👤 Staff Registry & Search")
    if not df_staff.empty:
        st.subheader("All Registered Staff")
        st.dataframe(df_staff, use_container_width=True, hide_index=True)
        st.divider()
        search_sn = st.text_input("🔍 Enter Staff SN to view History").strip()
        if search_sn:
            person = df_staff[df_staff['SN'] == search_sn]
            if not person.empty:
                st.success(f"History for: {person.iloc[0]['Name']} (SN: {search_sn})")
                if not df_events.empty:
                    logs = df_events[df_events['SN'] == search_sn]
                    st.dataframe(logs, use_container_width=True, hide_index=True)
            else:
                st.error("SN not found.")

# --- 7. EVENT LOGS ---
elif page == "🗓️ Event Logs":
    st.title("🗓️ Event Logs")
    if not df_events.empty:
        search_loc = st.text_input("🔍 Search by Event Location").strip()
        if search_loc:
            filtered = df_events[df_events['Event Location'].str.contains(search_loc, case=False, na=False)]
            if not filtered.empty:
                for (loc, date, name, dur), group in filtered.groupby(['Event Location', 'Event Date', 'Event Name', 'Event Duration (Mins)']):
                    with st.expander(f"📍 {loc} | 🗓️ {date} | 🔥 {name}", expanded=True):
                        st.write(f"**Duration:** {dur}")
                        if not df_staff.empty:
         # Inside the Event Logs search logic:
            if not df_staff.empty:
    staff_details = pd.merge(group[['SN']], df_staff[['SN', 'Name', 'Rank', 'Contact']], on='SN', how='left')
    # CHANGE: Use hide_index=True here
    st.dataframe(staff_details, hide_index=True, use_container_width=True)
            else:
                st.warning(f"No events found for: {search_loc}")
        else:
            st.dataframe(df_events, use_container_width=True, hide_index=True)

# --- 8. LEADERBOARD (TOP 5 ONLY) ---
elif page == "🏆 Leaderboard":
    st.title("🏆 Leaderboard - Top 5 Performers")
    
    if not df_events.empty:
        col_a, col_b = st.columns(2)
        
        # Top 5 by Most Events
        with col_a:
            st.subheader("🔥 Top 5: Most Events")
            ev_counts = df_events['SN'].value_counts().reset_index()
            ev_counts.columns = ['SN', 'Total Events']
            if not df_staff.empty:
                lb_ev = pd.merge(ev_counts, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
                # CHANGE: Use st.dataframe with hide_index=True
                st.dataframe(lb_ev[['Rank', 'Name', 'Total Events']].head(5), hide_index=True, use_container_width=True)

        # Top 5 by Total Duration
        with col_b:
            st.subheader("⏳ Top 5: Most Duration (Mins)")
            if 'Duration_Num' in df_events.columns:
                dur_counts = df_events.groupby('SN')['Duration_Num'].sum().reset_index().sort_values('Duration_Num', ascending=False)
                dur_counts.columns = ['SN', 'Total Minutes']
                if not df_staff.empty:
                    lb_dur = pd.merge(dur_counts, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
                    # CHANGE: Use st.dataframe with hide_index=True
                    st.dataframe(lb_dur[['Rank', 'Name', 'Total Minutes']].head(5), hide_index=True, use_container_width=True)
            else:
                st.info("Duration data not available.")
    else:
        st.info("No event data available to generate leaderboard.")

# --- 9. ADD DATA ---
elif page == "➕ Add Data":
    st.title("➕ Data Management")
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📋 Register Staff")
        with st.form("f1", clear_on_submit=True):
            s_sn, s_rk, s_nm = st.text_input("SN"), st.text_input("Rank"), st.text_input("Name")
            s_un, s_ct = st.text_input("Unit"), st.text_input("Contact")
            s_bd = st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
            if st.form_submit_button("Save Staff"):
                sh.worksheet("Details").append_row([s_sn, s_rk, s_nm, s_un, s_ct, s_bd])
                st.rerun()
    with c2:
        st.subheader("🔥 Log Event")
        with st.form("f2", clear_on_submit=True):
            e_sn_ref, e_sn_key = st.text_input("Sheet Ref"), st.text_input("Staff SN")
            e_lc, e_nm = st.text_input("Location"), st.text_input("Event Name")
            e_dt, e_dr = st.date_input("Date"), st.text_input("Duration")
            e_gr = st.selectbox("Group", ["New Year", "Eid", "National Day", "Other"])
            if st.form_submit_button("Save Event"):
                sh.worksheet("Event Details").append_row([e_sn_ref, e_sn_key, e_lc, e_nm, str(e_dt), e_dr, e_gr])
                st.rerun()



