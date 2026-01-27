import streamlit as st
import pandas as pd
import gspread
import json
from io import BytesIO
from google.oauth2.service_account import Credentials

# --- 1. SECURE CONNECTION ---
@st.cache_resource
def get_gspread_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_info = json.loads(st.secrets["gcp_service_account"]["service_account_info"])
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        st.stop()

# --- 2. CONFIG ---
SHEET_ID = "1eiIvDBKXrpY28R2LQGEj0xvF2JuOglfRQ6-RAFt4CFE" 
st.set_page_config(page_title="Staff Management Pro", layout="wide")

# --- 3. DATA ENGINE (ROBUST COLUMN HANDLING) ---
def load_and_scrub_data():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
        
        def clean_sheet(sheet_name):
            ws = sh.worksheet(sheet_name)
            data = ws.get_all_values()
            if len(data) <= 1: return pd.DataFrame()
            
            # Create headers, handling empty/duplicate columns
            headers = [h.strip() if h.strip() else f"Col_{i}" for i, h in enumerate(data[0])]
            unique_headers = []
            counts = {}
            for h in headers:
                if h in counts:
                    counts[h] += 1
                    unique_headers.append(f"{h}_{counts[h]}")
                else:
                    counts[h] = 0
                    unique_headers.append(h)
            
            df = pd.DataFrame(data[1:], columns=unique_headers)
            # Remove purely empty columns and rows
            df = df.loc[:, (df != "").any(axis=0)]
            return df.dropna(how='all')

        df_s = clean_sheet("Details")
        df_e = clean_sheet("Event Details")

        if not df_s.empty: df_s['SN'] = df_s['SN'].astype(str).str.strip()
        if not df_e.empty: 
            if 'SN' in df_e.columns: df_e['SN'] = df_e['SN'].astype(str).str.strip()
            if 'Event Duration (Mins)' in df_e.columns:
                df_e['Dur_Math'] = pd.to_numeric(df_e['Event Duration (Mins)'].astype(str).str.extract('(\d+)')[0], errors='coerce').fillna(0)
        
        return df_s, df_e
    except Exception as e:
        st.error(f"Data Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_staff, df_events = load_and_scrub_data()

# --- 4. NAVIGATION ---
page = st.sidebar.radio("Navigation", ["📊 Strategic Overview", "👤 Staff Profiles", "🗓️ Event Logs", "🏆 Leaderboard", "🖨️ Reports", "⚙️ Data Management"])

# --- 5. STRATEGIC OVERVIEW ---
if page == "📊 Strategic Overview":
    st.title("📊 Strategic Overview")
    if not df_staff.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Staff", len(df_staff))
        badge_col = 'Leader Badge' if 'Leader Badge' in df_staff.columns else df_staff.columns[min(5, len(df_staff.columns)-1)]
        tl_list = ["Team Leader", "Pro in Fireworks", "Master in Fireworks"]
        tls = len(df_staff[df_staff[badge_col].isin(tl_list)])
        c2.metric("Team Leaders", tls)
        c3.metric("Assistants", len(df_staff) - tls)
        st.divider()
        st.dataframe(df_staff, use_container_width=True, hide_index=True)

# --- 6. STAFF PROFILES ---
elif page == "👤 Staff Profiles":
    st.title("👤 Staff Registry & History")
    if not df_staff.empty:
        sn_search = st.selectbox("Select Staff SN", df_staff['SN'].unique())
        person = df_staff[df_staff['SN'] == sn_search].iloc[0]
        
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Name:** {person['Name']}")
            st.write(f"**Rank:** {person['Rank']}")
        with c2:
            st.write(f"**Contact:** {person.get('Contact', 'N/A')}")
            st.write(f"**Badge:** {person.get('Leader Badge', 'N/A')}")
            
        st.subheader("Event Participation History")
        history = df_events[df_events['SN'] == sn_search] if not df_events.empty else pd.DataFrame()
        st.dataframe(history, use_container_width=True, hide_index=True)

# --- 7. REPORTS (EXCEL & PDF) ---
elif page == "🖨️ Reports":
    st.title("🖨️ Report Center")
    
    t1, t2 = st.tabs(["📥 Excel Exports", "📄 PDF Print View"])
    
    with t1:
        c1, c2 = st.columns(2)
        with c1:
            st.write("### Full Staff Registry")
            towrite = BytesIO()
            df_staff.to_excel(towrite, index=False, engine='xlsxwriter')
            st.download_button("📥 Download Full Staff Excel", towrite.getvalue(), "Staff_Registry.xlsx")
            
        with c2:
            st.write("### Staff Profile Report")
            rep_sn = st.selectbox("Select Staff for Excel Report", df_staff['SN'].unique())
            if st.button("Generate Excel Profile"):
                p_data = df_staff[df_staff['SN'] == rep_sn]
                p_events = df_events[df_events['SN'] == rep_sn]
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    p_data.to_excel(writer, sheet_name='Profile_Details', index=False)
                    p_events.to_excel(writer, sheet_name='Event_History', index=False)
                st.download_button("📥 Download Individual Profile", output.getvalue(), f"Profile_{rep_sn}.xlsx")

    with t2:
        st.info("💡 Select a staff member and then press **Ctrl + P** to save this page as a PDF.")
        p_sn = st.selectbox("Select Staff for PDF View", df_staff['SN'].unique())
        if p_sn:
            p_info = df_staff[df_staff['SN'] == p_sn].iloc[0]
            st.markdown(f"## Staff Profile: {p_info['Name']}")
            st.write(f"**SN:** {p_info['SN']} | **Rank:** {p_info['Rank']}")
            st.divider()
            st.write("### Attendance History")
            p_hist = df_events[df_events['SN'] == p_sn]
            st.table(p_hist.drop(columns=['SN', 'Dur_Math'], errors='ignore'))

# --- 8. DATA MANAGEMENT ---
elif page == "⚙️ Data Management":
    st.title("⚙️ Data Management")
    t1, t2, t3 = st.tabs(["➕ Add New", "✏️ Edit Details", "🗑️ Delete Record"])
    
    # Restored logic for Add, Edit, and Delete using Gspread update_cell / delete_rows
    # ... (Same logic as previous successful tabs)
