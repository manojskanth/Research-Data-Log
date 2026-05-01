import streamlit as st
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload
import io
import datetime

# --- 1. CONFIGURATION ---
CURRENT_ACADEMIC_YEAR = "2025-26" 

# Master Sheet ID
MASTER_SHEET_ID = "15wPQ9QWydGKF1OIW1QkaeXB3msRjhwiJix4ZVyf6DxA"

# The 2025-26 Parent Folder (Central Hub Backup)
RESEARCH_MASTER_ID = "1c67i0HzSRxpMMrmwwBtpK5A-RpaGcVZY"

# Child Department Folders
DEPT_FOLDERS_25_26 = {
    "English & Languages": "1iP5UA715z4ow4OGyQLlomUrZn49GLdjT",
    "Social Science & Humanities": "1kwO7QrBYjnJazftv0aj8hZcp84ZKekcx",
    "Commerce": "1HMBoNkhksNpaitlBaGfq3JeoHsb_jmo-",
    "Management": "1VG3xY_SmhqmQ9BvSh6KvDXOptO3kHhsj",
    "Sciences": "1u_KRBhdZhcWQ55CyVI0v042bIpC5FQfs"
}

# Mapping for G-Site Portfolios
FACULTY_GSITE_FOLDERS = {
    "Dr. Manoj Kanth": "1IO_PjPHSI1cysys-mkHty-WkyXft5aK_",
    "Dr. Michael Preetam": "1cdtvdr94oPbe1my7yZXWw3XFjonehcfq",
    "Faculty Name 3": "PASTE_ID_HERE"
}

# --- 2. THE UPLOAD ENGINE (QUOTA-BYPASS VERSION) ---
def get_creds():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    )

def upload_to_drive(file_bytes, filename, folder_id, mime_type):
    service = build('drive', 'v3', credentials=get_creds())
    
    file_metadata = {
        'name': filename, 
        'parents': [folder_id]
    }
    
    # We use io.BytesIO(file_bytes) to ensure a fresh data stream for each sync destination
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
    
    # CRITICAL: supportsAllDrives=True allows the Service Account to use the storage 
    # quota of the FOLDER OWNER rather than its own (which is 0).
    file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink',
        supportsAllDrives=True,
        supportsTeamDrives=True 
    ).execute()
    
    return file.get('webViewLink')

# --- 3. UI ---
st.set_page_config(page_title="St. Mary's Research Hub", layout="wide")
st.title(f"🏢 Research Portal: {CURRENT_ACADEMIC_YEAR}")

with st.form("research_submission", clear_on_submit=True):
    f_dept = st.selectbox("Select Department", list(DEPT_FOLDERS_25_26.keys()))
    
    col1, col2 = st.columns(2)
    with col1:
        f_name = st.selectbox("Faculty Name", list(FACULTY_GSITE_FOLDERS.keys())) 
        f_activity = st.selectbox("Category", ["Journal Paper", "Book Chapter", "FDP", "Workshop", "Conference"])
    with col2:
        f_date = st.date_input("Date of Activity")
        f_title = st.text_input("Activity Title / Topic")

    f_file = st.file_uploader("Upload Evidence", type=['pdf', 'jpg', 'png', 'docx'])
    submit = st.form_submit_button(f"🚀 Sync to {CURRENT_ACADEMIC_YEAR}")

# --- 4. THE TRIPLE-SYNC EXECUTION ---
if submit and f_file:
    try:
        with st.spinner(f"Depositing record for {f_name}..."):
            timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
            month_name = f_date.strftime("%B")
            
            ext = f_file.name.split('.')[-1]
            filename = f"{f_name}_{f_activity}_{datetime.datetime.now().strftime('%H%M')}.{ext}"
            file_data = f_file.getvalue() 
            mtype = f_file.type

            # SYNC 1: DIRECT DEPOSIT IN DEPARTMENT FOLDER (Manager/Editor Access Required)
            target_folder = DEPT_FOLDERS_25_26[f_dept]
            doc_link = upload_to_drive(file_data, filename, target_folder, mtype)
            
            # SYNC 2: CENTRAL HUB BACKUP (2025-26 Parent Folder)
            upload_to_drive(file_data, filename, RESEARCH_MASTER_ID, mtype)
            
            # SYNC 3: FACULTY G-SITE PORTFOLIO
            if f_name in FACULTY_GSITE_FOLDERS and "PASTE_ID" not in FACULTY_GSITE_FOLDERS[f_name]:
                upload_to_drive(file_data, filename, FACULTY_GSITE_FOLDERS[f_name], mtype)
            
            # LOGGING: Append to Master Sheet Tab '2025-26'
            log_entry = [
                str(f_date), f_name, f_activity, f_title, 
                doc_link, f_dept, timestamp, CURRENT_ACADEMIC_YEAR, month_name
            ]
            
            service = build('sheets', 'v4', credentials=get_creds())
            service.spreadsheets().values().append(
                spreadsheetId=MASTER_SHEET_ID,
                range=f"'{CURRENT_ACADEMIC_YEAR}'!A2:I", 
                valueInputOption="USER_ENTERED",
                body={'values': [log_entry]}
            ).execute()
            
            st.success(f"✅ Records successfully deposited for {f_name}.")
            st.balloons()
            
    except Exception as e:
        # If the 403 error persists, we will know immediately via the UI
        st.error(f"Sync Error: {e}")