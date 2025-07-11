# 🎓 Student Welcome Email Checker

This tool helps Calbright instructors identify students who:
- Joined the course in the past 30 days (based on Salesforce enrollment data)
- Are active in Canvas (based on the gradebook export)
- Have not yet been sent a welcome email

Upload three CSVs:
- Salesforce export (must include CCC ID, Date of Enrollment, Name, and Email)
- Canvas Gradebook export (must include SIS User ID and assignment columns)
- Email log (manual list of CCC IDs already emailed). This list should have at minimum a field titled ccc_id (lowercase with an underscore between)

The app returns a filtered list of students to welcome and allows CSV download for outreach.
