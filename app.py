import streamlit as st
import pandas as pd

# --- CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=2)
def load_data():
    df_staff = pd.read_csv(DETAILS_URL).rename(columns=lambda x: x.strip())
    df_events = pd.read_csv(EVENTS_URL).rename(columns=lambda x: x.strip())
    
    # 1. Clean SN and Contact (Remove .0)
    for df in [df_staff, df_events]:
        if 'SN' in df.columns:
            df['SN'] = df['SN'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    if 'Contact' in df_staff.columns:
        df_staff['Contact'] = df_staff['Contact'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    # 2. Fix Duration Math (Search for the specific column)
    # This ensures your "3 mins" event is counted
    dur_col = next((c for c in ['Event duration(Mins)', 'Duration', 'duration'] if c in df_events.columns), None)
    if dur_col:
        df_events[dur_col] = pd.to_numeric(df_events[dur_col], errors='coerce').fillna(0)

    # 3. Categorization Logic (All 5 Categories)
    def categorize_staff(badge):
        b = str(badge).strip()
        # Assistants
        if b in ["Assist.Technician", "Driver"]: 
            return "Assist.Technician"
        # Leaders
        if b in ["Master in Fireworks", "Pro in Fireworks", "Team Leader"]: 
            return "Team Leader"
        return "Unassigned"

    df_staff['Category'] = df_staff['Leader Badge'].apply(categorize_staff)
    return df_staff, df_events, dur_col

df_staff, df_events, dur_col = load_data()

# --- TABS ---
# Wrapping everything in the tab objects to prevent jumping
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard", "👤 Staff Details", "➕ Add Data", "🗓️ Event Logs", "🏆 Leaderboard"
])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.title("📊 Strategic Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Registered", len(df_staff))
    c2.metric("Team Leaders", len(df_staff[df_staff['Category'] == "Team Leader"]))
    c3.metric("Assist. Technicians", len(df_staff[df_staff['Category'] == "Assist.Technician"]))
    
    st.write("---")
    unique_ev = df_events.drop_duplicates(subset=['Event Name', 'Event Location'])
    st.subheader("Event Categories")
    st.bar_chart(unique_ev['Master Group'].value_counts(), color="#0072B2")

# --- TAB 2: STAFF DETAILS (STABLE SEARCH) ---
with tab2:
    st.title("👤 Staff Details")
    
    # Filtering Logic
    f1, f2 = st.columns([1, 2])
    with f1:
        # Filter allows selecting the specific badges or grouped roles
        role_filter = st.multiselect("Filter Table by Role:", 
                                     options=["Team Leader", "Assist.Technician"], 
                                     default=["Team Leader", "Assist.Technician"])
    with f2:
        # Key prevents the tab-switching issue
        search_sn = st.text_input("🔍 Search by SN to view Profile", key="search_box")

    # Filtered Table
    display_df = df_staff[df_staff['Category'].isin(role_filter)]
    
    st.write("### Staff Directory")
    st.dataframe(display_df[['SN', 'Rank', 'Name', 'Unit', 'Contact', 'Leader Badge']], 
                 use_container_width=True, hide_index=True)

    # Individual Profile (Triggered by Search)
    if search_sn:
        profile = df_staff[df_staff['SN'] == search_sn]
        if not profile.empty:
            p = profile.iloc[0]
            st.markdown("---")
            st.header(f"Profile: {p['Name']}")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Rank", p['Rank'])
            m2.metric("Unit", p['Unit'])
            m3.metric("Contact", p['Contact'])
            m4.metric("Role", p['Category'])
            
            # History Math
            history = df_events[df_events['SN'] == search_sn]
            total_events = len(history)
            total_mins = history[dur_col].sum() if dur_col else 0
            
            e1, e2 = st.columns(2)
            e1.metric("Total Events Attended", total_events)
            e2.metric("Total Duration", f"{int(total_mins)} Mins")
            
            st.subheader("Attendance Log")
            st.dataframe(history, use_container_width=True, hide_index=True)
        else:
            st.warning("No staff found with that SN.")

# --- TAB 3: FORMS ---
with tab3:
    st.title("➕ Add Data")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Add Staff")
        with st.form("staff_f"):
            st.text_input("SN"); st.text_input("Full Name"); st.text_input("Rank")
            st.text_input("Unit"); st.text_input("Contact")
            st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
            if st.form_submit_button("Submit"): st.link_button("Open Sheet", SHEET_EDIT_URL)
    with col_b:
        st.subheader("Log Event")
        with st.form("event_f"):
            st.text_input("Event Name"); st.text_input("Event Location")
            st.date_input("Event Date"); st.number_input("Event duration(Mins)", min_value=1)
            if st.form_submit_button("Log"): st.link_button("Open Sheet", SHEET_EDIT_URL)

# --- TAB 4 & 5 ---
with tab4:
    st.title("🗓️ Event Logs")
    st.dataframe(df_events, use_container_width=True, hide_index=True)

with tab5:
    st.title("🏆 Leaderboard")
    top = df_events['SN'].value_counts().head(10).reset_index()
    top.columns = ['SN', 'Engagements']
    board = pd.merge(top, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.dataframe(board[['Name', 'Rank', 'Engagements']], use_container_width=True, hide_index=True)
