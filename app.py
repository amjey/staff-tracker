# ... (rest of the code remains the same)

    with cb:
        st.subheader("🔥 New Event")
        with st.form("event_form", clear_on_submit=True):
            e_sn = st.text_input("Staff SN")
            e_nm = st.text_input("Event Name")
            e_lc = st.text_input("Location")
            e_dt = st.date_input("Date")
            e_dr = st.number_input("Duration (Mins)", min_value=1)
            e_gr = st.selectbox("Group", ["New Year", "Eid Celebrations", "National Day", "Other"])
            
            if st.form_submit_button("Save Event"):
                if e_sn and e_nm:
                    ws = sh.worksheet("Event Details")
                    # This line pushes the data
                    ws.append_row([e_sn, e_nm, e_lc, str(e_dt), e_dr, e_gr])
                    
                    st.success("✅ Event Logged Successfully!")
                    
                    # --- THE FIX: Clear cache and Rerun immediately ---
                    st.cache_data.clear() 
                    st.rerun() 
                else:
                    st.error("Please fill in the SN and Event Name.")
