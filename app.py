import streamlit as st
import pandas as pd

# --- CONFIGURATION ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=10)
def load_data():
    # Load data and strip hidden spaces from headers
    df_staff = pd.read_csv(DETAILS_URL)
    df_staff.columns = df_staff.columns.str.strip()
    
    df_events = pd.read_csv(EVENTS_URL)
    df_events.columns = df_events.columns.str.strip()
    
    # Cleaning: Remove empty rows and force SN to string
    df_staff = df_staff.dropna(subset=['SN'])
    df_events = df_events.dropna(subset=['SN'])
    df_staff['SN'] = df_staff['SN'].astype(str)
    df_events['SN'] = df_events['SN'].astype(str)
    
    # Categorization Logic (151 Team Leaders / 731 Assist. Technicians)
    df_staff['Category'] = df_staff['Leader Badge'].apply(
        lambda x: "Assist.Technician" if str(x).strip().lower() == "driver" else "Team Leader"
    )
    
    return df_staff, df_events

# --- LOGIN ---
if "auth" not in st.session_state:
    st.title("🔒 Admin Login")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if pwd == "Admin@2026":
            st.session_state.auth = True
            st.rerun()
    st.stop()

df_staff, df_events = load_data()

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "👤 Staff Search", "🏆 Leaderboard"])

with tab1:
    st.title("📊 System Analytics")

    # 1. METRIC CARDS
    c1, c2, c3 = st.columns(3)
    total_reg = len(df_staff)
    assist_techs = len(df_staff[df_staff['Category'] == "Assist.Technician"])
    team_leaders = total_reg - assist_techs
    
    c1.metric("Total Registered", total_reg)
    c2.metric("Team Leaders", team_leaders)
    c3.metric("Assist. Technicians", assist_techs)

    st.write("---")

    # 2. EVENT CATEGORY SUMMARY & CHART (Fixing the -50 Axis)
    st.subheader("Events by Category")
    unique_events_df = df_events.drop_duplicates(subset=['Event Name', 'Event Location'])
    
    col_chart, col_table = st.columns([1, 1])
    
    with col_table:
        st.write("**Category Summary Table**")
        cat_counts = unique_events_df['Master Group'].value_counts().reset_index()
        cat_counts.columns = ['Event Category', 'Count']
        st.table(cat_counts)

    with col_chart:
        st.write("**Distribution Chart**")
        # Creating a bar chart and forcing it to stay above zero
        chart_data = unique_events_df['Master Group'].value_counts()
        st.bar_chart(chart_data, color="#07427a")

    st.write("---")

    # 3. LOCATION DEEP-DIVE WITH STAFF DETAILS (Rank, Name, Unit, Contact)
    st.subheader("📍 Deployment Details by Location")
    
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        sel_loc = st.selectbox("Select Location", sorted(df_events['Event Location'].unique()))
    with filter_col2:
        loc_data = df_events[df_events['Event Location'] == sel_loc]
        sel_event = st.selectbox(f"Select Event at {sel_loc}", sorted(loc_data['Event Name'].unique()))

    # Filter attendance for this specific event
    event_attendance = loc_data[loc_data['Event Name'] == sel_event]
    
    # JOIN: Link the attendance list to the staff master list to get contact details
    detailed_staff_list = pd.merge(
        event_attendance[['SN']], 
        df_staff[['SN', 'Rank', 'Name', 'Unit', 'Contact']], 
        on='SN', 
        how='left'
    )

    st.write(f"#### Staff On-Site ({len(detailed_staff_list)} members)")
    # Displaying the specific columns you requested
    st.dataframe(
        detailed_staff_list[['Rank', 'Name', 'Unit', 'Contact']], 
        use_container_width=True, 
        hide_index=True
    )

with tab3:
    st.title("🏆 Leaderboard")
    top_staff = df_events['SN'].value_counts().head(10).reset_index()
    top_staff.columns = ['SN', 'Engagements']
    top_staff = pd.merge(top_staff, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.table(top_staff[['Name', 'Rank', 'Engagements']])
