import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials

# --- 1. SECURE GOOGLE SHEETS CONNECTION ---
def get_gspread_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        # Reads the triple-quoted JSON string from your Streamlit Secrets
        creds_info = json.loads(st.secrets["gcp_service_account"]["service_account_info"])
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Secret Configuration Error: {e}")
        st.stop()

# --- 2. GLOBAL CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=2)
def load_data():
    try:
        df_staff = pd.read_csv(DETAILS_URL).rename(columns=lambda x: x.strip())
        df_events = pd.read_csv(EVENTS_URL).rename(columns=lambda x: x.strip())
        
        # Data Cleaning (SN and Contacts)
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

        # Leader Categorization for Dashboard
        def get_cat(b):
            b = str(b).strip()
            if b in ["Assist.Technician", "Driver"]: return "AT"
            if b in ["Master in Fireworks", "Pro in Fireworks", "Team Leader"]: return "TL"
            return "Other"
        df_staff['Category_Group'] = df_staff['Leader Badge'].apply(get_cat)

        return df_staff, df_events, dur_col, loc_col, cat_col
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), "", "", ""

df_staff, df_events, dur_col, loc_col, cat_col = load_data()

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("Main Menu")
    page = st.radio("Go to:", ["📊 Dashboard", "👤 Staff Details", "🗓️ Event Logs", "🏆 Leaderboard", "➕ Add Data"])
    st.divider()
    if st.button("🔄 Sync with Sheet"):
        st.cache_data.clear()
        st.rerun()

# --- 4. PAGE LOGIC ---

if page == "📊 Dashboard":
    st.title("📊 Strategic Overview")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Registered", len(df_staff))
    m2.metric("Team Leaders", len(df_staff[df_staff['Category_Group'] == "TL"]))
    m3.metric("Assist. Technicians", len(df_staff[df_staff['Category_Group'] == "AT"]))
    
    st.divider()
    if cat_col in df_events.columns:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("Event Stats")
            summary = df_events.groupby(cat_col).size().reset_index(name='Total')
            st.dataframe(summary, use_container_width=True, hide_index=True)
        with c2:
            st.subheader("Event Category Chart")
            st.bar_chart(df_events[cat_col].value_counts(), color="#2e7d32")

elif page == "👤 Staff Details":
    st.title("👤 Staff Profile Search")
    search_sn = st.text_input("🔍 Enter Staff SN", placeholder="e.g. 101")
    
    if search_sn:
        res = df_staff[df_staff['SN'] == search_sn.strip()]
        if not res.empty:
            p = res.iloc[0]
            st.header(f"Profile: {p['Name']}")
            hist = df_events[df_events['SN'] == p['SN']]
            k1, k2, k3 = st.columns(3)
            k1.metric("Rank", p['Rank'])
            k2.metric("Total Events", len(hist))
            k3.metric("Total Minutes", f"{int(hist[dur_col].sum())}")
            st.subheader("Full History")
            st.dataframe(hist, use_container_width=True, hide_index=True)
        else:
            st.warning("No staff found with this SN.")
    else:
        st.dataframe(df_staff, use_container_width=True, hide_index=True)

elif page == "🗓️ Event Logs":
    st.title("🗓️ Master Event Logs")
    s_loc = st.text_input("🔍 Filter by Location")
    filtered = df_events[df_events[loc_col].str.contains(s_loc, case=False, na=False)] if s_loc else df_events
    st.dataframe(filtered, use_container_width=True, hide_index=True)

elif page == "🏆 Leaderboard":
    st.title("🏆 Top Performers")
    l1, l2 = st.columns(2)
    with l1:
        st.subheader("🔥 Most Events")
        top_e = df_events['SN'].value_counts().head(5).reset_index()
        top_e.columns = ['SN', 'Events']
        merged = pd.merge(top_e, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
        st.dataframe(merged[['SN', 'Rank', 'Name', 'Events']], hide_index=True)
    with l2:
        st.subheader("⏳ Highest Duration")
        top_d = df_events.groupby('SN')[dur_col].sum().sort_values(ascending=False).head(5).reset_index()
        top_d.columns = ['SN', 'Mins']
        merged_d = pd.merge(top_d, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
        st.dataframe(merged_d[['SN', 'Rank', 'Name', 'Mins']], hide_index=True)

elif page == "➕ Add Data":
    st.title("➕ Data Entry Control")
    st.info("Directly linked to Google Sheets API.")
    
    # API Connection
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)

    ca, cb = st.columns(2)
    with ca:
        st.subheader("📋 Register New Staff")
        with st.form("staff_form", clear_on_submit=True):
            f_sn = st.text_input("SN")
            f_rk = st.text_input("Rank")
            f_nm = st.text_input("Name")
            f_un = st.text_input("Unit")
            f_ct = st.text_input("Contact")
            f_bd = st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
            if st.form_submit_button("Save Staff Member"):
                if f_sn and f_nm:
                    sh.worksheet("Details").append_row([f_sn, f_rk, f_nm, f_un, f_ct, f_bd])
                    st.success(f"Successfully saved {f_nm}!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("SN and Name are mandatory.")

    with cb:
        st.subheader("🔥 Log New Event")
        with st.form("event_form", clear_on_submit=True):
            e_sn = st.text_input("Staff SN")
            e_nm = st.text_input("Event Name")
            e_lc = st.text_input("Location")
            e_dt = st.date_input("Date")
            e_dr = st.number_input("Duration (Mins)", min_value=1)
            e_gr = st.selectbox("Group", ["New Year", "Eid Celebrations", "National Day", "Other"])
            if st.form_submit_button("Save Event Data"):
                if e_sn and e_nm:
                    sh.worksheet("Event Details").append_row([e_sn, e_nm, e_lc, str(e_dt), e_dr, e_gr])
                    st.success(f"Event logged for SN {e_sn}!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Staff SN and Event Name are mandatory.")

    st.divider()
    st.subheader("👀 Recent Logs (Last 5 Entries)")
    st.dataframe(df_events.tail(5), use_container_width=True, hide_index=True)
