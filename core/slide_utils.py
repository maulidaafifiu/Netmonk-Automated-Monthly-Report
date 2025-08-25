import os
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config.input_data import DESTINATION_FOLDER_ID, SCREENSHOT_FOLDER_ID

from core.screenshots_utils import screenshot_specific_element_playwright

# --- Konfigurasi Lingkup ---
SCOPES = [
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/drive'
]

# --- Otentikasi Google API ---
def authenticate_google():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials_slide&drive.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def get_slides_service():
    return build('slides', 'v1', credentials=authenticate_google())

def get_drive_service():
    return build('drive', 'v3', credentials=authenticate_google())

# --- Upload ke Google Drive (dengan folder opsional) ---
def upload_to_drive(filepath, filename, file_type='default', folder_id=None):
    drive_service = get_drive_service()

    # Tentukan folder tujuan berdasarkan jenis file jika folder_id belum diberikan
    if not folder_id:
        if file_type == 'screenshot':
            folder_id = SCREENSHOT_FOLDER_ID
        else:
            folder_id = DESTINATION_FOLDER_ID  # fallback ke default (slide)

    file_metadata = {
        'name': filename,
        'mimeType': 'image/png',
        'parents': [folder_id]
    }

    media = MediaFileUpload(filepath, mimetype='image/png')
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    file_id = uploaded_file.get('id')

    drive_service.permissions().create(
        fileId=file_id,
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()

    print(f"☁️ File di-upload ke Google Drive (folder: {folder_id}), file_id = {file_id}")
    return file_id

# --- Duplikat Template Slide ---
def copy_slide_template(drive_service, template_slide_id, destination_folder_id, new_file_name):
    metadata = {
        'name': new_file_name,
        'parents': [destination_folder_id],
        'mimeType': 'application/vnd.google-apps.presentation'
    }
    return drive_service.files().copy(fileId=template_slide_id, body=metadata).execute()['id']

# --- Ganti Teks Placeholder di Slide ---
def replace_text_in_google_slide(presentation_id, replacements):
    slides_service = get_slides_service()
    requests = [{
        'replaceAllText': {
            'replaceText': new_text,
            'containsText': {'text': old_text, 'matchCase': True}
        }
    } for old_text, new_text in replacements.items()]
    slides_service.presentations().batchUpdate(
        presentationId=presentation_id,
        body={'requests': requests}
    ).execute()
    print("📝 Placeholder teks berhasil diganti.")

# --- Sisipkan Gambar ke Slide ---
def insert_image_to_slide(presentation_id, image_file_id, slide_index=0, x=50, y=50, width=600, height=340):
    slides_service = get_slides_service()
    page_id = slides_service.presentations().get(presentationId=presentation_id).execute()['slides'][slide_index]['objectId']
    image_url = f"https://drive.google.com/uc?id={image_file_id}"
    requests = [{
        'createImage': {
            'url': image_url,
            'elementProperties': {
                'pageObjectId': page_id,
                'size': {
                    'height': {'magnitude': height, 'unit': 'PT'},
                    'width': {'magnitude': width, 'unit': 'PT'}
                },
                'transform': {
                    'scaleX': 1,
                    'scaleY': 1,
                    'translateX': x,
                    'translateY': y,
                    'unit': 'PT'
                }
            }
        }
    }]
    slides_service.presentations().batchUpdate(presentationId=presentation_id, body={'requests': requests}).execute()
    print("🖼️ Gambar berhasil disisipkan ke slide.")

# --- Screenshot dan Sisip ke Slide ---
def capture_and_insert_to_slide(
    url, presentation_id, slide_index=0, 
    selector=None, full_dashboard=True, 
    drive_filename='Screenshot Upload', 
    x=50, y=50, width=600, height=340, 
    wait_time=30, tab=None, wait_for=None,
    drive_folder_id=None  # folder untuk simpan screenshot
):
    if not selector:
        raise ValueError("Selector wajib diisi jika ingin screenshot elemen saja.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"element_{timestamp}.png"
    output_file = os.path.join("temp", filename)
    os.makedirs("temp", exist_ok=True)

    screenshot_specific_element_playwright(
        url, selector, output_file=output_file,
        wait_time=wait_time, tab=tab, wait_for=wait_for
    )

    file_id = upload_to_drive(output_file, drive_filename, file_type='screenshot')
    insert_image_to_slide(
        presentation_id, file_id,
        slide_index=slide_index,
        x=x, y=y, width=width, height=height
    )

    if os.path.exists(output_file):
        os.remove(output_file)
