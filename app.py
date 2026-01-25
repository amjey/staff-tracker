with tab1:
    st.title("📊 System Overview")
    
    # 1. Staff Categorization Summary
    st.subheader("Staff Distribution")
    col1, col2, col3 = st.columns(3)
    
    # Count Categories
    total_staff = len(df_staff)
    assist_techs = len(df_staff[df_staff['Category'] == "Assist.Technician"])
    team_leaders = len(df_staff[df_staff['Category'] == "Team Leader"])
    
    col1.metric("Total Staff", total_staff)
    col2.metric("Team Leaders", team_leaders)
    col3.metric("Assist. Technicians", assist_techs)

    # 2. Visual Breakdown (Charts)
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.write("#### Staff by Category")
        staff_counts = df_staff['Category'].value_counts()
        st.bar_chart(staff_counts)

    with chart_col2:
        st.write("#### Events by Category")
        # Link events to staff categories to see which group is attending more events
        event_summary = pd.merge(df_events, df_staff[['SN', 'Category']], on='SN', how='left')
        event_counts = event_summary['Category'].value_counts()
        st.bar_chart(event_counts)

    # 3. Recent Activity Table
    st.write("---")
    st.write("#### Recent Event Activity")
    # Showing the last 10 events with staff names and categories
    recent_activity = pd.merge(df_events, df_staff[['SN', 'Name', 'Category']], on='SN', how='left')
    st.dataframe(recent_activity.tail(10), use_container_width=True, hide_index=True)
