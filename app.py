import streamlit as st
import pandas as pd

# --- 1. GLOBAL CONFIG (Fixed NameError) ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

# --- 2. TAB PERSISTENCE LOGIC (Fixed Tab Shifting) ---
# This small block ensures that the app stays on the current tab after a search
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = 0

def on_tab_change():
    # Placeholder for potential future logic
    pass

@st.cache_data(ttl=2)
def load_data():
    try:
        df_staff = pd.read_csv(DETAILS_URL).rename(columns=lambda x: x.strip())
        df_events = pd.read_csv(EVENTS_URL).rename(columns=lambda x: x.strip())
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame(), "", "", "", ""

    # Aggressive SN Cleaning
    def clean_val(val):
        return str(val).split('.')[0].strip()

    df_staff['SN'] = df_staff['SN'].apply(clean_val)
    df_events['SN'] = df_events['SN'].apply(clean_val)
    
    if 'Contact' in df_staff.columns:
        df_staff['Contact'] = df_staff['Contact'].apply(clean_val)
    
    # Dynamic Column Mapping
    dur_col = next((c for c in df_events.columns if 'duration' in c.lower()), "Duration")
    date_col = next((c for c in df_events.columns if 'date' in c.lower()), "Event Date")
    loc_col = next((c for c in df_events.columns if 'location' in c.lower()), "Event Location")
    cat_col = next((c for c in df_events.columns if 'group' in c.lower() or 'category' in c.lower()), "Master Group")

    if dur_col in df_events.columns:
        df_events[dur_col] = pd.to_numeric(df_events[dur_col], errors='coerce').fillna(0)

    return df_staff, df_events, dur_col, date_col, loc_col, cat_col

df_staff, df_events, dur_col, date_col, loc_col, cat_col = load_data()

# --- 3. STABLE TAB UI ---
tab_list = ["📊 Dashboard", "👤 Staff Details", "➕ Add Data", "🗓️ Event Logs", "🏆 Leaderboard"]
tabs = st.tabs(tab_list)

# --- TAB 1: DASHBOARD ---
with tabs[0]:
    st.title("📊 Strategic Overview")
    if not df_staff.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Registered", len(df_staff))
        
        # Categorization logic
        def get_cat(b):
            b = str(b).strip()
            if b in ["Assist.Technician", "Driver"]: return "AT"
            if b in ["Master in Fireworks", "Pro in Fireworks", "Team Leader"]: return "TL"
            return "Other"
        
        df_staff['Category_Group'] = df_staff['Leader Badge'].apply(get_cat)
        c2.metric("Team Leaders", len(df_staff[df_staff['Category_Group'] == "TL"]))
        c3.metric("Assist. Technicians", len(df_staff[df_staff['Category_Group'] == "AT"]))
        
        st.write("---")
        st.subheader("Event Category Summary")
        if cat_col in df_events.columns:
            summary = df_events.groupby(cat_col).size().reset_index(name='Total Events')
            st.table(summary)

# --- TAB 2: STAFF DETAILS ---
with tabs[1]:
    st.title("👤 Staff Details")
    f1, f2 = st.columns([1, 2])
    with f1:
        opts = ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"]
        role_filter = st.multiselect("Filter Table:", options=opts, default=opts)
    with f2:
        # 'key' is essential here to stop shifting
        search_sn = st.text_input("🔍 Search SN for Profile", key="staff_search_box")

    display_df = df_staff[df_staff['Leader Badge'].isin(role_filter)]
    st.dataframe(display_df[['SN', 'Rank', 'Name', 'Unit', 'Contact', 'Leader Badge']], use_container_width=True, hide_index=True)

    if search_sn:
        clean_sn = str(search_sn).strip()
        match = df_staff[df_staff['SN'] == clean_sn]
        if not match.empty:
            p = match.iloc[0]
            st.markdown("---")
            st.header(f"Profile: {p['Name']}")
            p_history = df_events[df_events['SN'] == clean_sn]
            
            m1, m2 = st.columns(2)
            m1.metric("Total Events", len(p_history))
            m2.metric("Total Duration", f"{int(p_history[dur_col].sum())} Mins")
            st.dataframe(p_history, use_container_width=True, hide_index=True)

# --- TAB 3: ADD DATA ---
with tabs[2]:
    st.title("➕ Add Data")
    st.info("Ensure column headers in Google Sheets match exactly.")
    st.link_button("Edit Google Sheet", SHEET_EDIT_URL)

# --- TAB 4: EVENT LOGS (LOCATION SEARCH) ---
with tabs[3]:
    st.title("🗓️ Event Logs")
    s_col, d_col = st.columns([2, 1])
    with s_col:
        search_loc = st.text_input("🔍 Search by Location Name", key="location_search_box")
    with d_col:
        all_locs = sorted(df_events[loc_col].unique().tolist()) if loc_col in df_events.columns else []
        selected_loc = st.selectbox("Or Select Location", ["-- All --"] + all_locs)

    filtered_ev = df_events.copy()
    if search_loc:
        filtered_ev = filtered_ev[filtered_ev[loc_col].str.contains(search_loc, case=False, na=False)]
    elif selected_loc != "-- All --":
        filtered_ev = filtered_ev[filtered_ev[loc_col] == selected_loc]

    st.write(f"### Found {len(filtered_ev)} Details")
    st.dataframe(filtered_ev, use_container_width=True, hide_index=True)

# --- TAB 5: LEADERBOARD ---
with tabs[4]:
    st.title("🏆 Leaderboard")
    if not df_events.empty:
        top = df_events['SN'].value_counts().head(10).reset_index()
        top.columns = ['SN', 'Engagements']
        board = pd.merge(top, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
        st.dataframe(board[['Name', 'Rank', 'Engagements']], use_container_width=True, hide_index=True)
