import streamlit as st
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload
import io
import datetime

# --- 1. CONFIGURATION ---
# Using the verified IDs you provided
MASTER_SHEET_ID = "15wPQ9QWydGKF1OIW1QkaeXB3msRjhwiJix4ZVyf6DxA"
RESEARCH_MASTER_ID = "1aAP24-2LTtZN71gZb64vhczfIfRN_L0j"

DEPT_FOLDERS = {
    "Department of English": "1aAP24-2LTtZN71gZb64vhczfIfRN_L0j"
}

FACULTY_GSITE_FOLDERS = {
    "Dr. Manoj Kanth": "1IO_PjPHSI1cysys-mkHty-WkyXft5aK_" 
}

# --- 2. ENGINES ---
def get_creds():
    """Fetches credentials from Streamlit Secrets."""
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
    )

def upload_to_drive(file_stream, filename, folder_id):
    """Uploads file using the folder owner's quota."""
    service = build('drive', 'v3', credentials=get_creds())
    
    file_metadata = {
        'name': filename, 
        'parents': [folder_id]
    }
    
    media = MediaIoBaseUpload(file_stream, mimetype='application/pdf', resumable=True)
    
    # FIXED: Added supportsAllDrives=True to resolve the 403 Storage Quota error
    file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink',
        supportsAllDrives=True 
    ).execute()
    
    return file.get('webViewLink')

def log_to_sheets(data_row):
    """Logs activity metadata to the Master Google Sheet."""
    service = build('sheets', 'v4', credentials=get_creds())
    body = {'values': [data_row]}
    service.spreadsheets().values().append(
        spreadsheetId=MASTER_SHEET_ID,
        range="Sheet1!A:G",
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()

# --- 3. INTERFACE ---
st.set_page_config(page_title="St. Mary's Research Portal", page_icon="🔬")
st.title("🔬 Research Sync: Pilot Phase")
st.markdown("Automated Sync: **Dept Drive** ↔ **Central Research** ↔ **GSite Folder** ↔ **Log**")

with st.form("pilot_sync_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        f_name = st.selectbox("Faculty Name", list(FACULTY_GSITE_FOLDERS.keys()))
        f_dept = st.selectbox("Department", list(DEPT_FOLDERS.keys()))
    with col2:
        f_activity = st.selectbox("Activity", ["Journal Paper", "Book Chapter", "FDP", "Workshop", "Conference"])
        f_date = st.date_input("Date of Activity", datetime.date.today())
    
    f_title = st.text_input("Title of Research/Activity")
    f_file = st.file_uploader("Upload Evidence (PDF only)", type=['pdf'])
    
    submit = st.form_submit_button("🚀 Run Triple-Sync & Log")

# --- 4. EXECUTION LOGIC ---
if submit and f_file:
    try:
        with st.spinner("Processing uploads..."):
            # Prepare file and unique filename
            timestamp_str = datetime.datetime.now().strftime("%d-%m-%Y_%H%M")
            filename = f"{f_name}_{f_activity}_{timestamp_str}.pdf"
            file_bytes = f_file.getvalue()
            
            # Action 1: Upload to Department Drive
            upload_to_drive(io.BytesIO(file_bytes), filename, DEPT_FOLDERS[f_dept])
            
            # Action 2: Upload to Research Master Drive & Capture link for the log
            doc_link = upload_to_drive(io.BytesIO(file_bytes), filename, RESEARCH_MASTER_ID)
            
            # Action 3: Upload to Faculty GSite Folder
            upload_to_drive(io.BytesIO(file_bytes), filename, FACULTY_GSITE_FOLDERS[f_name])
            
            # Action 4: Update Google Sheets Master Log
            log_entry = [str(f_date), f_name, f_dept, f_activity, f_title, doc_link, timestamp_str]
            log_to_sheets(log_entry)
            
            st.success(f"✅ Triple-Sync Successful for {f_name}!")
            st.info(f"The entry has been logged in the Master Sheet.")
            st.balloons()
            
    except Exception as e:
        st.error(f"System Error: {e}")
        st.warning("Check if the Service Account email has 'Editor' access to all folders and the sheet.")