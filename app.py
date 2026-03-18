# --- REPLICATING 3RD DOWN LAYOUT FOR RED/GREEN ZONE ---
with tabs[3]: 
    st.header("🟢 Red & Green Zone Strategy")
    # Filter for Opponent Territory (Positive Yard Lines in your CSV)
    rg_data = p_data[p_data[cols['field']] > 0].copy()
    
    if not rg_data.empty:
        # Define the Zones based on your LCC All O.csv data
        rg_data['RG_Zone'] = rg_data[cols['field']].apply(
            lambda x: "🟢 Green Zone (Inside 10)" if x <= 10 else "🔴 Red Zone (20-11)"
        )
        
        # 1. TOP METRIC (Duplicating 3rd Down Style)
        rz_success = (rg_data[cols['gain']] >= 3).mean() * 100 # Gain of 3+ is 'successful' in RZ
        st.metric("Red Zone Efficiency (Plays gaining 3+ yds)", f"{rz_success:.1f}%")
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Zone Distribution**")
            st.table(rg_data['RG_Zone'].value_counts())
        with c2:
            # 2. THE HEATMAP (Duplicating 3rd Down Style)
            rg_tendency = rg_data.groupby('RG_Zone')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            st.dataframe(rg_tendency.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
        
        # 3. THE EXPANDERS (Duplicating 3rd Down Style)
        for zone in ["🔴 Red Zone (20-11)", "🟢 Green Zone (Inside 10)"]:
            z_subset = rg_data[rg_data['RG_Zone'] == zone]
            if not z_subset.empty:
                with st.expander(f"Top Plays: {zone}"):
                    st.table(z_subset[cols['play']].value_counts().head(3))
    else:
        st.info("No plays detected in opponent territory (Positive Yard Lines).")
