import streamlit as st
import pandas as pd

# --- 1. GLOBAL CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=2)
def load_data():
    df_staff = pd.read_csv(DETAILS_URL).rename(columns=lambda x: x.strip())
    df_events = pd.read_csv(EVENTS_URL).rename(columns=lambda x: x.strip())
    
    clean_val = lambda x: str(x).split('.')[0].strip()
    df_staff['SN'] = df_staff['SN'].apply(clean_val)
    df_events['SN'] = df_events['SN'].apply(clean_val)
    
    # Clean Contact
    if 'Contact' in df_staff.columns:
        df_staff['Contact'] = df_staff['Contact'].apply(clean_val)
    
    # Dynamic Column Mapping
    dur_col = next((c for c in df_events.columns if 'duration' in c.lower()), "Duration")
    loc_col = next((c for c in df_events.columns if 'location' in c.lower()), "Event Location")
    cat_col = next((c for c in df_events.columns if 'group' in c.lower() or 'category' in c.lower()), "Master Group")
    
    if dur_col in df_events.columns:
        df_events[dur_col] = pd.to_numeric(df_events[dur_col], errors='coerce').fillna(0)

    # Role Mapping for Dashboard
    def get_cat(b):
        b = str(b).strip()
        if b in ["Assist.Technician", "Driver"]: return "AT"
        if b in ["Master in Fireworks", "Pro in Fireworks", "Team Leader"]: return "TL"
        return "Other"
    df_staff['Category_Group'] = df_staff['Leader Badge'].apply(get_cat)

    return df_staff, df_events, dur_col, loc_col, cat_col

df_staff, df_events, dur_col, loc_col, cat_col = load_data()

# --- 2. STABLE NAVIGATION ---
# Using standard tabs but with fixed content ensures no data loss
t1, t2, t3, t4, t5 = st.tabs(["📊 Dashboard", "👤 Staff Details", "➕ Add Data", "🗓️ Event Logs", "🏆 Leaderboard"])

# --- TAB 1: DASHBOARD (DATA RESTORED) ---
with t1:
    st.title("📊 Strategic Overview")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Registered", len(df_staff))
    m2.metric("Team Leaders", len(df_staff[df_staff['Category_Group'] == "TL"]))
    m3.metric("Assist. Technicians", len(df_staff[df_staff['Category_Group'] == "AT"]))
    
    st.write("---")
    st.subheader("Event Frequency by Category")
    if cat_col in df_events.columns:
        summary = df_events.groupby(cat_col).size().reset_index(name='Total Events')
        st.dataframe(summary, use_container_width=True, hide_index=True)

# --- TAB 2: STAFF DETAILS (DATA RESTORED) ---
with t2:
    st.title("👤 Staff Profiles")
    f1, f2 = st.columns([1, 2])
    with f1:
        roles = ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"]
        role_filter = st.multiselect("Filter Table:", options=roles, default=roles, key="role_sel")
    with f2:
        search_sn = st.text_input("🔍 Search SN for Profile", key="sn_search_key")

    display_df = df_staff[df_staff['Leader Badge'].isin(role_filter)]
    st.dataframe(display_df[['SN', 'Rank', 'Name', 'Unit', 'Contact', 'Leader Badge']], use_container_width=True, hide_index=True)

    if search_sn:
        p_match = df_staff[df_staff['SN'] == search_sn.strip()]
        if not p_match.empty:
            p = p_match.iloc[0]
            st.markdown("---")
            st.header(f"Profile: {p['Name']}")
            hist = df_events[df_events['SN'] == search_sn.strip()]
            st.metric("Total Duration", f"{int(hist[dur_col].sum())} Mins")
            st.dataframe(hist, use_container_width=True, hide_index=True)

# --- TAB 3: ADD DATA ---
with t3:
    st.title("➕ Data Management")
    st.link_button("Open Master Google Sheet", SHEET_EDIT_URL)
    st.info("Direct editing in Google Sheets is the fastest way to update Rank, Unit, or SN.")

# --- TAB 4: EVENT LOGS (LOCATION SEARCH RESTORED) ---
with t4:
    st.title("🗓️ Event Logs")
    search_loc = st.text_input("🔍 Search by Location Name", key="loc_search_key")
    
    filtered_ev = df_events.copy()
    if search_loc:
        filtered_ev = filtered_ev[filtered_ev[loc_col].str.contains(search_loc, case=False, na=False)]
    
    st.write(f"### Found {len(filtered_ev)} Event Entries")
    st.dataframe(filtered_ev, use_container_width=True, hide_index=True)

# --- TAB 5: LEADERBOARD (TOP 5 WITH SN) ---
with t5:
    st.title("🏆 Top 5 Performance Leaderboard")
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("🔥 Top 5 by Engagements")
        t_eng = df_events['SN'].value_counts().head(5).reset_index()
        t_eng.columns = ['SN', 'Events']
        res_eng = pd.merge(t_eng, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
        st.dataframe(res_eng[['SN', 'Rank', 'Name', 'Events']], use_container_width=True, hide_index=True)

    with c2:
        st.subheader("⏳ Top 5 by Total Duration")
        t_dur = df_events.groupby('SN')[dur_col].sum().sort_values(ascending=False).head(5).reset_index()
        t_dur.columns = ['SN', 'Total Mins']
        res_dur = pd.merge(t_dur, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
        st.dataframe(res_dur[['SN', 'Rank', 'Name', 'Total Mins']], use_container_width=True, hide_index=True)
