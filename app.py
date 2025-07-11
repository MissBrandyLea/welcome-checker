import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re

st.title("\U0001F393 Student Welcome Email Checker (Customizable)")

# --- Upload CSVs and validate headers ---
sf = None
canvas = None
emailed = None

salesforce_file = st.file_uploader("\U0001F4E5 Upload Salesforce Export", type="csv")
if salesforce_file:
    st.subheader("\U0001F9FE Salesforce File Check")
    sf = pd.read_csv(salesforce_file)
    required_sf_headers = [
        "First Name", "Last Name", "Email", "Calbright Email",
        "CCC ID", "Date of Enrollment",
        "Last LMS Activity Timestamp", "Last LMS SAA Timestamp"
    ]
    for header in required_sf_headers:
        st.write(f"{'✅' if header in sf.columns else '❌'} `{header}` {'found' if header in sf.columns else 'missing'}")
    st.write("\U0001F4C4 Sample Salesforce rows", sf.head(3))

canvas_file = st.file_uploader("\U0001F4E5 Upload Canvas Gradebook Export", type="csv")
if canvas_file:
    st.subheader("\U0001F9FE Canvas File Check")
    canvas = pd.read_csv(canvas_file)
    required_canvas_headers = ["SIS User ID"]
    for header in required_canvas_headers:
        st.write(f"{'✅' if header in canvas.columns else '❌'} `{header}` {'found' if header in canvas.columns else 'missing'}")
    has_pre = any("Pre-Assessment" in col for col in canvas.columns)
    has_milestone = any("Milestone" in col for col in canvas.columns)
    has_summative = any("Summative" in col for col in canvas.columns)
    st.write("\U0001F50D Assignment Columns:")
    st.write(f"{'✅' if has_pre else '❌'} Pre-Assessment")
    st.write(f"{'✅' if has_milestone else '❌'} Milestone")
    st.write(f"{'✅' if has_summative else '❌'} Summative")
    st.write("\U0001F4C4 Sample Canvas rows", canvas.head(3))

emailed_file = st.file_uploader("\U0001F4E5 Upload Welcome Email Log", type="csv")
if emailed_file:
    st.subheader("\U0001F9FE Welcome Email Log Check")
    emailed = pd.read_csv(emailed_file)
    required_emailed_headers = ["ccc_id"]
    for header in required_emailed_headers:
        st.write(f"{'✅' if header in emailed.columns else '❌'} `{header}` {'found' if header in emailed.columns else 'missing'}")
    st.write("\U0001F4C4 Sample Email log rows", emailed.head(3))

