import streamlit as st
import pandas as pd

# --- CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=10)
def load_data():
    # Load and clean whitespace
    df_staff = pd.read_csv(DETAILS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df_events = pd.read_csv(EVENTS_URL).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    # Remove phantom empty rows
    df_staff = df_staff.dropna(subset=['SN'])
    df_events = df_events.dropna(subset=['SN'])
    
    return df_staff, df_events

df_staff, df_events = load_data()

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Location Dashboard", "👤 Staff Details", "🏆 Leaderboard"])

with tab1:
    st.title("📊 Event Location Analysis")

    # --- 1. STAFF REGISTRATION TOTALS ---
    # Strictly categorizing by Column F (Leader Badge)
    drivers = df_staff[df_staff['Leader Badge'].str.lower() == 'driver']
    t_leaders = df_staff[df_staff['Leader Badge'].str.lower() != 'driver']

    st.subheader("Staff Totals")
    s1, s2, s3 = st.columns(3)
    s1.metric("Total Registered", len(df_staff))
    s2.metric("Team Leaders", len(t_leaders))
    s3.metric("Assist. Technicians", len(drivers))

    st.write("---")

    # --- 2. THE NEW LOCATION LOGIC ---
    st.subheader("Events by Location")
    
    # We define a "Unique Event" as a combination of Name + Location + Date
    # This prevents counting individual staff rows as separate events
    unique_events = df_events.drop_duplicates(subset=['Event Name', 'Event Location', 'Date'])
    
    m1, m2 = st.columns(2)
    m1.metric("Total Unique Events", len(unique_events))
    m2.metric("Total Staff Engagements", len(df_events))

    # Bar chart showing which location has the most events
    location_counts = unique_events['Event Location'].value_counts()
    
    col_chart, col_data = st.columns([2, 1])
    with col_chart:
        st.bar_chart(location_counts)
    
    with col_data:
        st.write("**Events per Location**")
        st.dataframe(location_counts, use_container_width=True)

    # --- 3. NESTED FILTERING (SUB-CATEGORIES) ---
    st.write("---")
    st.subheader("Deep Dive by Location")
    
    # Filter 1: Pick Location
    loc_list = sorted(df_events['Event Location'].unique())
    selected_loc = st.selectbox("Select a Location to see Events", loc_list)

    # Filter 2: Pick Sub-Category (Event Name) based on that Location
    loc_filtered_df = df_events[df_events['Event Location'] == selected_loc]
    event_list = sorted(loc_filtered_df['Event Name'].unique())
    selected_event = st.selectbox(f"Select Event in {selected_loc}", event_list)

    # Final View
    final_view = loc_filtered_df[loc_filtered_df['Event Name'] == selected_event]
    
    st.write(f"#### Staff present at: {selected_event}")
    st.dataframe(final_view[['SN', 'Name', 'Rank', 'Master Group']], use_container_width=True, hide_index=True)

with tab3:
    st.title("🏆 Leaderboard")
    # Top 5 by row count (Engagements)
    top_5 = df_events['SN'].value_counts().head(5).reset_index()
    top_5.columns = ['SN', 'Engagements']
    top_5 = pd.merge(top_5, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.table(top_staff[['Name', 'Rank', 'Engagements']])
