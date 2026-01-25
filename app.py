import streamlit as st
import pandas as pd

# --- CONFIGURATION ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=5)
def load_data():
    # Load and immediately strip any accidental spaces from headers
    df_staff = pd.read_csv(DETAILS_URL).rename(columns=lambda x: x.strip())
    df_events = pd.read_csv(EVENTS_URL).rename(columns=lambda x: x.strip())
    
    # --- FIX FOR "NONE" VALUES ---
    # We clean SNs to be pure strings without decimals (123.0 -> 123)
    # This ensures the 'Details' sheet can match the 'Event' sheet
    for df in [df_staff, df_events]:
        df['SN'] = df['SN'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    # Categorization for Staff Totals (Target: 151/731)
    df_staff['Category'] = df_staff['Leader Badge'].apply(
        lambda x: "Assist.Technician" if str(x).strip().lower() == "driver" else "Team Leader"
    )
    
    return df_staff, df_events

df_staff, df_events = load_data()

st.title("📊 System Analytics")

# 1. METRICS (Target: 151 Team Leaders / 731 Technicians)
c1, c2, c3 = st.columns(3)
total_reg = len(df_staff)
assist_techs = len(df_staff[df_staff['Category'] == "Assist.Technician"])
team_leaders = total_reg - assist_techs

c1.metric("Total Registered", total_reg)
c2.metric("Team Leaders", team_leaders)
c3.metric("Assist. Technicians", assist_techs)

st.write("---")

# 2. EVENTS BY CATEGORY (FIXING THE "0" INDEX COLUMN)
st.subheader("Events by Category")
unique_events_df = df_events.drop_duplicates(subset=['Event Name', 'Event Location'])

col_chart, col_table = st.columns([1, 1])

with col_table:
    st.write("**Category Summary Table**")
    cat_counts = unique_events_df['Master Group'].value_counts().reset_index()
    cat_counts.columns = ['Event Category', 'Count']
    
    # FIX: Using st.dataframe with hide_index=True removes the 0, 1, 2 column
    st.dataframe(cat_counts, use_container_width=True, hide_index=True)

with col_chart:
    st.write("**Distribution Chart**")
    chart_data = unique_events_df['Master Group'].value_counts()
    # Simple bar chart grounded at zero
    st.bar_chart(chart_data, color="#0072B2")

st.write("---")

# 3. DEPLOYMENT DETAILS (FIXING THE "NONE" VALUES)
st.subheader("📍 Deployment Details by Location")

f1, f2 = st.columns(2)
with f1:
    sel_loc = st.selectbox("Select Location", sorted(df_events['Event Location'].unique()))
with f2:
    loc_data = df_events[df_events['Event Location'] == sel_loc]
    sel_event = st.selectbox(f"Select Event at {sel_loc}", sorted(loc_data['Event Name'].unique()))

# Filter the specific event attendance
event_attendance = loc_data[loc_data['Event Name'] == sel_event]

# DATA JOIN: This pulls Rank, Name, Unit, and Contact from the 'Details' sheet 
# linking them via the SN (Serial Number)
detailed_staff_list = pd.merge(
    event_attendance[['SN']], 
    df_staff[['SN', 'Rank', 'Name', 'Unit', 'Contact']], 
    on='SN', 
    how='inner' # 'inner' only shows people who actually exist in your Details sheet
)

st.write(f"#### Staff On-Site ({len(detailed_staff_list)} members)")

# FIX: hide_index=True here as well to keep the table clean
st.dataframe(
    detailed_staff_list[['Rank', 'Name', 'Unit', 'Contact']], 
    use_container_width=True, 
    hide_index=True
)
