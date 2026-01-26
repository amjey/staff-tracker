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

    display_df = df_staff[df_staff['Leader Badge'].isin(role_filter)]
    st.dataframe(display_df[['SN', 'Rank', 'Name', 'Unit', 'Contact', 'Leader Badge']], use_container_width=True, hide_index=True)

    if search_sn:
        clean_in = str(search_sn).strip()
        match = df_staff[df_staff['SN'] == clean_in]
        if not match.empty:
            p = match.iloc[0]
            st.markdown("---")
            st.header(f"Profile: {p['Name']}")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Rank", p['Rank']); m2.metric("Unit", p['Unit'])
            m3.metric("Contact", p['Contact']); m4.metric("Badge", p['Leader Badge'])
            
            p_history = df_events[df_events['SN'] == clean_in]
            st.metric("Total Events", len(p_history))
            st.metric("Total Duration", f"{int(p_history[dur_col].sum())} Mins")
            st.dataframe(p_history, use_container_width=True, hide_index=True)

# --- TAB 4: EVENT LOGS (LOCATION SEARCH) ---
with t4:
    st.title("🗓️ Event Logs & Location Search")
    
    # 1. Search Interface
    search_col, filter_col = st.columns([2, 1])
    
    with search_col:
        # Search by Location Name
        search_loc = st.text_input("🔍 Search by Location (e.g. Soneva, Jumeirah)", key="loc_search_anchor")
    
    with filter_col:
        # Dropdown for all locations found in the sheet
        all_locs = sorted(df_events[loc_col].unique().tolist())
        selected_loc = st.selectbox("Or Select from List", ["-- All Locations --"] + all_locs)

    # 2. Filter Logic
    filtered_df = df_events.copy()
    if search_loc:
        filtered_df = filtered_df[filtered_df[loc_col].str.contains(search_loc, case=False, na=False)]
    elif selected_loc != "-- All Locations --":
        filtered_df = filtered_df[filtered_df[loc_col] == selected_loc]

    # 3. Display Details
    st.write(f"### Found {len(filtered_df)} Event Entries")
    
    if not filtered_df.empty:
        # Show Summary Stats for that Location
        s1, s2 = st.columns(2)
        total_loc_mins = filtered_df[dur_col].sum()
        unique_events_count = len(filtered_df.drop_duplicates(subset=['Event Name', date_col] if date_col in filtered_df.columns else ['Event Name']))
        
        s1.metric("Events at this Location", unique_events_count)
        s2.metric("Total Pyro Duration", f"{int(total_loc_mins)} Mins")

        st.write("---")
        # Full Detail Table
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    else:
        st.info("No events found for this location.")

# --- TABS 3 & 5 (Form & Leaderboard) ---
with t3:
    st.title("➕ Add Data")
    st.info("Check Google Sheets for live updates to SN, Rank, and Unit.")
    st.link_button("Edit Google Sheet", SHEET_EDIT_URL)

with t5:
    st.title("🏆 Leaderboard")
    top = df_events['SN'].value_counts().head(10).reset_index()
    top.columns = ['SN', 'Engagements']
    board = pd.merge(top, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.dataframe(board[['Name', 'Rank', 'Engagements']], use_container_width=True, hide_index=True)
