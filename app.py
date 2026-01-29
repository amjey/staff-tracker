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

# --- 3. BULLETPROOF DATA ENGINE (From Code 1) ---
def load_and_scrub_data():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
        
        def clean_sheet(sheet_name):
            ws = sh.worksheet(sheet_name)
            raw = ws.get_all_values()
            if len(raw) <= 1: return pd.DataFrame()
            
            # Fix duplicate/empty headers (Fixes the crash from deleted columns)
            headers = [h.strip() if h.strip() else f"Col_{i}" for i, h in enumerate(raw[0])]
            final_headers = []
            counts = {}
            for h in headers:
                if h in counts:
                    counts[h] += 1
                    final_headers.append(f"{h}_{counts[h]}")
                else:
                    counts[h] = 0
                    final_headers.append(h)
            
            df = pd.DataFrame(raw[1:], columns=final_headers)
            # Remove phantom empty columns
            df = df.loc[:, ~df.columns.str.contains('^Col_|^Unnamed')]
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
page = st.sidebar.radio("Navigation", ["📊 Strategic Overview", "👤 Staff Profiles", "🗓️ Event Logs", "🏆 Leaderboard", "🖨️ Reports", "⚙️ Data Management"])

# --- 5. STRATEGIC OVERVIEW ---
if page == "📊 Strategic Overview":
    st.title("📊 Strategic Overview")
    if not df_staff.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Registered Staff", len(df_staff))
        
        # Flexibly find Badge column
        badge_col = next((c for c in df_staff.columns if "Badge" in c), df_staff.columns[min(5, len(df_staff.columns)-1)])
        tl_list = ["Team Leader", "Pro in Fireworks", "Master in Fireworks"]
        tls = len(df_staff[df_staff[badge_col].isin(tl_list)])
        
        c2.metric("Total Team Leaders", tls)
        c3.metric("Assistants / Technicians", len(df_staff) - tls)
        st.divider()
        st.dataframe(df_staff, use_container_width=True, hide_index=True)

# --- 6. STAFF PROFILES ---
elif page == "👤 Staff Profiles":
    st.title("👤 Staff Search & History")
    if not df_staff.empty:
        sel_sn = st.selectbox("Select Staff SN", df_staff['SN'].unique())
        person = df_staff[df_staff['SN'] == sel_sn].iloc[0]
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Name:** {person['Name']}")
            st.write(f"**Rank:** {person['Rank']}")
        with col2:
            st.write(f"**Unit:** {person.get('Unit', 'N/A')}")
            st.write(f"**Badge:** {person.get(badge_col, 'N/A')}")
        
        st.subheader("Event History")
        history = df_events[df_events['SN'] == sel_sn] if not df_events.empty else pd.DataFrame()
        st.dataframe(history, use_container_width=True, hide_index=True)

# --- 7. EVENT LOGS (With Expander from Code 2) ---
elif page == "🗓️ Event Logs":
    st.title("🗓️ Event Logs")
    if not df_events.empty:
        search_loc = st.text_input("🔍 Search by Location").strip()
        filtered = df_events[df_events['Event Location'].str.contains(search_loc, case=False, na=False)] if search_loc else df_events
        
        if not filtered.empty and search_loc:
            for (loc, date, name, dur), group in filtered.groupby(['Event Location', 'Event Date', 'Event Name', 'Event Duration (Mins)']):
                with st.expander(f"📍 {loc} | 🗓️ {date} | 🔥 {name}"):
                    st.write(f"**Duration:** {dur}")
                    if not df_staff.empty:
                        details = pd.merge(group[['SN']], df_staff[['SN', 'Name', 'Rank']], on='SN', how='left')
                        st.dataframe(details, hide_index=True, use_container_width=True)
        else:
            st.dataframe(filtered, use_container_width=True, hide_index=True)

