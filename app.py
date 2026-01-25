import streamlit as st
import pandas as pd

# --- CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=10)
def load_data():
    # Load and clean headers to prevent KeyErrors seen in previous attempts
    df_staff = pd.read_csv(DETAILS_URL)
    df_staff.columns = df_staff.columns.str.strip()
    
    df_events = pd.read_csv(EVENTS_URL)
    df_events.columns = df_events.columns.str.strip()
    
    # Validation: Filter out completely empty rows
    df_staff = df_staff.dropna(subset=['SN'])
    df_events = df_events.dropna(subset=['SN'])
    
    # FIX: Robust Categorization Logic for Staff Totals
    # Maps 'Driver' to Assist. Technician and others to Team Leader
    df_staff['Category'] = df_staff['Leader Badge'].apply(
        lambda x: "Assist.Technician" if str(x).strip().lower() == "driver" else "Team Leader"
    )
    
    return df_staff, df_events

# --- SECURITY ---
if "auth" not in st.session_state:
    st.title("🔒 Staff Management Login")
    pwd = st.text_input("Enter Admin Password", type="password")
    if st.button("Login"):
        if pwd == "Admin@2026":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Invalid Password")
    st.stop()

df_staff, df_events = load_data()

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "👤 Staff Details", "🏆 Leaderboard"])

with tab1:
    st.title("📊 Strategic Overview")

    # --- 1. CORRECTED STAFF TOTALS (151 / 731) ---
    st.subheader("Staff Totals")
    s1, s2, s3 = st.columns(3)
    
    total_reg = len(df_staff)
    assist_techs = len(df_staff[df_staff['Category'] == "Assist.Technician"])
    team_leaders = total_reg - assist_techs
    
    s1.metric("Total Registered", total_reg)
    s2.metric("Team Leaders", team_leaders)
    s3.metric("Assist. Technicians", assist_techs)

    st.write("---")

    # --- 2. THE NEW CATEGORY & EVENT COUNT TABLE ---
    st.subheader("Events by Category")
    
    # Identify unique events to avoid counting all 1734 staff entries as separate events
    unique_event_cols = ['Event Name', 'Event Location']
    if 'Date' in df_events.columns:
        unique_event_cols.append('Date')
    
    unique_events_df = df_events.drop_duplicates(subset=unique_event_cols)
    
    col_chart, col_table = st.columns([1, 1])
    
    with col_table:
        st.write("**Event Category Summary Table**")
        if 'Master Group' in unique_events_df.columns:
            # Create the table you requested
            cat_table = unique_events_df['Master Group'].value_counts().reset_index()
            cat_table.columns = ['Event Category', 'Unique Event Count']
            st.table(cat_table)
        else:
            st.info("Master Group column not found.")

    with col_chart:
        st.write("**Event Distribution Chart**")
        if 'Master Group' in unique_events_df.columns:
            st.bar_chart(unique_events_df['Master Group'].value_counts())

    # --- 3. LOCATION DRILL-DOWN ---
    st.write("---")
    st.subheader("Location Drill-Down")
    
    sel_loc = st.selectbox("Select Location", sorted(df_events['Event Location'].unique()))
    loc_data = df_events[df_events['Event Location'] == sel_loc]
    
    sel_sub = st.selectbox(f"Select Event at {sel_loc}", sorted(loc_data['Event Name'].unique()))
    final_view = loc_data[loc_data['Event Name'] == sel_sub]
    
    st.write(f"**Staff Engaged at {sel_sub} ({len(final_view)}):**")
    # Using safe column display to avoid KeyErrors
    display_cols = [c for c in ['SN', 'Name', 'Rank', 'Unit'] if c in final_view.columns]
    st.dataframe(final_view[display_cols], use_container_width=True, hide_index=True)

with tab3:
    st.title("🏆 Leaderboard")
    top_staff = df_events['SN'].value_counts().head(10).reset_index()
    top_staff.columns = ['SN', 'Engagements']
    top_staff = pd.merge(top_staff, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.table(top_staff[['Name', 'Rank', 'Engagements']])
