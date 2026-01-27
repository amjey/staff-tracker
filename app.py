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

# --- 3. THE DATA ENGINE ---
def load_and_scrub_data():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
        
        def clean_sheet(sheet_name):
            worksheet = sh.worksheet(sheet_name)
            raw_data = worksheet.get_all_values()
            if len(raw_data) <= 1: return pd.DataFrame()
            
            # Filter out empty columns and rename duplicates
            headers = [h.strip() if h.strip() else f"Unnamed_{i}" for i, h in enumerate(raw_data[0])]
            final_headers = []
            counts = {}
            for h in headers:
                if h in counts:
                    counts[h] += 1
                    final_headers.append(f"{h}_{counts[h]}")
                else:
                    counts[h] = 0
                    final_headers.append(h)
            
            df = pd.DataFrame(raw_data[1:], columns=final_headers)
            # Remove phantom columns (like the ones you deleted)
            df = df.loc[:, ~df.columns.str.contains('^Unnamed|^Col_')]
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
        st.error(f"Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_staff, df_events = load_and_scrub_data()

# --- 4. NAVIGATION ---
page = st.sidebar.radio("Navigation", ["📊 Strategic Overview", "👤 Staff Profiles", "🗓️ Event Logs", "🏆 Leaderboard", "🖨️ Reports", "➕ Data Management"])

# --- 5. STRATEGIC OVERVIEW ---
if page == "📊 Strategic Overview":
    st.title("📊 Strategic Overview")
    if not df_staff.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Staff", len(df_staff))
        badge_col = 'Leader Badge' if 'Leader Badge' in df_staff.columns else df_staff.columns[5]
        tls = len(df_staff[df_staff[badge_col].str.contains("Leader|Master|Pro", na=False)])
        c2.metric("Team Leaders", tls)
        c3.metric("Assistants", len(df_staff) - tls)
        st.divider()
        st.subheader("📋 Registered Staff Directory")
        st.dataframe(df_staff, use_container_width=True, hide_index=True)

# --- 6. STAFF PROFILES (WITH HISTORY) ---
elif page == "👤 Staff Profiles":
    st.title("👤 Staff Registry & Search")
    if not df_staff.empty:
        search_sn = st.text_input("🔍 Search by Staff SN (Enter to view history)").strip()
        if search_sn:
            person = df_staff[df_staff['SN'] == search_sn]
            if not person.empty:
                st.success(f"Viewing: {person.iloc[0]['Name']}")
                st.table(person) # Better for visual profiling
                st.subheader("🗓️ Attended Events")
                history = df_events[df_events['SN'] == search_sn] if not df_events.empty else pd.DataFrame()
                if not history.empty:
                    st.dataframe(history, use_container_width=True, hide_index=True)
                else:
                    st.info("No recorded events for this Staff SN.")
            else:
                st.error("SN not found.")

# --- 7. REPORTS (EXCEL & PDF MODE) ---
elif page == "🖨️ Reports":
    st.title("🖨️ Report Center")
    tab_ex, tab_pdf = st.tabs(["📊 Excel Exports", "📄 PDF Print Mode"])
    
    with tab_ex:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Full Staff Registry")
            towrite = BytesIO()
            df_staff.to_excel(towrite, index=False, engine='xlsxwriter')
            st.download_button("📥 Download Full Registry", towrite.getvalue(), "Full_Staff_Registry.xlsx")
        
        with c2:
            st.subheader("Individual Staff Profile")
            target_sn = st.selectbox("Select SN for Report", df_staff['SN'].unique())
            if st.button("Generate Excel Profile"):
                p_info = df_staff[df_staff['SN'] == target_sn]
                p_events = df_events[df_events['SN'] == target_sn]
                towrite = BytesIO()
                with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
                    p_info.to_excel(writer, sheet_name='Info', index=False)
                    p_events.to_excel(writer, sheet_name='Events', index=False)
                st.download_button("📥 Download Profile", towrite.getvalue(), f"Profile_{target_sn}.xlsx")

    with tab_pdf:
        st.info("💡 To save as PDF: Select a staff member below, then press **Ctrl+P** (or Command+P) and choose 'Save as PDF'.")
        pdf_sn = st.selectbox("Select Staff to Print", df_staff['SN'].unique(), key="pdf_sel")
        if pdf_sn:
            p_data = df_staff[df_staff['SN'] == pdf_sn].iloc[0]
            st.markdown(f"""
            <div style="border:2px solid #eee; padding:20px; border-radius:10px">
                <h2>Staff Activity Report</h2>
                <hr>
                <p><b>Name:</b> {p_data['Name']} | <b>SN:</b> {p_data['SN']}</p>
                <p><b>Rank:</b> {p_data['Rank']} | <b>Unit:</b> {p_data.get('Unit', 'N/A')}</p>
            </div>
            """, unsafe_with_html=True)
            p_events = df_events[df_events['SN'] == pdf_sn]
            st.write("### Events Attended")
            st.table(p_events.drop(columns=['SN', 'Dur_Math'], errors='ignore'))

# --- 8. DATA MANAGEMENT (RESTORED TABS) ---
elif page == "➕ Data Management":
    st.title("⚙️ Data Management")
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    
    t_add, t_edit, t_del = st.tabs(["➕ Add New", "✏️ Edit Details", "🗑️ Delete Record"])
    
    with t_add:
        st.write("Add new entries via the Google Sheet or manual forms.")
        # [Add form logic if needed]

    with t_edit:
        st.subheader("Edit Staff Info")
        edit_sn = st.selectbox("Select Staff to Edit", df_staff['SN'])
        row_idx = df_staff[df_staff['SN'] == edit_sn].index[0] + 2
        with st.form("edit_form"):
            new_rank = st.text_input("New Rank", value=df_staff.loc[df_staff['SN']==edit_sn, 'Rank'].values[0])
            new_name = st.text_input("New Name", value=df_staff.loc[df_staff['SN']==edit_sn, 'Name'].values[0])
            if st.form_submit_button("Update Sheet"):
                sh.worksheet("Details").update_cell(row_idx, 2, new_rank)
                sh.worksheet("Details").update_cell(row_idx, 3, new_name)
                st.success("Updated!")
                st.rerun()

    with t_del:
        st.warning("Action cannot be undone.")
        del_sn = st.selectbox("Select SN to Delete", df_staff['SN'], key="del_staff")
        if st.button("Confirm Delete Staff"):
            d_idx = df_staff[df_staff['SN'] == del_sn].index[0] + 2
            sh.worksheet("Details").delete_rows(int(d_idx))
            st.success("Deleted!")
            st.rerun()
