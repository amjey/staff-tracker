import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=10)
def load_data():
    df_staff = pd.read_csv(DETAILS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df_events = pd.read_csv(EVENTS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    # Logic: "Driver" in Leader Badge -> Assist.Technician, else Team Leader
    df_staff['Category'] = df_staff['Leader Badge'].apply(
        lambda x: "Assist.Technician" if str(x).lower() == "driver" else "Team Leader"
    )
    
    # Ensure SN is string for matching; fix potential search errors
    df_staff['SN'] = df_staff['SN'].astype(str)
    df_events['SN'] = df_events['SN'].astype(str)
    
    # Pre-calculate display name for selectors
    df_staff['Display'] = df_staff['SN'] + " - " + df_staff['Name'] + " (" + df_staff['Rank'] + ")"
    return df_staff, df_events

# --- SECURITY ---
if "auth" not in st.session_state:
    st.title("🔒 Staff Management Login")
    if st.text_input("Password", type="password") == "Admin@2026":
        if st.button("Login"):
            st.session_state.auth = True
            st.rerun()
    st.stop()

df_staff, df_events = load_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("🔍 Global Search")
# Fixed search logic to prevent the 'AttributeError' from your first image
search_sn = st.sidebar.text_input("Search by SN")
category_filter = st.sidebar.multiselect("Filter by Category", options=["Team Leader", "Assist.Technician"])

filtered_staff = df_staff
if search_sn:
    filtered_staff = filtered_staff[filtered_staff['SN'].str.contains(search_sn, na=False)]
if category_filter:
    filtered_staff = filtered_staff[filtered_staff['Category'].isin(category_filter)]

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "➕ Add Data", "👤 Staff Details", "🗓️ Event Logs", "🏆 Leaderboard"])

with tab2: # ADD DATA IMPROVEMENTS
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("➕ Add New Staff")
        with st.form("staff_form"):
            n_sn = st.text_input("SN")
            n_name = st.text_input("Full Name")
            n_rank = st.text_input("Rank")   # New Field
            n_unit = st.text_input("Unit")   # New Field
            n_badge = st.selectbox("Leader Badge", ["Team Leader", "Driver", "Staff"])
            if st.form_submit_button("Generate Staff Entry"):
                st.info(f"Add to Sheet: {n_sn}, {n_name}, {n_rank}, {n_unit}, {n_badge}")
                st.link_button("Go to Google Sheets", SHEET_EDIT_URL)

    with col_b:
        st.subheader("➕ Add New Event")
        with st.form("event_form"):
            e_name = st.text_input("Event Name")
            e_loc = st.text_input("Location")
            e_dur = st.number_input("Duration (Mins)", min_value=0) # New Field
            # Multi-select using the new Display name (SN + Name + Rank)
            e_staff = st.multiselect("Select Multiple Staff", options=df_staff['Display'].tolist())
            if st.form_submit_button("Generate Event Log"):
                st.success(f"Log {e_name} ({e_dur}m) for {len(e_staff)} staff.")
                st.link_button("Go to Google Sheets", SHEET_EDIT_URL)

with tab3: # STAFF INSIGHT IMPROVEMENTS
    st.title("👤 Staff History")
    # Fixed the "numbers" issue from your second image; now shows Name and Rank
    choice = st.selectbox("Select Staff", options=df_staff['Display'].tolist())
    sel_sn = choice.split(" - ")[0]
    
    s_info = df_staff[df_staff['SN'] == sel_sn].iloc[0]
    st.write(f"### Profile: {s_info['Name']}")
    st.write(f"**Rank:** {s_info['Rank']} | **Unit:** {s_info['Unit']} | **Category:** {s_info['Category']}")
    
    st.write("#### All Attended Events")
    history = df_events[df_events['SN'] == sel_sn]
    st.dataframe(history, use_container_width=True, hide_index=True)

with tab5: # LEADERBOARD IMPROVEMENTS
    st.title("🏆 Leaderboard (Top 5)")
    
    # Calculate Stats
    e_counts = df_events.groupby('SN').size().reset_index(name='Events')
    # If duration column is named exactly 'Duration (Mins)' in your sheet:
    if 'Duration (Mins)' in df_events.columns:
        dur_stats = df_events.groupby('SN')['Duration (Mins)'].sum().reset_index(name='Total Mins')
        leader_df = pd.merge(e_counts, dur_stats, on='SN')
    else:
        leader_df = e_counts
        
    leader_df = pd.merge(leader_df, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    
    c_l1, c_l2 = st.columns(2)
    with c_l1:
        st.subheader("Most Events")
        top_e = leader_df.sort_values('Events', ascending=False).head(5)
        st.table(top_e[['Name', 'Rank', 'Events']])
        
    with c_l2:
        st.subheader("Highest Duration")
        if 'Total Mins' in leader_df.columns:
            top_d = leader_df.sort_values('Total Mins', ascending=False).head(5)
            st.table(top_d[['Name', 'Rank', 'Total Mins']])
