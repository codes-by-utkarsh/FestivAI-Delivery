import os
import json
import requests
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def main():
    if not os.path.exists('credentials.json'):
        print("credentials.json not found in root")
        return
        
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    if not creds.valid:
        creds.refresh(Request())
    
    access_token = creds.token
    print(f"Token acquired: {access_token[:15]}...")
    
    # 1. Upload a dummy text file to test
    file_content = b"Hello, this is a test image content hosted on Google Drive."
    filename = "test_drive_upload.txt"
    mime_type = "text/plain"
    
    upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=media"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": mime_type
    }
    
    print("Uploading file to Google Drive...")
    res = requests.post(upload_url, headers=headers, data=file_content)
    if res.status_code != 200:
        print(f"Upload failed: {res.status_code} - {res.text}")
        return
        
    file_id = res.json().get("id")
    print(f"File uploaded successfully! File ID: {file_id}")
    
    # 2. Rename file (PATCH metadata)
    print("Setting filename...")
    patch_url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    patch_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    patch_data = {"name": filename}
    res_patch = requests.patch(patch_url, headers=patch_headers, json=patch_data)
    print(f"Rename response: {res_patch.status_code}")
    
    # 3. Create permission to make it public
    print("Setting permissions to public reader...")
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
    print(f"Permission response: {res_perm.status_code} - {res_perm.text}")
    
    # 4. Check if we can read the file without authentication
    public_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    print(f"Testing public URL: {public_url}")
    res_get = requests.get(public_url)
    print(f"Public URL GET response: {res_get.status_code}")
    print(f"Public URL GET content: {res_get.text}")

if __name__ == "__main__":
    main()
