{\rtf1\ansi\ansicpg1252\cocoartf2869
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\froman\fcharset0 Times-Roman;\f1\fnil\fcharset0 AppleColorEmoji;}
{\colortbl;\red255\green255\blue255;\red0\green0\blue0;}
{\*\expandedcolortbl;;\cssrgb\c0\c0\c0;}
\paperw11900\paperh16840\margl1440\margr1440\vieww29360\viewh19760\viewkind0
\deftab720
\pard\pardeftab720\partightenfactor0

\f0\fs24 \cf0 \expnd0\expndtw0\kerning0
import streamlit as st\
from googleapiclient.discovery import build\
from google.oauth2 import service_account\
from googleapiclient.http import MediaIoBaseUpload\
import io\
import datetime\
\
# --- 1. CONFIGURATION (Using your provided IDs) ---\
MASTER_SHEET_ID = "15wPQ9QWydGKF1OIW1QkaeXB3msRjhwiJix4ZVyf6DxA"\
RESEARCH_MASTER_ID = "1aAP24-2LTtZN71gZb64vhczfIfRN_L0j"\
\
# Mapping your specific folder and department\
DEPT_FOLDERS = \{\
    "Department of English": "1aAP24-2LTtZN71gZb64vhczfIfRN_L0j"\
\}\
\
FACULTY_GSITE_FOLDERS = \{\
    "Dr. Manoj Kanth": "1IO_PjPHSI1cysys-mkHty-WkyXft5aK_" \
\}\
\
# --- 2. AUTHENTICATION ENGINE ---\
def get_creds():\
    # Reads from Streamlit Cloud Secrets\
    return service_account.Credentials.from_service_account_info(\
        st.secrets["gcp_service_account"],\
        scopes=[\
            "https://www.googleapis.com/auth/drive",\
            "https://www.googleapis.com/auth/spreadsheets"\
        ]\
    )\
\
def upload_to_drive(file_stream, filename, folder_id):\
    service = build('drive', 'v3', credentials=get_creds())\
    file_metadata = \{'name': filename, 'parents': [folder_id]\}\
    media = MediaIoBaseUpload(file_stream, mimetype='application/pdf', resumable=True)\
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()\
    return file.get('webViewLink')\
\
def log_to_sheets(data_row):\
    service = build('sheets', 'v4', credentials=get_creds())\
    body = \{'values': [data_row]\}\
    service.spreadsheets().values().append(\
        spreadsheetId=MASTER_SHEET_ID,\
        range="Sheet1!A:G",\
        valueInputOption="USER_ENTERED",\
        body=body\
    ).execute()\
\
# --- 3. UI INTERFACE ---\
st.set_page_config(page_title="St. Mary's Research Portal", layout="centered")\
st.title("
\f1 \uc0\u55357 \u56620 
\f0  Research Sync: Pilot Phase")\
st.write("Automatically updates Dept Drive, Central Drive, GSite, and Master Log.")\
\
with st.form("pilot_sync_form", clear_on_submit=True):\
    f_name = st.selectbox("Faculty Name", list(FACULTY_GSITE_FOLDERS.keys()))\
    f_dept = st.selectbox("Department", list(DEPT_FOLDERS.keys()))\
    f_activity = st.selectbox("Activity", ["Journal Paper", "Book Chapter", "FDP", "Workshop", "Conference"])\
    f_title = st.text_input("Title of Research/Activity")\
    f_file = st.file_uploader("Upload Evidence (PDF only)", type=['pdf'])\
    \
    submit = st.form_submit_button("
\f1 \uc0\u55357 \u56960 
\f0  Run Triple-Sync & Log")\
\
# --- 4. EXECUTION LOGIC ---\
if submit and f_file:\
    try:\
        with st.spinner("Synchronizing data across all platforms..."):\
            # Prepare file and metadata\
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")\
            filename = f"\{f_name\}_\{f_activity\}_\{datetime.datetime.now().strftime('%d%m%y')\}.pdf"\
            file_content = io.BytesIO(f_file.getvalue())\
            \
            # Action 1: Upload to Department Drive\
            file_content.seek(0)\
            upload_to_drive(file_content, filename, DEPT_FOLDERS[f_dept])\
            \
            # Action 2: Upload to Research Master Drive & Get permanent link\
            file_content.seek(0)\
            doc_link = upload_to_drive(file_content, filename, RESEARCH_MASTER_ID)\
            \
            # Action 3: Upload to Faculty GSite Folder\
            file_content.seek(0)\
            upload_to_drive(file_content, filename, FACULTY_GSITE_FOLDERS[f_name])\
            \
            # Action 4: Update Google Sheets Master Log\
            log_entry = [timestamp, f_name, f_dept, f_activity, f_title, doc_link]\
            log_to_sheets(log_entry)\
            \
            st.success(f"
\f1 \uc0\u9989 
\f0  Success! Data synced for \{f_name\}.")\
            st.balloons()\
            \
    except Exception as e:\
        st.error(f"Pilot Error: \{e\}")\
        st.info("Ensure the Service Account email is an 'Editor' on all links provided.")}