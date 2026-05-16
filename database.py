import gspread
import os
import json
from google.oauth2.service_account import Credentials
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def init_db():
    try:
        creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if creds_json:
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        else:
            if os.path.exists('credentials.json'):
                creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
            else:
                logger.warning("No credentials.json found and GOOGLE_CREDENTIALS_JSON is empty.")
                return None
        
        client = gspread.authorize(creds)
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        if not spreadsheet_id:
            logger.warning("SPREADSHEET_ID env var is not set. Skipping DB initialization.")
            return None
            
        sheet = client.open_by_key(spreadsheet_id)
        sheet_names = [s.title for s in sheet.worksheets()]
        required_sheets = ["Users", "Customers", "Festivals", "Video Logs"]
        
        for rs in required_sheets:
            if rs not in sheet_names:
                ws = sheet.add_worksheet(title=rs, rows="1000", cols="20")
                logger.info(f"Created missing worksheet: {rs}")
                if rs == "Users":
                    ws.append_row(["user_id", "name", "email", "password_hash", "role", "created_by", "created_at"])
                elif rs == "Customers":
                    ws.append_row(["customer_id", "agent_id", "company_name", "owner_name", "whatsapp", "address", "logo_url", "photo1", "photo2", "photo3", "photo4", "photo5", "photo6", "photo7", "photo8", "photo9", "photo10", "subscription_end", "last_used_photo", "status"])
                elif rs == "Festivals":
                    ws.append_row(["festival_id", "date", "name", "type"])
                elif rs == "Video Logs":
                    ws.append_row(["log_id", "customer_id", "festival_id", "video_url", "sent_status", "sent_at"])
        return sheet
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return None

def get_users_sheet(sheet):
    return sheet.worksheet("Users")

def get_customers_sheet(sheet):
    return sheet.worksheet("Customers")

def get_festivals_sheet(sheet):
    return sheet.worksheet("Festivals")

def get_video_logs_sheet(sheet):
    return sheet.worksheet("Video Logs")

if __name__ == "__main__":
    init_db()