# --- 8. REPORTS (PDF & Individual Excel) ---
elif page == "🖨️ Reports":
    st.title("🖨️ Report Center")
    t_ex, t_pdf = st.tabs(["📊 Excel Exports", "📄 PDF Print View"])
    
    with t_ex:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Full Registry")
            out = BytesIO()
            df_staff.to_excel(out, index=False, engine='xlsxwriter')
            st.download_button("📥 Download Full Staff Excel", out.getvalue(), "Full_Staff_List.xlsx")
        with c2:
            st.subheader("Staff Profile Report")
            rep_sn = st.selectbox("Select SN for Report", df_staff['SN'].unique())
            if st.button("Generate Excel Profile"):
                p_info = df_staff[df_staff['SN'] == rep_sn]
                p_events = df_events[df_events['SN'] == rep_sn]
                out_p = BytesIO()
                with pd.ExcelWriter(out_p, engine='xlsxwriter') as writer:
                    p_info.to_excel(writer, sheet_name='Details', index=False)
                    p_events.to_excel(writer, sheet_name='Events_Attended', index=False)
                st.download_button("📥 Download Individual Excel", out_p.getvalue(), f"Profile_{rep_sn}.xlsx")

    with t_pdf:
        st.info("To save as PDF: Select staff, then press Ctrl+P (Command+P) and choose 'Save as PDF'.")
        pdf_sn = st.selectbox("Select Staff for PDF View", df_staff['SN'].unique())
        if pdf_sn:
            p = df_staff[df_staff['SN'] == pdf_sn].iloc[0]
            st.markdown(f"## STAFF REPORT: {p['Name']}")
            st.write(f"**SN:** {p['SN']} | **Rank:** {p['Rank']} | **Unit:** {p.get('Unit', 'N/A')}")
            st.divider()
            st.write("### Attendance Record")
            st.table(df_events[df_events['SN'] == pdf_sn].drop(columns=['SN', 'Dur_Math'], errors='ignore'))

# --- 9. DATA MANAGEMENT (Restored Edit/Delete from Code 2) ---
elif page == "⚙️ Data Management":
    st.title("⚙️ Data Management")
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    
    m_add, m_edit, m_del = st.tabs(["➕ Add", "✏️ Edit", "🗑️ Delete"])
    
    with m_add:
        st.subheader("Register New Staff")
        with st.form("add_form", clear_on_submit=True):
            a_sn, a_rk, a_nm = st.text_input("SN"), st.text_input("Rank"), st.text_input("Name")
            a_un, a_ct = st.text_input("Unit"), st.text_input("Contact")
            a_bd = st.selectbox("Badge", ["Team Leader", "Assist.Technician", "Driver", "Master in Fireworks", "Pro in Fireworks"])
            if st.form_submit_button("Save to Sheet"):
                sh.worksheet("Details").append_row([a_sn, a_rk, a_nm, a_un, a_ct, a_bd])
                st.success("Staff added!"); st.rerun()

    with m_edit:
        st.subheader("Modify Existing Data")
        e_choice = st.radio("Edit Type", ["Staff", "Event"], horizontal=True)
        if e_choice == "Staff" and not df_staff.empty:
            e_sn = st.selectbox("Select Staff to Edit", df_staff['SN'])
            row = df_staff[df_staff['SN'] == e_sn].iloc[0]
            idx = df_staff[df_staff['SN'] == e_sn].index[0] + 2
            with st.form("edit_staff"):
                u_rk = st.text_input("Rank", value=row['Rank'])
                u_nm = st.text_input("Name", value=row['Name'])
                if st.form_submit_button("Update Staff"):
                    sh.worksheet("Details").update_cell(idx, 2, u_rk)
                    sh.worksheet("Details").update_cell(idx, 3, u_nm)
                    st.success("Updated!"); st.rerun()

    with m_del:
        st.subheader("Remove Records")
        d_choice = st.radio("Delete Type", ["Staff", "Event"], horizontal=True)
        if d_choice == "Staff" and not df_staff.empty:
            d_sn = st.selectbox("Select SN to Remove", df_staff['SN'])
            if st.button("⚠️ Confirm Delete Staff"):
                idx = df_staff[df_staff['SN'] == d_sn].index[0] + 2
                sh.worksheet("Details").delete_rows(int(idx))
                st.success("Deleted!"); st.rerun()
