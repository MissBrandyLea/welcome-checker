import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.title("🎓 Student Welcome Email Checker")

# Upload your CSVs
salesforce_file = st.file_uploader("📥 Upload Salesforce Export", type="csv")
canvas_file = st.file_uploader("📥 Upload Canvas Gradebook Export", type="csv")
emailed_file = st.file_uploader("📥 Upload Welcome Email Log", type="csv")

if salesforce_file and canvas_file and emailed_file:
    # Load CSVs into DataFrames
    sf = pd.read_csv(salesforce_file)
    canvas = pd.read_csv(canvas_file)
    emailed = pd.read_csv(emailed_file)

    # Rename columns for consistency (trim spaces)
    sf.columns = [col.strip() for col in sf.columns]
    canvas.columns = [col.strip() for col in canvas.columns]
    emailed.columns = [col.strip() for col in emailed.columns]

    # Convert Join Date
    if 'Date of Enrollment' in sf.columns:
        sf['Date of Enrollment'] = pd.to_datetime(sf['Date of Enrollment'], errors='coerce')
        date_cutoff = datetime.today() - timedelta(days=30)
        recent_sf = sf[sf['Date of Enrollment'] >= date_cutoff]
    else:
        st.error("❌ 'Date of Enrollment' not found in Salesforce CSV.")
        st.stop()

    # Match CCC IDs (primary key)
    canvas_ids = set(canvas['SIS User ID'].astype(str))
    emailed_ids = set(emailed['ccc_id'].astype(str))
    
    # Pre-filter: only students from Salesforce who joined recently
    recent_sf['CCC ID'] = recent_sf['CCC ID'].astype(str)
    filtered_sf = recent_sf[recent_sf['CCC ID'].isin(canvas_ids)]
    filtered_sf = filtered_sf[~filtered_sf['CCC ID'].isin(emailed_ids)]

    # Optional: check if Pre-Assessment or Milestone was submitted in Canvas
    pre_cols = [col for col in canvas.columns if col.startswith("1.0: Pre-Assessment")]
    ms_cols = [col for col in canvas.columns if col.startswith("1.0: Milestone")]

    if pre_cols and ms_cols:
        # Merge student activity info (not required, but good context)
        activity_status = []
        for _, row in filtered_sf.iterrows():
            sid = row['CCC ID']
            canvas_row = canvas[canvas['SIS User ID'].astype(str) == sid]
            if canvas_row.empty:
                activity_status.append("Not in Canvas")
                continue

            pre_submitted = canvas_row[pre_cols].notna().any(axis=1).values[0]
            ms_submitted = canvas_row[ms_cols].notna().any(axis=1).values[0]

            if pre_submitted and ms_submitted:
                activity_status.append("✅ Pre + Milestone")
            elif pre_submitted:
                activity_status.append("🟡 Pre only")
            else:
                activity_status.append("❌ No activity")

        filtered_sf['Activity Status'] = activity_status

 # Add Canvas activity columns (Pre-Assessment and Milestone) to output
    filtered_canvas = canvas[canvas['SIS User ID'].isin(filtered_sf['CCC ID'])][['SIS User ID'] + pre_cols + ms_cols]
    filtered_canvas = filtered_canvas.rename(columns={'SIS User ID': 'CCC ID'})

    # Merge into final DataFrame
    output_df = pd.merge(filtered_sf, filtered_canvas, on='CCC ID', how='left')

    # Final selected columns (from Salesforce + Canvas)
    final_cols = [
        'CCC ID', 'First Name', 'Last Name', 'Email', 'Calbright Email', 'Date of Enrollment',
        'Activity Status'
    ] + pre_cols + ms_cols

    output_df = output_df[final_cols]

    # Display and export
    st.subheader("📋 Students to Welcome")
    st.write(output_df)

    # Download button
    csv = output_df.to_csv(index=False).encode('utf-8')
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"students_to_welcome_{timestamp}.csv"

    # Download button with timestamped filename
    st.download_button("⬇️ Download CSV", data=csv, file_name=filename)

else:
    st.info("👆 Please upload all three CSV files to begin.")
