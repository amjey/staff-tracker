import json # Add this at the top
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # We now parse the string we created in Secrets back into a dictionary
    creds_dict = json.loads(st.secrets["gcp_service_account"]["service_account_info"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

# --- 2. GLOBAL CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=2)
def load_data():
    try:
        # Load CSV data for viewing
        df_staff = pd.read_csv(DETAILS_URL).rename(columns=lambda x: x.strip())
        df_events = pd.read_csv(EVENTS_URL).rename(columns=lambda x: x.strip())
        
        # Aggressive SN & Contact Cleaning
        clean_val = lambda x: str(x).split('.')[0].strip()
        df_staff['SN'] = df_staff['SN'].apply(clean_val)
        df_events['SN'] = df_events['SN'].apply(clean_val)
        
        if 'Contact' in df_staff.columns:
            df_staff['Contact'] = df_staff['Contact'].astype(str).apply(lambda x: x.split('.')[0])

        # Flexible Column Discovery
        dur_col = next((c for c in df_events.columns if 'duration' in c.lower()), "Duration")
        loc_col = next((c for c in df_events.columns if 'location' in c.lower()), "Location")
        cat_col = next((c for c in df_events.columns if 'group' in c.lower() or 'category' in c.lower()), "Master Group")

        if dur_col in df_events.columns:
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
        st.error(f"Critical Data Load Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), "", "", ""

df_staff, df_events, dur_col, loc_col, cat_col = load_data()

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("Settings & Navigation")
    page = st.radio("Go to:", ["📊 Dashboard", "👤 Staff Details", "🗓️ Event Logs", "🏆 Leaderboard", "➕ Add Data"])
    st.write("---")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# --- 4. PAGE LOGIC ---

if page == "📊 Dashboard":
    st.title("📊 Strategic Overview")
    if not df_staff.empty:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Registered", len(df_staff))
        m2.metric("Team Leaders", len(df_staff[df_staff['Category_Group'] == "TL"]))
        m3.metric("Assist. Technicians", len(df_staff[df_staff['Category_Group'] == "AT"]))
        
        st.write("---")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Event Frequency")
            if cat_col in df_events.columns:
                summary = df_events.groupby(cat_col).size().reset_index(name='Total Events')
                st.dataframe(summary, use_container_width=True, hide_index=True)
        with c2:
            st.subheader("Event Breakdown Chart")
            if cat_col in df_events.columns:
                chart_data = df_events[cat_col].value_counts()
                st.bar_chart(chart_data)

elif page == "👤 Staff Details":
    st.title("👤 Staff Profiles")
    search_sn = st.text_input("🔍 Enter SN to view Profile", key="perm_sn_search")
    
    if search_sn:
        p_match = df_staff[df_staff['SN'] == search_sn.strip()]
        if not p_match.empty:
            p = p_match.iloc[0]
            st.header(f"Profile: {p['Name']}")
            hist = df_events[df_events['SN'] == search_sn.strip()]
            col_a, col_b = st.columns(2)
            col_a.metric("Events", len(hist))
            col_b.metric("Total Duration", f"{int(hist[dur_col].sum())} Mins")
            st.dataframe(hist, use_container_width=True, hide_index=True)
        else:
            st.warning("No staff member found with that SN.")
    else:
        st.dataframe(df_staff[['SN', 'Rank', 'Name', 'Unit', 'Contact', 'Leader Badge']], hide_index=True)

elif page == "🗓️ Event Logs":
    st.title("🗓️ Event Logs")
    search_loc = st.text_input("🔍 Search Location", key="perm_loc_search")
    filtered = df_events.copy()
    if search_loc:
        filtered = filtered[filtered[loc_col].str.contains(search_loc, case=False, na=False)]
    st.dataframe(filtered, use_container_width=True, hide_index=True)

elif page == "🏆 Leaderboard":
    st.title("🏆 Performance Leaderboard (Top 5)")
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("🔥 Top 5 by Events")
        t_eng = df_events['SN'].value_counts().head(5).reset_index()
        t_eng.columns = ['SN', 'Events']
        res_eng = pd.merge(t_eng, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
        st.dataframe(res_eng[['SN', 'Rank', 'Name', 'Events']], hide_index=True)
    with col_r:
        st.subheader("⏳ Top 5 by Duration")
        t_dur = df_events.groupby('SN')[dur_col].sum().sort_values(ascending=False).head(5).reset_index()
        t_dur.columns = ['SN', 'Total Mins']
        res_dur = pd.merge(t_dur, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
        st.dataframe(res_dur[['SN', 'Rank', 'Name', 'Total Mins']], hide_index=True)

elif page == "➕ Add Data":
    st.title("➕ Data Management")
    st.info("Form data will be saved directly to Google Sheets.")
    
    # Connect to Google Sheets via API
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
    except Exception as e:
        st.error("Could not connect to Google Sheets API. Check your Secrets configuration.")
        st.stop()

    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("📋 Register New Staff")
        with st.form("staff_form", clear_on_submit=True):
            new_sn = st.text_input("SN")
            new_name = st.text_input("Full Name")
            new_rank = st.text_input("Rank")
            new_unit = st.text_input("Unit")
            new_contact = st.text_input("Contact Number")
            new_badge = st.selectbox("Leader Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
            
            if st.form_submit_button("Save to Google Sheet"):
                if new_sn and new_name:
                    ws = sh.worksheet("Details")
                    ws.append_row([new_sn, new_rank, new_name, new_unit, new_contact, new_badge])
                    st.success(f"Successfully added {new_name} to Details!")
                    st.cache_data.clear() # Forces app to reload new data
                else:
                    st.error("SN and Name are required.")

    with col_b:
        st.subheader("🔥 Log New Event")
        with st.form("event_form", clear_on_submit=True):
            ev_sn = st.text_input("Staff SN")
            ev_name = st.text_input("Event Name")
            ev_loc = st.text_input("Event Location")
            ev_date = st.date_input("Event Date")
            ev_dur = st.number_input("Duration (Mins)", min_value=1)
            ev_group = st.selectbox("Master Group", ["New Year", "Eid Al Fitr", "Eid Al Adha", "National Day", "Other"])
            
            if st.form_submit_button("Save Event Log"):
                if ev_sn and ev_name:
                    ws = sh.worksheet("Event Details")
                    ws.append_row([ev_sn, ev_name, ev_loc, str(ev_date), ev_dur, ev_group])
                    st.success(f"Logged event for SN: {ev_sn}!")
                    st.cache_data.clear() # Forces app to reload new data
                else:
                    st.error("Staff SN and Event Name are required.")

    st.write("---")
    st.link_button("📂 Manual Edit Google Sheet", SHEET_EDIT_URL)

