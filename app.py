with tab1:
    st.title("📊 Dashboard Overview")
    
    # --- 1. STAFF TOTALS (FROM DETAILS SHEET COLUMN F) ---
    st.subheader("Staff Distribution")
    c1, c2, c3 = st.columns(3)
    
    # Count based on Leader Badge (Column F)
    # Assist.Technician = "Driver", rest are "Team Leader"
    total_staff = len(df_staff)
    assist_techs = len(df_staff[df_staff['Leader Badge'].str.lower() == "driver"])
    team_leaders = total_staff - assist_techs
    
    c1.metric("Total Registered", total_staff)
    c2.metric("Team Leaders", team_leaders)
    c3.metric("Assist. Technicians", assist_techs)

    # --- 2. EVENT TOTALS (FROM EVENT DETAILS SHEET) ---
    st.write("---")
    st.subheader("Event Activity")
    e_col1, e_col2 = st.columns(2)
    
    # Total Events from Column D (Event Name)
    total_events_count = len(df_events['Event Name'].dropna())
    
    # Categorization from Column G (Master Group)
    event_categories = df_events['Master Group'].value_counts()
    
    e_col1.metric("Total Events Logged", total_events_count)
    
    with e_col2:
        st.write("**Events by Master Group (Column G)**")
        if not event_categories.empty:
            st.bar_chart(event_categories)
        else:
            st.info("No data found in Column G (Master Group)")

    # --- 3. EVENT CATEGORY BREAKDOWN TABLE ---
    st.write("#### Category Breakdown Table")
    if not event_categories.empty:
        # Convert Series to DataFrame for a clean table
        df_cat_summary = event_categories.reset_index()
        df_cat_summary.columns = ['Master Group', 'Number of Events']
        st.dataframe(df_cat_summary, use_container_width=True, hide_index=True)
