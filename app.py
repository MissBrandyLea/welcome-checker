import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re

st.title("🎓 Student Welcome Email Checker (Customizable)")

# --- Upload CSVs and validate headers ---
sf = None
canvas = None
emailed = None

salesforce_file = st.file_uploader("📥 Upload Salesforce Export", type="csv")
if salesforce_file:
    st.subheader("🧾 Salesforce File Check")
    sf = pd.read_csv(salesforce_file)
    required_sf_headers = [
        "First Name", "Last Name", "Email", "Calbright Email",
        "CCC ID", "Date of Enrollment",
        "Last LMS Activity Timestamp", "Last LMS SAA Timestamp"
    ]
    for header in required_sf_headers:
        st.write(f"{'✅' if header in sf.columns else '❌'} `{header}` {'found' if header in sf.columns else 'missing'}")

canvas_file = st.file_uploader("📥 Upload Canvas Gradebook Export", type="csv")
if canvas_file:
    st.subheader("🧾 Canvas File Check")
    canvas = pd.read_csv(canvas_file)
    required_canvas_headers = ["SIS User ID"]
    for header in required_canvas_headers:
        st.write(f"{'✅' if header in canvas.columns else '❌'} `{header}` {'found' if header in canvas.columns else 'missing'}")
    
    has_pre = any("Pre-Assessment" in col for col in canvas.columns)
    has_milestone = any("Milestone" in col for col in canvas.columns)
    has_summative = any("Summative" in col for col in canvas.columns)

    st.write("🔍 Assignment Columns:")
    st.write(f"{'✅' if has_pre else '❌'} Pre-Assessment")
    st.write(f"{'✅' if has_milestone else '❌'} Milestone")
    st.write(f"{'✅' if has_summative else '❌'} Summative")

emailed_file = st.file_uploader("📥 Upload Welcome Email Log", type="csv")
if emailed_file:
    st.subheader("🧾 Welcome Email Log Check")
    emailed = pd.read_csv(emailed_file)
    required_emailed_headers = ["ccc_id"]
    for header in required_emailed_headers:
        st.write(f"{'✅' if header in emailed.columns else '❌'} `{header}` {'found' if header in emailed.columns else 'missing'}")

# --- Process Data if All Uploaded ---
if sf is not None and canvas is not None and emailed is not None:
    # Clean headers
    sf.columns = [col.strip() for col in sf.columns]
    canvas.columns = [col.strip() for col in canvas.columns]
    emailed.columns = [col.strip() for col in emailed.columns]

    # Sidebar filters
    st.sidebar.header("🔍 Filter Criteria")
    days_since_enrollment = st.sidebar.number_input("📅 Max Days Since Enrollment", min_value=0, value=30)
    days_since_lms = st.sidebar.number_input("📊 Max Days Since Last LMS Activity", min_value=0, value=14)
    days_since_saa = st.sidebar.number_input("🧭 Max Days Since Last SAA Activity", min_value=0, value=14)
    max_pre_completed = st.sidebar.slider("⭐ Highest Pre-Assessment Completed (1–12)", min_value=1, max_value=12, value=1)

    # Convert Salesforce dates
    sf['Date of Enrollment'] = pd.to_datetime(sf['Date of Enrollment'], errors='coerce')
    sf['Last LMS Activity Timestamp'] = pd.to_datetime(sf['Last LMS Activity Timestamp'], errors='coerce')
    sf['Last LMS SAA Timestamp'] = pd.to_datetime(sf['Last LMS SAA Timestamp'], errors='coerce')

    # Date filters
    today = datetime.today()
    cutoff_enroll = today - timedelta(days=days_since_enrollment)
    cutoff_lms = today - timedelta(days=days_since_lms)
    cutoff_saa = today - timedelta(days=days_since_saa)

    sf = sf[
        (sf['Date of Enrollment'] >= cutoff_enroll) &
        (sf['Last LMS Activity Timestamp'] >= cutoff_lms) &
        (sf['Last LMS SAA Timestamp'] >= cutoff_saa)
    ]

    # Filter out already emailed
    sf['CCC ID'] = sf['CCC ID'].astype(str)
    emailed_ids = set(emailed['ccc_id'].astype(str))
    filtered_sf = sf[~sf['CCC ID'].isin(emailed_ids)]

    # Canvas matching
    canvas['SIS User ID'] = canvas['SIS User ID'].astype(str)
    canvas_matched = canvas[canvas['SIS User ID'].isin(filtered_sf['CCC ID'])]

    # --- Identify assignment columns ---
    pre_cols = [col for col in canvas.columns if re.search(r"\b\d{1,2}\.0[A-Z]?[ :]?.*Pre-Assessment.*", col, re.IGNORECASE)]
    ms_cols  = [col for col in canvas.columns if re.search(r"\b\d{1,2}\.0[A-Z]?[ :]?.*Milestone.*", col, re.IGNORECASE)]
    sum_cols = [col for col in canvas.columns if re.search(r"\b\d{1,2}\.0[A-Z]?[ :]?.*Summative.*", col, re.IGNORECASE)]

    if not pre_cols:
        st.warning("⚠️ No Pre-Assessment columns found. Please check your Canvas export.")
        st.stop()

    # Filter by pre-assessment threshold
    pre_map = {col: int(col.split('.')[0]) for col in pre_cols}
    relevant_pre_cols = [col for col, num in pre_map.items() if num >= max_pre_completed]
    canvas_filtered_ids = canvas[relevant_pre_cols].notna().any(axis=1)
    canvas_ids = set(canvas[canvas_filtered_ids]['SIS User ID'])
    filtered_sf = filtered_sf[filtered_sf['CCC ID'].isin(canvas_ids)]

    # Merge Canvas data
    canvas_subset = canvas[['SIS User ID'] + pre_cols + ms_cols + sum_cols]
    canvas_subset = canvas_subset.rename(columns={'SIS User ID': 'CCC ID'})
    output_df = pd.merge(filtered_sf, canvas_subset, on='CCC ID', how='left')

    # Display results
    st.subheader("📋 Students to Welcome (Filtered)")
    st.write(f"🎯 **{len(output_df)} students** meet all filter criteria.")
    st.write(output_df)

    # Download button
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"students_to_welcome_{timestamp}.csv"
    csv = output_df.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download CSV", data=csv, file_name=filename)

else:
    st.info("👆 Please upload all three CSV files to begin.")