# --- Process Data if All Uploaded ---
if sf is not None and canvas is not None and emailed is not None:
        # --- Clean Column Headers ---
    sf.columns = [col.strip() for col in sf.columns]
    canvas.columns = [col.strip() for col in canvas.columns]
    emailed.columns = [col.strip() for col in emailed.columns]

    # --- Sidebar: User Filter Controls ---
    st.sidebar.header("\U0001F50D Filter Criteria")
    days_since_enrollment = st.sidebar.number_input("\U0001F4C5 Max Days Since Enrollment", min_value=0, value=30)
    days_since_lms = st.sidebar.number_input("\U0001F4CA Max Days Since Last LMS Activity", min_value=0, value=7)
    days_since_saa = st.sidebar.number_input("\U0001F9ED Max Days Since Last SAA Activity", min_value=0, value=7)
    max_pre_completed = st.sidebar.slider("\u2B50 Highest Pre-Assessment Completed (1–12)", min_value=0, max_value=12, value=0)

    # --- Log: Initial Salesforce Load ---
    st.write(f"\U0001F9FE Initial students after loading Salesforce: {len(sf)}")

    # --- Convert Salesforce Timestamps to datetime ---
    sf['Date of Enrollment'] = pd.to_datetime(sf['Date of Enrollment'], errors='coerce')
    sf['Last LMS Activity Timestamp'] = pd.to_datetime(sf['Last LMS Activity Timestamp'], errors='coerce')
    sf['Last LMS SAA Timestamp'] = pd.to_datetime(sf['Last LMS SAA Timestamp'], errors='coerce')

    # --- Apply Date Filters ---
    #today = datetime.today()
    #cutoff_enroll = today - timedelta(days=days_since_enrollment)
    #cutoff_lms = today - timedelta(days=days_since_lms)
    #cutoff_saa = today - timedelta(days=days_since_saa)

    #sf = sf[
    #    (sf['Date of Enrollment'] >= cutoff_enroll) &
    #    (sf['Last LMS Activity Timestamp'] >= cutoff_lms) &
    #    (sf['Last LMS SAA Timestamp'] >= cutoff_saa)
    #]
    #st.write(f"\U0001F4C6 After date filters: {len(sf)} students")

    # --- Exclude Students Who Already Received Welcome Email ---
    sf['CCC ID'] = sf['CCC ID'].astype(str)
    emailed_ids = set(emailed['ccc_id'].astype(str))
    filtered_sf = sf[~sf['CCC ID'].isin(emailed_ids)]
    st.write(f"\U0001F4E4 After removing emailed: {len(filtered_sf)} students")

    # --- Inner Join: Keep Only CCC IDs Present in Canvas ---
    canvas['SIS User ID'] = canvas['SIS User ID'].astype(str)
    canvas_matched = canvas[canvas['SIS User ID'].isin(filtered_sf['CCC ID'])]
    st.write(f"\U0001F4DD Matched to Canvas: {len(canvas_matched)} students")

    # --- Identify Assignment Columns (Pre/Milestone/Summative) ---
    pre_cols = [col for col in canvas.columns if re.search(r"\b\d{1,2}\.0[A-Z]?[ :]*Pre-Assessment", col, re.IGNORECASE)]
    ms_cols  = [col for col in canvas.columns if re.search(r"\b\d{1,2}\.0[A-Z]?[ :]*Milestone", col, re.IGNORECASE)]
    sum_cols = [col for col in canvas.columns if re.search(r"\b\d{1,2}\.0[A-Z]?[ :]*Summative", col, re.IGNORECASE)]


    # --- Stop if Pre-Assessment Columns Are Missing ---
    if not pre_cols:
        st.warning("\u26A0\ufe0f No Pre-Assessment columns found. Please check your Canvas export.")
        st.stop()

    # --- Compute Highest Completed Pre-Assessment per Student ---
    pre_map = {col: int(col.split('.')[0]) for col in pre_cols}

    # Extract only Pre columns for analysis
    pre_scores = canvas[['SIS User ID'] + pre_cols].copy()

    # Replace non-numeric/empty entries with NaN, force numeric (0+ counts as completed)
    for col in pre_cols:
        pre_scores[col] = pd.to_numeric(pre_scores[col], errors='coerce')

    # For each row, find the highest-numbered Pre column with a non-NaN value
    def max_completed_pre(row):
        completed = [pre_map[col] for col in pre_cols if not pd.isna(row[col])]
        return max(completed) if completed else 0

    pre_scores['Highest_Pre_Completed'] = pre_scores.apply(max_completed_pre, axis=1)

    # Keep only students with exactly the selected max
    eligible_ids = pre_scores[pre_scores['Highest_Pre_Completed'] == max_pre_completed]['SIS User ID']
    filtered_sf = filtered_sf[filtered_sf['CCC ID'].isin(eligible_ids)]

    st.write(f"🌟 After Pre-Assessment filter: {len(filtered_sf)} students")


    # --- Merge Canvas Columns Into Output ---
    canvas_subset = canvas[['SIS User ID'] + pre_cols + ms_cols + sum_cols]
    canvas_subset = canvas_subset.rename(columns={'SIS User ID': 'CCC ID'})
    output_df = pd.merge(filtered_sf, canvas_subset, on='CCC ID', how='inner')

    # --- Final Output Display and Export ---
    st.subheader("📋 Students to Welcome (Filtered)")
    st.write(f"🎯 **{len(output_df)} students** meet all filter criteria.")

    output_df.index = output_df.index + 1  # Shift index to start at 1
    st.dataframe(output_df, use_container_width=True)


    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"students_to_welcome_{timestamp}.csv"
    csv = output_df.to_csv(index=False).encode('utf-8')
    st.download_button("\u2B07\ufe0f Download CSV", data=csv, file_name=filename)

else:
    st.info("\U0001F446 Please upload all three CSV files to begin.")
