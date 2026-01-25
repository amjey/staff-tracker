import streamlit as st
import pandas as pd

# --- CONFIGURATION ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=5)
def load_data():
    # Load and clean headers
    df_staff = pd.read_csv(DETAILS_URL).rename(columns=lambda x: x.strip())
    df_events = pd.read_csv(EVENTS_URL).rename(columns=lambda x: x.strip())
    
    # Clean SNs to ensure successful matching for the table (removes 'None' issue)
    for df in [df_staff, df_events]:
        df['SN'] = df['SN'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    # --- UPDATED STAFF COUNT LOGIC ---
    # Mapping based on your specific requirements:
    # Assist.Technician -> Assist.Technician
    # Driver -> Assist.Technician
    # Master in Fireworks -> Team Leader
    # Pro in Fireworks -> Team Leader
    def categorize_staff(badge):
        badge_str = str(badge).strip()
        if badge_str in ["Assist.Technician", "Driver"]:
            return "Assist.Technician"
        elif badge_str in ["Master in Fireworks", "Pro in Fireworks"]:
            return "Team Leader"
            elif badge_str in ["Team Leader"]:
            return "Team Leader"
        return "Unassigned" # Fallback for other values

    df_staff['Category'] = df_staff['Leader Badge'].apply(categorize_staff)
    
    return df_staff, df_events

df_staff, df_events = load_data()

st.title("📊 System Analytics")

# 1. STAFF TOTALS (Targeting correct counts based on new rules)
c1, c2, c3 = st.columns(3)
total_reg = len(df_staff[df_staff['SN'] != 'nan'])
team_leaders = len(df_staff[df_staff['Category'] == "Team Leader"])
assist_techs = len(df_staff[df_staff['Category'] == "Assist.Technician"])

c1.metric("Total Registered", total_reg)
c2.metric("Team Leaders", team_leaders)
c3.metric("Assist. Technicians", assist_techs)

st.write("---")

# 2. EVENTS BY CATEGORY (REMOVING THE "0, 1, 2" INDEX)
st.subheader("Events by Category")
unique_events_df = df_events.drop_duplicates(subset=['Event Name', 'Event Location'])

col_chart, col_table = st.columns([1, 1])

with col_table:
    st.write("**Category Summary Table**")
    cat_counts = unique_events_df['Master Group'].value_counts().reset_index()
    cat_counts.columns = ['Event Category', 'Count']
    
    # FIX: hide_index=True removes the leading 0, 1, 2 column
    st.dataframe(cat_counts, use_container_width=True, hide_index=True)

with col_chart:
    st.write("**Distribution Chart**")
    chart_data = unique_events_df['Master Group'].value_counts()
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

# Merge with Staff Details to populate the table with real data instead of 'None'
event_attendance = loc_data[loc_data['Event Name'] == sel_event]
detailed_staff_list = pd.merge(
    event_attendance[['SN']], 
    df_staff[['SN', 'Rank', 'Name', 'Unit', 'Contact']], 
    on='SN', 
    how='inner'
)

st.write(f"#### Staff On-Site ({len(detailed_staff_list)} members found)")
# hide_index=True here as well for a professional look
st.dataframe(
    detailed_staff_list[['Rank', 'Name', 'Unit', 'Contact']], 
    use_container_width=True, 
    hide_index=True
)

