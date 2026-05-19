import os
import json
import logging
import uuid
import requests
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

_CACHED_CREDS = None

def get_google_creds():
    global _CACHED_CREDS
    if _CACHED_CREDS is not None:
        return _CACHED_CREDS
    try:
        creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if creds_json:
            if creds_json.endswith('.json'):
                _CACHED_CREDS = Credentials.from_service_account_file(creds_json, scopes=SCOPES)
            else:
                creds_dict = json.loads(creds_json)
                _CACHED_CREDS = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        elif os.path.exists('credentials.json'):
            _CACHED_CREDS = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        return _CACHED_CREDS
    except Exception as e:
        logger.error(f"Error loading credentials: {e}")
        return None

def upload_to_google_drive(file_content: bytes, filename: str, mime_type: str = "image/jpeg") -> str:
    """
    Uploads a file to Google Drive under a specific folder (DRIVE_FOLDER_ID) shared with the service account.
    Returns the public download link of the file.
    """
    folder_id = os.getenv("DRIVE_FOLDER_ID")
    if not folder_id:
        logger.error("DRIVE_FOLDER_ID env variable is not set. Cannot upload to Drive.")
        raise ValueError("DRIVE_FOLDER_ID env variable is not set.")

    creds = get_google_creds()
    if not creds:
        raise ValueError("Google Credentials could not be loaded.")
    
    if not creds.valid:
        creds.refresh(Request())
    
    access_token = creds.token

    # 1. Upload file media content
    upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=media"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": mime_type
    }
    
    logger.info(f"Uploading file '{filename}' to Google Drive...")
    res = requests.post(upload_url, headers=headers, data=file_content)
    if res.status_code != 200:
        logger.error(f"Failed to upload media to Google Drive: {res.status_code} - {res.text}")
        raise Exception(f"Google Drive upload failed: {res.text}")
        
    file_id = res.json().get("id")
    
    # 2. Update metadata (set filename and parent folder ID)
    logger.info(f"Setting metadata for file ID '{file_id}' (filename: '{filename}', parent: '{folder_id}')...")
    patch_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?addParents={folder_id}"
    patch_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    patch_data = {
        "name": filename
    }
    res_patch = requests.patch(patch_url, headers=patch_headers, json=patch_data)
    if res_patch.status_code != 200:
        logger.warning(f"Failed to update metadata/parents for file '{file_id}': {res_patch.text}")

    # 3. Create permission to make the file readable by anyone with the link
    logger.info(f"Setting public permissions for file ID '{file_id}'...")
    perm_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
    perm_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    perm_data = {
        "role": "reader",
        "type": "anyone"
    }
    res_perm = requests.post(perm_url, headers=perm_headers, json=perm_data)
    if res_perm.status_code != 200:
        logger.warning(f"Failed to set public permission on Google Drive file '{file_id}': {res_perm.text}")

    # Return the direct public download link
    public_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    logger.info(f"Successfully uploaded to Google Drive. Public URL: {public_url}")
    return public_url

def upload_to_cloudinary(file_content: bytes, filename: str) -> str:
    """
    Uploads a file to Cloudinary if configured.
    """
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
    preset = os.getenv("CLOUDINARY_UPLOAD_PRESET") # can use unsigned upload preset
    
    if not cloud_name:
        raise ValueError("CLOUDINARY_CLOUD_NAME is not set.")

    # We can do signed or unsigned upload. Unsigned is easiest if preset is set.
    url = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
    
    if preset:
        # Unsigned upload
        data = {
            "upload_preset": preset,
            "public_id": os.path.splitext(filename)[0]
        }
        files = {
            "file": file_content
        }
        res = requests.post(url, data=data, files=files)
    else:
        # Signed upload requires generating a signature, let's keep it simple with unsigned preset
        raise ValueError("Cloudinary unsigned upload requires CLOUDINARY_UPLOAD_PRESET.")
        
    if res.status_code != 200:
        logger.error(f"Cloudinary upload failed: {res.status_code} - {res.text}")
        raise Exception(f"Cloudinary upload failed: {res.text}")
        
    return res.json().get("secure_url")

def upload_image(file_content: bytes, filename: str, mime_type: str = "image/jpeg") -> str:
    """
    Generic upload function. Checks environment variables to decide where to upload:
    1. Google Drive (if DRIVE_FOLDER_ID is set)
    2. Cloudinary (if CLOUDINARY_CLOUD_NAME is set)
    3. Local filesystem (fallback)
    """
    # 1. Google Drive
    if os.getenv("DRIVE_FOLDER_ID"):
        try:
            return upload_to_google_drive(file_content, filename, mime_type)
        except Exception as e:
            logger.error(f"Google Drive upload failed: {e}. Falling back to local/other storage.")

    # 2. Cloudinary
    if os.getenv("CLOUDINARY_CLOUD_NAME"):
        try:
            return upload_to_cloudinary(file_content, filename)
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}. Falling back to local/other storage.")

    # 3. Fallback to Local Filesystem
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # Return absolute path
    return os.path.abspath(file_path)
