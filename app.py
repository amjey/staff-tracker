import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Staff Management System", layout="wide")
EXCEL_FILE = 'SomethingNew26.xlsx'

def save_data(staff_df, events_df):
    try:
        with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl') as writer:
            staff_df.to_excel(writer, sheet_name='Details', index=False)
            events_df.to_excel(writer, sheet_name='Event Details', index=False)
        return True
    except PermissionError:
        st.error(f"❌ Close '{EXCEL_FILE}' in Excel and try again.")
        return False

@st.cache_data
def load_data():
    if not os.path.exists(EXCEL_FILE):
        return pd.DataFrame(), pd.DataFrame()
    df_staff = pd.read_excel(EXCEL_FILE, sheet_name='Details')
    df_events = pd.read_excel(EXCEL_FILE, sheet_name='Event Details')
    df_staff['SN'] = df_staff['SN'].astype(str)
    df_events['SN'] = df_events['SN'].astype(str)
    return df_staff, df_events

try:
    df_staff, df_events = load_data()
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "👤 Add Staff", "📅 Add Event", "🗑️ Delete Data"])

    # --- TAB 1: DASHBOARD ---
    with tab1:
        st.sidebar.header("Filter")
        
        # Filter back to SN as requested
        selected_sn = st.sidebar.selectbox("Select Staff SN", df_staff['SN'].unique())
        
        # Get data based on SN
        staff_info = df_staff[df_staff['SN'] == selected_sn].iloc[0]
        personal_events = df_events[df_events['SN'] == selected_sn]
        
        st.title(f"👤 {staff_info['Name']}")
        
        # --- CUSTOM COLOR BADGE LOGIC ---
        badge_col = [c for c in df_staff.columns if 'Leader' in c or 'Badge' in c]
        
        if badge_col:
            actual_col_name = badge_col[0]
            role_value = str(staff_info[actual_col_name]).strip()
            role_lower = role_value.lower()
            
            # Specific Rules: Blue for Assist.Technician & Driver, Gold for others
            if "assist.technician" in role_lower or "driver" in role_lower:
                # Blue Badge
                st.info(f" **DESIGNATION:** {role_value}")
            elif role_lower in ["no", "n/a", "nan", ""]:
                st.write("*(No role assigned)*")
            else:
                # Gold/Green Badge for everyone else
                st.success(f" **DESIGNATION:** {role_value}")
        else:
            st.warning("⚠️ No 'Badge' column found in Excel.")

        # Metrics Row
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Rank", staff_info.get('Rank', 'N/A'))
        c2.metric("Unit", staff_info.get('Unit', 'N/A'))
        c3.metric("Contact", staff_info.get('Contact', 'N/A'))
        c4.metric("Events", len(personal_events))
        c5.metric("Total Mins", personal_events['Event Duration (Mins)'].sum())

        st.divider()
        st.subheader(f"Event History for {staff_info['Name']}")
        st.dataframe(personal_events, use_container_width=True, hide_index=True)

    # --- TAB 2: ADD STAFF ---
    with tab2:
        st.subheader("Register New Staff Member")
        with st.form("new_staff"):
            col1, col2 = st.columns(2)
            with col1:
                sn_in = st.text_input("SN")
                name_in = st.text_input("Full Name")
                rank_in = st.text_input("Rank")
            with col2:
                unit_in = st.text_input("Unit")
                contact_in = st.text_input("Contact")
                badge_in = st.text_input("Badge/Role Info")
                
            if st.form_submit_button("Add Staff"):
                # We use the FIRST badge column name found in Excel to keep it consistent
                target_col = badge_col[0] if badge_col else "Team Leader Badge"
                new_s = pd.DataFrame([{
                    "SN": sn_in, "Name": name_in, "Rank": rank_in, 
                    "Unit": unit_in, "Contact": contact_in, target_col: badge_in
                }])
                df_staff = pd.concat([df_staff, new_s], ignore_index=True)
                if save_data(df_staff, df_events):
                    st.success("Staff added!"); st.cache_data.clear(); st.rerun()

    # --- TAB 3: ADD EVENT ---
    with tab3:
        st.subheader("Log New Event")
        with st.form("event_form"):
            targets = st.multiselect("Select Staff SN", df_staff['SN'].unique())
            e_id = st.text_input("Event ID")
            e_name = st.text_input("Event Name")
            e_dur = st.number_input("Duration (Mins)", min_value=0)
            if st.form_submit_button("Save Event"):
                new_e = []
                for s in targets:
                    s_nm = df_staff[df_staff['SN'] == s]['Name'].values[0]
                    new_e.append({"SN": s, "Event ID": e_id, "Event Name": e_name, "Event Duration (Mins)": e_dur, "Master Group": s_nm})
                df_events = pd.concat([df_events, pd.DataFrame(new_e)], ignore_index=True)
                if save_data(df_staff, df_events):
                    st.success("Logged!"); st.cache_data.clear(); st.rerun()

    # --- TAB 4: DELETE ---
    with tab4:
        st.subheader("Management")
        del_sn = st.selectbox("Select SN to Remove", df_staff['SN'].unique())
        if st.button("Delete Record"):
            df_staff = df_staff[df_staff['SN'] != del_sn]
            df_events = df_events[df_events['SN'] != del_sn]
            if save_data(df_staff, df_events):
                st.success("Deleted"); st.cache_data.clear(); st.rerun()

except Exception as e:
    st.error(f"Error: {e}")