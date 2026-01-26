import streamlit as st
import pandas as pd

# --- CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
DETAILS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Details"
EVENTS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Event%20Details"

st.set_page_config(page_title="Staff Management Pro", layout="wide")

@st.cache_data(ttl=2)
def load_data():
    df_staff = pd.read_csv(DETAILS_URL).rename(columns=lambda x: x.strip())
    df_events = pd.read_csv(EVENTS_URL).rename(columns=lambda x: x.strip())
    
    # 1. Clean SNs (The Matchmaker)
    clean_sn = lambda x: str(x).split('.')[0].strip()
    df_staff['SN'] = df_staff['SN'].apply(clean_sn)
    df_events['SN'] = df_events['SN'].apply(clean_sn)
    
    # 2. Find Duration & Date Columns Dynamically (Prevents KeyErrors)
    dur_col = next((c for c in df_events.columns if 'duration' in c.lower()), None)
    date_col = next((c for c in df_events.columns if 'date' in c.lower()), None)
    loc_col = next((c for c in df_events.columns if 'location' in c.lower()), None)
    cat_col = next((c for c in df_events.columns if 'group' in c.lower() or 'category' in c.lower()), None)

    if dur_col:
        df_events[dur_col] = pd.to_numeric(df_events[dur_col], errors='coerce').fillna(0)
    
    return df_staff, df_events, dur_col, date_col, loc_col, cat_col

df_staff, df_events, dur_col, date_col, loc_col, cat_col = load_data()

# --- STABLE TABS ---
t1, t2, t3, t4, t5 = st.tabs(["📊 Dashboard", "👤 Staff Details", "➕ Add Data", "🗓️ Event Logs", "🏆 Leaderboard"])

# ... (Dashboard & Staff Details remain same)

# --- TAB 4: NEW & IMPROVED EVENT LOGS ---
with t4:
    st.title("🗓️ Event Records")
    
    # Advanced Filtering Row
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if loc_col:
            loc_list = ["All"] + sorted(df_events[loc_col].unique().tolist())
            sel_loc = st.selectbox("Filter by Location", loc_list)
        else:
            sel_loc = "All"

    with col2:
        if cat_col:
            cat_list = ["All"] + sorted(df_events[cat_col].unique().tolist())
            sel_cat = st.selectbox("Filter by Category", cat_list)
        else:
            sel_cat = "All"

    with col3:
        search_query = st.text_input("🔍 Search Event Name", placeholder="e.g. New Year")

    # Applying Filters
    filtered_events = df_events.copy()
    if sel_loc != "All":
        filtered_events = filtered_events[filtered_events[loc_col] == sel_loc]
    if sel_cat != "All":
        filtered_events = filtered_events[filtered_events[cat_col] == sel_cat]
    if search_query:
        filtered_events = filtered_events[filtered_events['Event Name'].str.contains(search_query, case=False, na=False)]

    st.write(f"Showing **{len(filtered_events)}** matching event entries")
    
    # Display Table
    st.dataframe(filtered_events, use_container_width=True, hide_index=True)

    # Export Button
    csv = filtered_events.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Filtered Logs as CSV", data=csv, file_name="event_logs.csv", mime="text/csv")

# --- TAB 1: FIXED DASHBOARD (Avoiding the KeyError) ---
with t1:
    st.title("📊 Strategic Overview")
    # Quick Summary Table (Like in your screenshot)
    if cat_col:
        st.subheader("Category Summary Table")
        summary = df_events.groupby(cat_col).size().reset_index(name='Count')
        st.table(summary)
    
    # ... (Rest of dashboard)
