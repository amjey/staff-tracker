import streamlit as st
import pandas as pd

# --- CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=10)
def load_data():
    # Load and force strip whitespaces from column headers to prevent KeyErrors
    df_staff = pd.read_csv(DETAILS_URL)
    df_staff.columns = df_staff.columns.str.strip()
    
    df_events = pd.read_csv(EVENTS_URL)
    df_events.columns = df_events.columns.str.strip()
    
    # Validation: Filter out completely empty rows
    df_staff = df_staff.dropna(subset=['SN'])
    df_events = df_events.dropna(subset=['SN'])
    
    # CRITICAL: Categorization Logic for Staff Totals (Target: 151/731)
    # Drivers = Assist.Technician, everyone else = Team Leader
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
    st.title("📊 Event Location Dashboard")

    # --- 1. STAFF TOTALS (Resolves 878/4 Error) ---
    st.subheader("Staff Totals")
    s1, s2, s3 = st.columns(3)
    
    total_reg = len(df_staff)
    assist_techs = len(df_staff[df_staff['Category'] == "Assist.Technician"])
    team_leaders = total_reg - assist_techs
    
    s1.metric("Total Registered", total_reg)
    s2.metric("Team Leaders", team_leaders)
    s3.metric("Assist. Technicians", assist_techs)

    st.write("---")

    # --- 2. UNIQUE EVENTS & LOCATION TABLE ---
    st.subheader("Events Overview")
    
    # Identify unique events
    unique_cols = ['Event Name', 'Event Location']
    if 'Date' in df_events.columns:
        unique_cols.append('Date')
    
    unique_events_df = df_events.drop_duplicates(subset=unique_cols)
    
    m1, m2 = st.columns(2)
    m1.metric("Total Unique Events", len(unique_events_df))
    m2.metric("Total Staff Engagements", len(df_events))

    # ADDED: Event Category Table (By Master Group)
    st.write("#### Event Categories Summary")
    if 'Master Group' in unique_events_df.columns:
        cat_summary = unique_events_df['Master Group'].value_counts().reset_index()
        cat_summary.columns = ['Category (Master Group)', 'Unique Event Count']
        st.table(cat_summary) # Display as a clean table
    else:
        st.warning("Master Group column not found in data.")

    # Location Bar Chart
    st.write("#### Events by Location")
    loc_counts = unique_events_df['Event Location'].value_counts()
    st.bar_chart(loc_counts)

    # --- 3. LOCATION DEEP-DIVE ---
    st.write("---")
    st.subheader("Location Deep-Dive")
    
    sel_loc = st.selectbox("Select Location", sorted(df_events['Event Location'].unique()))
    loc_data = df_events[df_events['Event Location'] == sel_loc]
    
    sel_sub = st.selectbox(f"Select Event at {sel_loc}", sorted(loc_data['Event Name'].unique()))
    final_view = loc_data[loc_data['Event Name'] == sel_sub]
    
    st.write(f"**Staff Present at {sel_sub} ({len(final_view)}):**")
    display_cols = [c for c in ['SN', 'Name', 'Rank', 'Unit'] if c in final_view.columns]
    st.dataframe(final_view[display_cols], use_container_width=True, hide_index=True)

with tab3:
    st.title("🏆 Leaderboard")
    top_staff = df_events['SN'].value_counts().head(10).reset_index()
    top_staff.columns = ['SN', 'Engagements']
    top_staff = pd.merge(top_staff, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.table(top_staff[['Name', 'Rank', 'Engagements']])
