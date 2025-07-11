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

    # --- Convert Salesforce Timestamps to datetime ---
    sf['Date of Enrollment'] = pd.to_datetime(sf['Date of Enrollment'], errors='coerce')
    sf['Last LMS Activity Timestamp'] = pd.to_datetime(sf['Last LMS Activity Timestamp'], errors='coerce')
    sf['Last LMS SAA Timestamp'] = pd.to_datetime(sf['Last LMS SAA Timestamp'], errors='coerce')

    # --- Sidebar: Filter Toggles and Inputs ---
    st.sidebar.header("🔧 Filter Settings")

    # Date filters
    use_enroll_filter = st.sidebar.checkbox("📅 Filter by Enrollment Date", value=False)
    if use_enroll_filter:
        days_since_enrollment = st.sidebar.number_input("🗓️ Max Days Since Enrollment", min_value=0, value=30)


    use_lms_filter = st.sidebar.checkbox("📊 Filter by Last LMS Activity", value=False)
    if use_lms_filter:
        days_since_lms = st.sidebar.number_input("📊 Max Days Since Last LMS Activity", min_value=0, value=7)


    use_saa_filter = st.sidebar.checkbox("🧠 Filter by Last SAA Activity", value=False)
    if use_saa_filter:
        days_since_saa = st.sidebar.number_input("🧠 Max Days Since Last SAA Activity", min_value=0, value=7)


    # Pre-assessment filter
    use_pre_filter = st.sidebar.checkbox("🌟 Filter by Pre-Assessment Completed", value=False)
    if use_pre_filter:
        max_pre_completed = st.sidebar.slider("🌟 Highest Pre-Assessment Completed (0–12)", min_value=0, max_value=12, value=0)


    # --- Diagnostics: Date Nulls and Cutoffs ---
#    st.write("🧪 Nulls in Enrollment Dates:", sf['Date of Enrollment'].isna().sum())
#    st.write("🧪 Nulls in LMS Activity Dates:", sf['Last LMS Activity Timestamp'].isna().sum())
#    st.write("🧪 Nulls in SAA Dates:", sf['Last LMS SAA Timestamp'].isna().sum())

    today = datetime.today()

    cutoff_enroll = None
    if use_enroll_filter:
        cutoff_enroll = today - timedelta(days=days_since_enrollment)

    cutoff_lms = None
    if use_lms_filter:
        cutoff_lms = today - timedelta(days=days_since_lms)

    cutoff_saa = None
    if use_saa_filter:
        cutoff_saa = today - timedelta(days=days_since_saa)


#    st.write("📅 Date Cutoffs:", {
#        "Enrollment": cutoff_enroll if use_enroll_filter else "Disabled",
#        "LMS Activity": cutoff_lms if use_lms_filter else "Disabled",
#        "SAA Activity": cutoff_saa if use_saa_filter else "Disabled"
#    })

    # --- Apply Date Filters Conditionally ---
    filtered = sf.copy()
    if use_enroll_filter:
        filtered = filtered[filtered['Date of Enrollment'] >= cutoff_enroll]
        st.write("📆 After Enrollment Date Filter:", len(filtered))

    if use_lms_filter:
        filtered = filtered[filtered['Last LMS Activity Timestamp'] >= cutoff_lms]
        st.write("📊 After LMS Activity Filter:", len(filtered))

    if use_saa_filter:
        filtered = filtered[filtered['Last LMS SAA Timestamp'] >= cutoff_saa]
        st.write("🧠 After SAA Activity Filter:", len(filtered))

    sf = filtered  # Final filtered Salesforce
    st.write(f"🧮 After date filters: {len(sf)} students")

    # --- Exclude Students Who Already Received Welcome Email ---
    sf['CCC ID'] = sf['CCC ID'].astype(str)
    emailed_ids = set(emailed['ccc_id'].astype(str))
    filtered_sf = sf[~sf['CCC ID'].isin(emailed_ids)]
    st.write("📤 After removing emailed:", len(filtered_sf), "students")

    # --- Canvas Inner Join on CCC ID ---
    canvas['SIS User ID'] = canvas['SIS User ID'].astype(str)
    canvas_matched = canvas[canvas['SIS User ID'].isin(filtered_sf['CCC ID'])]
    st.write("📝 Matched to Canvas:", len(canvas_matched), "students")

    # --- Identify Assignment Columns (Pre/Milestone/Summative) ---
    pre_cols = [col for col in canvas.columns if re.search(r"\b\d{1,2}\.0[A-Z]?[ :]*Pre-Assessment", col, re.IGNORECASE)]
    ms_cols  = [col for col in canvas.columns if re.search(r"\b\d{1,2}\.0[A-Z]?[ :]*Milestone", col, re.IGNORECASE)]
    sum_cols = [col for col in canvas.columns if re.search(r"\b\d{1,2}\.0[A-Z]?[ :]*Summative", col, re.IGNORECASE)]

    # --- Stop if Pre-Assessment Columns Are Missing ---
    if not pre_cols:
        st.warning("⚠️ No Pre-Assessment columns found. Please check your Canvas export.")
        st.stop()

    # --- Compute Highest Completed Pre-Assessment per Student ---
    pre_map = {col: int(col.split('.')[0]) for col in pre_cols}
    pre_scores = canvas[['SIS User ID'] + pre_cols].copy()

    # Clean up scores: Convert to numeric and treat 0+ as completed
    for col in pre_cols:
        pre_scores[col] = pd.to_numeric(pre_scores[col], errors='coerce')

    def max_completed_pre(row):
        completed = [pre_map[col] for col in pre_cols if not pd.isna(row[col])]
        return max(completed) if completed else 0

    pre_scores['Highest_Pre_Completed'] = pre_scores.apply(max_completed_pre, axis=1)

    # --- Apply Pre-Assessment Filter Conditionally ---
    if use_pre_filter:
        eligible_ids = pre_scores[pre_scores['Highest_Pre_Completed'] == max_pre_completed]['SIS User ID']
        filtered_sf = filtered_sf[filtered_sf['CCC ID'].isin(eligible_ids)]
        st.write("🌟 After Pre-Assessment filter:", len(filtered_sf), "students")



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
