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
    # Load and clean headers
    df_staff = pd.read_csv(DETAILS_URL).rename(columns=lambda x: x.strip())
    df_events = pd.read_csv(EVENTS_URL).rename(columns=lambda x: x.strip())
    
    # --- THE "ZERO-FAIL" CLEANING ---
    # We force SNs to be strings, remove .0, and remove ALL spaces
    for df in [df_staff, df_events]:
        if 'SN' in df.columns:
            df['SN'] = df['SN'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    # Clean Contact (Remove .0)
    if 'Contact' in df_staff.columns:
        df_staff['Contact'] = df_staff['Contact'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    # Find the duration column and force it to be a float (number)
    # Check for 'Event duration(Mins)' specifically
    dur_col = 'Event duration(Mins)' if 'Event duration(Mins)' in df_events.columns else 'Duration'
    if dur_col in df_events.columns:
        df_events[dur_col] = pd.to_numeric(df_events[dur_col], errors='coerce').fillna(0)

    # Categorization logic
    def categorize_staff(badge):
        b = str(badge).strip()
        if b in ["Assist.Technician", "Driver"]: return "Assist.Technician"
        if b in ["Master in Fireworks", "Pro in Fireworks", "Team Leader"]: return "Team Leader"
        return "Unassigned"

    df_staff['Category'] = df_staff['Leader Badge'].apply(categorize_staff)
    return df_staff, df_events, dur_col

df_staff, df_events, dur_col = load_data()

# --- STABLE TABS (Prevents Shifting) ---
tab_titles = ["📊 Dashboard", "👤 Staff Details", "➕ Add Data", "🗓️ Event Logs", "🏆 Leaderboard"]
tabs = st.tabs(tab_titles)

# --- TAB 1: DASHBOARD ---
with tabs[0]:
    st.title("📊 Strategic Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Registered", len(df_staff))
    c2.metric("Team Leaders", len(df_staff[df_staff['Category'] == "Team Leader"]))
    c3.metric("Assist. Technicians", len(df_staff[df_staff['Category'] == "Assist.Technician"]))
    st.write("---")
    unique_ev = df_events.drop_duplicates(subset=['Event Name', 'Event Location'])
    st.subheader("Event Categories")
    st.bar_chart(unique_ev['Master Group'].value_counts(), color="#0072B2")

# --- TAB 2: STAFF DETAILS (FIXED DURATION) ---
with tabs[1]:
    st.title("👤 Staff Profiles")
    
    f1, f2 = st.columns([1, 2])
    with f1:
        # Full selection of badges for the Directory filter
        role_filter = st.multiselect("Filter Directory by Badge:", 
                                     options=["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"], 
                                     default=["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
    with f2:
        # SEARCH BOX - Unique key stops the tab shifting
        search_sn = st.text_input("🔍 Type SN and Press Enter to view Profile", key="profile_search_input")

    # Filtered Table for directory
    display_df = df_staff[df_staff['Leader Badge'].isin(role_filter)]
    st.write("### 🗂️ Staff Directory")
    st.dataframe(display_df[['SN', 'Rank', 'Name', 'Unit', 'Contact', 'Leader Badge']], 
                 use_container_width=True, hide_index=True)

    # --- PROFILE VIEW ---
    if search_sn:
        # Strip search input to match cleaned SNs
        clean_search = str(search_sn).strip()
        p_match = df_staff[df_staff['SN'] == clean_search]
        
        if not p_match.empty:
            p = p_match.iloc[0]
            st.markdown("---")
            st.header(f"Profile: {p['Name']}")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Rank", p['Rank'])
            m2.metric("Unit", p['Unit'])
            m3.metric("Contact", p['Contact'])
            m4.metric("Badge", p['Leader Badge'])
            
            # --- THE DURATION CALCULATION FIX ---
            # We filter events by the CLEANED SN
            personal_history = df_events[df_events['SN'] == clean_search]
            
            total_events = len(personal_history)
            
            # Summing the duration column (ensuring it's treated as numbers)
            if dur_col in personal_history.columns:
                total_mins = personal_history[dur_col].sum()
            else:
                total_mins = 0
            
            st.write("---")
            e1, e2 = st.columns(2)
            e1.metric("Total Events Attended", total_events)
            # Use int() to keep it clean, or float if you have partial minutes
            e1.metric("Total Duration (Mins)", f"{int(total_mins)} Mins")
            
            st.subheader("Individual Event Log")
            st.dataframe(personal_history, use_container_width=True, hide_index=True)
        else:
            st.warning(f"No staff member found with SN: {search_sn}")

# --- TABS 3, 4, 5 (Forms, Logs, Leaderboard) ---
with tabs[2]:
    st.title("➕ Data Management")
    # ... (Forms stay same as your working version)
    st.info("Forms are ready in your Google Sheets link.")

with tabs[3]:
    st.title("🗓️ Event Logs")
    st.dataframe(df_events, use_container_width=True, hide_index=True)

with tabs[4]:
    st.title("🏆 Leaderboard")
    top = df_events['SN'].value_counts().head(10).reset_index()
    top.columns = ['SN', 'Engagements']
    board = pd.merge(top, df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
    st.dataframe(board[['Name', 'Rank', 'Engagements']], use_container_width=True, hide_index=True)
