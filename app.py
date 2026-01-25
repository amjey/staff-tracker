import streamlit as st
import pandas as pd

# --- CONFIGURATION ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=5)
def load_data():
    # Load and clean headers
    df_staff = pd.read_csv(DETAILS_URL).rename(columns=lambda x: x.strip())
    df_events = pd.read_csv(EVENTS_URL).rename(columns=lambda x: x.strip())
    
    # Clean SNs to ensure successful matching (removes 'None' issue)
    for df in [df_staff, df_events]:
        df['SN'] = df['SN'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    # --- YOUR UPDATED STAFF COUNT LOGIC ---
    def categorize_staff(badge):
        badge_str = str(badge).strip()
        if badge_str in ["Assist.Technician", "Driver"]:
            return "Assist.Technician"
        elif badge_str in ["Master in Fireworks", "Pro in Fireworks", "Team Leader"]:
            return "Team Leader"
        return "Unassigned"

    df_staff['Category'] = df_staff['Leader Badge'].apply(categorize_staff)
    return df_staff, df_events

# --- SECURITY ---
if "auth" not in st.session_state:
    st.title("🔒 Admin Login")
    pwd = st.text_input("Enter Admin Password", type="password")
    if st.button("Login"):
        if pwd == "Admin@2026":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Invalid Password")
    st.stop()

df_staff, df_events = load_data()

# --- TABS NAVIGATION ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard", "➕ Add Data", "👤 Staff Search", "🗓️ Event Logs", "🏆 Leaderboard"
])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.title("📊 System Analytics")
    c1, c2, c3 = st.columns(3)
    total_reg = len(df_staff[df_staff['SN'] != 'nan'])
    team_leaders = len(df_staff[df_staff['Category'] == "Team Leader"])
    assist_techs = len(df_staff[df_staff['Category'] == "Assist.Technician"])

    c1.metric("Total Registered", total_reg)
    c2.metric("Team Leaders", team_leaders)
    c3.metric("Assist. Technicians", assist_techs)

    st.write("---")
    st.subheader("Events by Category")
    unique_events_df = df_events.drop_duplicates(subset=['Event Name', 'Event Location'])
    col_chart, col_table = st.columns([1, 1])

    with col_table:
        st.write("**Category Summary Table**")
        cat_counts = unique_events_df['Master Group'].value_counts().reset_index()
        cat_counts.columns = ['Event Category', 'Count']
        st.dataframe(cat_counts, use_container_width=True, hide_index=True)

    with col_chart:
        st.write("**Distribution Chart**")
        chart_data = unique_events_df['Master Group'].value_counts()
        st.bar_chart(chart_data, color="#0072B2")

# --- TAB 2: ADD DATA (FORMS) ---
with tab2:
    st.title("➕ Data Management")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Add Staff Info")
        with st.form("staff_form"):
            st.text_input("SN")
            st.text_input("Full Name")
            st.text_input("Rank")
            st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
            if st.form_submit_button("Submit Staff"):
                st.link_button("Paste into Google Sheets", SHEET_EDIT_URL)
    with col_b:
        st.subheader("Log New Event")
        with st.form("event_form"):
            st.text_input("Event Name")
            st.text_input("Event Location")
            st.multiselect("Select Staff", options=df_staff['Name'].tolist())
            if st.form_submit_button("Submit Event"):
                st.link_button("Paste into Google Sheets", SHEET_EDIT_URL)

# --- TAB 3: STAFF SEARCH (LOCATION DEEP DIVE) ---
with tab3:
    st.subheader("📍 Deployment Details by Location")
    f1, f2 = st.columns(2)
    with f1:
        sel_loc = st.selectbox("Select Location", sorted(df_events['Event Location'].unique()))
    with f2:
        loc_data = df_events[df_events['Event Location'] == sel_loc]
        sel_event = st.selectbox(f"Select Event at {sel_loc}", sorted(loc_data['Event Name'].unique()))

    event_attendance = loc_data[loc_data['Event Name'] == sel_event]
    detailed_staff_list = pd.merge(
        event_attendance[['SN']], 
        df_staff[['SN', 'Rank', 'Name', 'Unit', 'Contact']], 
        on='SN', how='inner'
    )
    st.write(f"#### Staff On-Site ({len(detailed_staff_list)} members)")
    st.dataframe(detailed_staff_list[['Rank', 'Name', 'Unit', 'Contact']], use_container_width=True, hide_index=True)

# --- TAB 4: EVENT LOGS (FULL LIST) ---
with tab4:
    st.title("🗓️ Master Event Logs")
    st.dataframe(df_events, use_container_width=True, hide_index=True)

# --- TAB 5: LEADERBOARD ---
with tab5:
    st.title("🏆 Leaderboard")
    top_staff = df_events['SN'].value_counts().head(10).reset_index()
    top_staff.columns = ['SN', 'Engagements']
    top_staff = pd.merge(top_staff, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.table(top_staff[['Name', 'Rank', 'Engagements']])
