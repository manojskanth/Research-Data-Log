import streamlit as st
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload
import io
import datetime

# --- 1. CONFIGURATION: 2025-26 PARENT-CHILD SETUP ---
# Parent Tab Name in Google Sheets
CURRENT_ACADEMIC_YEAR = "2025-26" 

# Child Department Folders (Mapped exactly from your Drive links)
DEPT_FOLDERS_25_26 = {
    "Commerce": "1HMBoNkhksNpaitlBaGfq3JeoHsb_jmo-",
    "English & Languages": "14Nhs3qve5vDBbIT6GmzaRue51hvTzAOG",
    "Management": "1VG3xY_SmhqmQ9BvSh6KvDXOptO3kHhsj",
    "Sciences": "1u_KRBhdZhcWQ55CyVI0v042bIpC5FQfs",
    "Social Science & Humanities": "1m0xEcv-WKQr8CWfHlZ5AuCWIFXAm1H5g"
}

# Core IDs
MASTER_SHEET_ID = "15wPQ9QWydGKF1OIW1QkaeXB3msRjhwiJix4ZVyf6DxA"
RESEARCH_MASTER_ID = "1aAP24-2LTtZN71gZb64vhczfIfRN_L0j" 

# --- 2. AUTH & GOOGLE DRIVE ENGINE ---
def get_creds():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    )

def upload_to_drive(file_bytes, filename, folder_id, mime_type):
    service = build('drive', 'v3', credentials=get_creds())
    file_metadata = {'name': filename, 'parents': [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
    file = service.files().create(
        body=file_metadata, media_body=media, fields='id, webViewLink',
        supportsAllDrives=True, supportsTeamDrives=True 
    ).execute()
    return file.get('webViewLink')

# --- 3. UI: YEAR-FIRST INTERFACE ---
st.set_page_config(page_title="St. Mary's Research Hub", layout="wide")
st.title(f"🏢 Research Portal: {CURRENT_ACADEMIC_YEAR}")

with st.form("research_submission", clear_on_submit=True):
    # Selection: Choosing the 'Child' (Department) within the 'Parent' (Year)
    f_dept = st.selectbox("Select Department", list(DEPT_FOLDERS_25_26.keys()))
    
    col1, col2 = st.columns(2)
    with col1:
        # Defaulting to your name for the pilot
        f_name = st.text_input("Faculty Name", value="Dr. Manoj Kanth") 
        f_activity = st.selectbox("Category", ["Journal Paper", "Book Chapter", "FDP", "Workshop", "Conference"])
    with col2:
        f_date = st.date_input("Date of Activity")
        f_title = st.text_input("Activity Title / Topic")

    f_file = st.file_uploader("Upload Document (PDF, Image, Docx)", type=['pdf', 'jpg', 'png', 'docx'])
    submit = st.form_submit_button(f"🚀 Sync to {CURRENT_ACADEMIC_YEAR} Records")

# --- 4. EXECUTION: ROUTING & LOGGING ---
if submit and f_file:
    try:
        with st.spinner(f"Routing to {f_dept}..."):
            timestamp = datetime.datetime.now().strftime("%d-%m-%Y_%H:%M")
            month_name = f_date.strftime("%B")
            
            # File Naming Logic
            ext = f_file.name.split('.')[-1]
            filename = f"{f_name}_{f_activity}_{timestamp}.{ext}"
            file_bytes = f_file.getvalue()
            
            # Sync 1: Upload to the specific Child Department Folder
            doc_link = upload_to_drive(file_bytes, filename, DEPT_FOLDERS_25_26[f_dept], f_file.type)
            
            # Sync 2: Secondary backup to Central Hub
            upload_to_drive(file_bytes, filename, RESEARCH_MASTER_ID, f_file.type)
            
            # Sync 3: Log to Parent Sheet Tab '2025-26' (9-Column Layout)
            # Layout: Date, Name, Category, Title, Link, Dept, Timestamp, Year, Month
            log_entry = [
                str(f_date), f_name, f_activity, f_title, 
                doc_link, f_dept, timestamp, CURRENT_ACADEMIC_YEAR, month_name
            ]
            
            service = build('sheets', 'v4', credentials=get_creds())
            service.spreadsheets().values().append(
                spreadsheetId=MASTER_SHEET_ID,
                range=f"'{CURRENT_ACADEMIC_YEAR}'!A2:I", # Appends starting from Row 2
                valueInputOption="USER_ENTERED",
                body={'values': [log_entry]}
            ).execute()
            
            st.success(f"✅ Successfully synced to {CURRENT_ACADEMIC_YEAR} > {f_dept}")
            st.balloons()
            
    except Exception as e:
        st.error(f"Routing Error: {e}")