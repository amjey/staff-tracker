import streamlit as st
import pandas as pd

# --- CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=2)
def load_data():
    df_staff = pd.read_csv(DETAILS_URL).rename(columns=lambda x: x.strip())
    df_events = pd.read_csv(EVENTS_URL).rename(columns=lambda x: x.strip())
    
    # 1. Aggressive SN Cleaning (The Bridge)
    def clean_val(val):
        return str(val).split('.')[0].strip()

    df_staff['SN'] = df_staff['SN'].apply(clean_val)
    df_events['SN'] = df_events['SN'].apply(clean_val)
    
    # 2. Dynamic Column Mapping (Fixes the KeyErrors)
    dur_col = next((c for c in df_events.columns if 'duration' in c.lower()), "Duration")
    date_col = next((c for c in df_events.columns if 'date' in c.lower()), "Event Date")
    loc_col = next((c for c in df_events.columns if 'location' in c.lower()), "Event Location")
    cat_col = next((c for c in df_events.columns if 'group' in c.lower() or 'category' in c.lower()), "Master Group")

    # Force Duration to Number
    if dur_col in df_events.columns:
        df_events[dur_col] = pd.to_numeric(df_events[dur_col], errors='coerce').fillna(0)

    # 3. Role Mapping
    def categorize_staff(badge):
        b = str(badge).strip()
        if b in ["Assist.Technician", "Driver"]: return "Assist.Technician"
        if b in ["Master in Fireworks", "Pro in Fireworks", "Team Leader"]: return "Team Leader"
        return "Unassigned"

    df_staff['Category'] = df_staff['Leader Badge'].apply(categorize_staff)
    return df_staff, df_events, dur_col, date_col, loc_col, cat_col

# Load once globally
df_staff, df_events, dur_col, date_col, loc_col, cat_col = load_data()

# --- STABLE TABS NAVIGATION ---
# Defining tabs as objects ensures the app doesn't jump back to tab 1
t1, t2, t3, t4, t5 = st.tabs(["📊 Dashboard", "👤 Staff Details", "➕ Add Data", "🗓️ Event Logs", "🏆 Leaderboard"])

# --- TAB 1: DASHBOARD ---
with t1:
    st.title("📊 Strategic Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Registered", len(df_staff))
    c2.metric("Team Leaders", len(df_staff[df_staff['Category'] == "Team Leader"]))
    c3.metric("Assist. Technicians", len(df_staff[df_staff['Category'] == "Assist.Technician"]))
    
    st.write("---")
    st.subheader("Category Summary")
    summary = df_events.groupby(cat_col).size().reset_index(name='Total Events')
    st.table(summary) # This is the index-free table you wanted

# --- TAB 2: STAFF DETAILS (No Shifting) ---
with t2:
    st.title("👤 Staff Profiles")
    f1, f2 = st.columns([1, 2])
    with f1:
        roles = ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"]
        role_filter = st.multiselect("Filter Table:", options=roles, default=roles)
    with f2:
        search_sn = st.text_input("🔍 Search SN for Profile", key="profile_search_anchor")

    display_df = df_staff[df_staff['Leader Badge'].isin(
