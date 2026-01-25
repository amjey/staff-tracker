import streamlit as st
import pandas as pd

# --- CONFIGURATION ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=10)
def load_data():
    # Load and clean headers
    df_staff = pd.read_csv(DETAILS_URL)
    df_staff.columns = df_staff.columns.str.strip()
    
    df_events = pd.read_csv(EVENTS_URL)
    df_events.columns = df_events.columns.str.strip()
    
    # CRITICAL: Force SN to String in BOTH sheets to ensure the match works
    df_staff = df_staff.dropna(subset=['SN'])
    df_events = df_events.dropna(subset=['SN'])
    df_staff['SN'] = df_staff['SN'].astype(str).str.strip()
    df_events['SN'] = df_events['SN'].astype(str).str.strip()
    
    # Categorization Logic (Target: 151 Team Leaders / 731 Technicians)
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

# --- DASHBOARD ---
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

# 2. EVENT CATEGORY SUMMARY & CLEAN CHART (No -50 padding)
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
    chart_data = unique_events_df['Master Group'].value_counts()
    # Simple bar chart config to prevent Y-axis from dipping below zero
    st.bar_chart(chart_data, y_label="Unique Events", color="#0072B2")

st.write("---")

# 3. DEPLOYMENT DETAILS (Pulling from Details Sheet)
st.subheader("📍 Deployment Details by Location")

f1, f2 = st.columns(2)
with f1:
    sel_loc = st.selectbox("Select Location", sorted(df_events['Event Location'].unique()))
with f2:
    loc_data = df_events[df_events['Event Location'] == sel_loc]
    sel_event = st.selectbox(f"Select Event at {sel_loc}", sorted(loc_data['Event Name'].unique()))

# Filter attendance for this specific event
event_attendance = loc_data[loc_data['Event Name'] == sel_event]

# FIX FOR "NONE" VALUES: 
# We perform a left join with the cleaned staff details sheet
detailed_staff_list = pd.merge(
    event_attendance[['SN']], 
    df_staff[['SN', 'Rank', 'Name', 'Unit', 'Contact']], 
    on='SN', 
    how='left'
)

st.write(f"#### Staff On-Site ({len(detailed_staff_list)} members)")
# If SNs matched correctly, these columns will no longer be "None"
st.dataframe(
    detailed_staff_list[['Rank', 'Name', 'Unit', 'Contact']], 
    use_container_width=True, 
    hide_index=True
)
