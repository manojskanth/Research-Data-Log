import streamlit as st
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload
import io
import datetime

# --- 1. CONFIGURATION ---
MASTER_SHEET_ID = "15wPQ9QWydGKF1OIW1QkaeXB3msRjhwiJix4ZVyf6DxA"
RESEARCH_MASTER_ID = "1aAP24-2LTtZN71gZb64vhczfIfRN_L0j" # Central Research Hub ID

# Updated with the ID you provided for the English folder in the Hub
DEPT_DRIVE_CONFIG = {
    "English & Languages": "1iP5UA715z4ow4OGyQLlomUrZn49GLdjT", 
    "Commerce": "1aAP24-2LTtZN71gZb64vhczfIfRN_L0j",             # Placeholder (Central Hub)
    "Sciences": "1aAP24-2LTtZN71gZb64vhczfIfRN_L0j",             # Placeholder (Central Hub)
    "Social Science & Humanities": "1aAP24-2LTtZN71gZb64vhczfIfRN_L0j",
    "Management": "1aAP24-2LTtZN71gZb64vhczfIfRN_L0j"
}

FACULTY_GSITE_FOLDERS = {
    "Dr. Manoj Kanth": "1IO_PjPHSI1cysys-mkHty-WkyXft5aK_" 
}

# --- 2. CORE ENGINES ---
def get_creds():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    )

def upload_to_drive(file_bytes, filename, folder_id, mime_type):
    """Uploads file to Shared Drive using fresh streams for each call."""
    service = build('drive', 'v3', credentials=get_creds())
    file_metadata = {'name': filename, 'parents': [folder_id]}
    
    # We wrap the bytes in a new stream for every single upload to prevent 'empty file' errors
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
    
    file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink',
        supportsAllDrives=True,
        supportsTeamDrives=True 
    ).execute()
    return file.get('webViewLink')

def log_to_sheet(dept_name, activity_type, data_row):
    """Routes data to the correct Departmental Tab and Section."""
    service = build('sheets', 'v4', credentials=get_creds())
    
    # Logic: Professional Development vs. Research Output Sections
    if activity_type in ["FDP", "Workshop"]:
        target_range = f"'{dept_name}'!A3:G"
    else:
        target_range = f"'{dept_name}'!A50:G"

    body = {'values': [data_row]}
    service.spreadsheets().values().append(
        spreadsheetId=MASTER_SHEET_ID,
        range=target_range,
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()

# --- 3. UI INTERFACE ---
st.set_page_config(page_title="St. Mary's Research Hub", layout="wide")
st.title("🔬 Research Hub: Pilot Sync")

with st.form("pilot_sync", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        f_name = st.selectbox("Faculty Name", list(FACULTY_GSITE_FOLDERS.keys()))
        f_dept = st.selectbox("Target Department (for Testing)", list(DEPT_DRIVE_CONFIG.keys()))
        f_activity = st.selectbox("Category", ["Journal Paper", "Book Chapter", "FDP", "Workshop", "Conference"])
    with c2:
        f_date = st.date_input("Date of Activity")
        f_title = st.text_input("Title / Topic")
        f_file = st.file_uploader("Upload Evidence", type=['pdf', 'jpg', 'png', 'docx'])
    
    submit = st.form_submit_button("🚀 Run Triple-Sync")

# --- 4. EXECUTION ---
if submit and f_file:
    try:
        with st.spinner(f"Routing data to {f_dept} Drive and Sheet..."):
            timestamp = datetime.datetime.now().strftime("%d-%m-%Y_%H%M")
            ext = f_file.name.split('.')[-1]
            filename = f"{f_name}_{f_activity}_{timestamp}.{ext}"
            
            # Read file into memory once
            file_bytes = f_file.getvalue()
            mtype = f_file.type

            # SYNC 1: Specific Departmental Folder
            upload_to_drive(file_bytes, filename, DEPT_DRIVE_CONFIG[f_dept], mtype)
            
            # SYNC 2: Central Research Repository (Backup)
            doc_link = upload_to_drive(file_bytes, filename, RESEARCH_MASTER_ID, mtype)
            
            # SYNC 3: Personal GSite Folder (Inside the Hub)
            upload_to_drive(file_bytes, filename, FACULTY_GSITE_FOLDERS[f_name], mtype)
            
            # LOG: Write to the selected Departmental Tab
            log_entry = [str(f_date), f_name, f_activity, f_title, doc_link, "Pilot_Verified", timestamp]
            log_to_sheet(f_dept, f_activity, log_entry)
            
            st.success(f"✅ Success! Routed to {f_dept} records.")
            st.balloons()
            
    except Exception as e:
        st.error(f"Pilot Error: {e}")