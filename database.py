import gspread
import os
import json
from google.oauth2.service_account import Credentials
import logging
import dotenv
dotenv.load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Full Indian festival calendar for 2025-2026
INDIAN_FESTIVALS_2025_2026 = [
    # 2025
    {"date": "2025-01-14", "name": "Makar Sankranti", "type": "Hindu"},
    {"date": "2025-01-26", "name": "Republic Day", "type": "National"},
    {"date": "2025-02-02", "name": "Basant Panchami", "type": "Hindu"},
    {"date": "2025-02-12", "name": "Maha Shivratri", "type": "Hindu"},
    {"date": "2025-03-13", "name": "Holi", "type": "Hindu"},
    {"date": "2025-03-14", "name": "Dhulandi (Holi)", "type": "Hindu"},
    {"date": "2025-03-31", "name": "Eid-ul-Fitr", "type": "Islamic"},
    {"date": "2025-04-06", "name": "Ram Navami", "type": "Hindu"},
    {"date": "2025-04-10", "name": "Mahavir Jayanti", "type": "Jain"},
    {"date": "2025-04-14", "name": "Ambedkar Jayanti", "type": "National"},
    {"date": "2025-04-18", "name": "Good Friday", "type": "Christian"},
    {"date": "2025-04-20", "name": "Easter Sunday", "type": "Christian"},
    {"date": "2025-05-01", "name": "Maharashtra Day", "type": "Regional"},
    {"date": "2025-05-12", "name": "Buddha Purnima", "type": "Buddhist"},
    {"date": "2025-06-07", "name": "Eid-ul-Adha", "type": "Islamic"},
    {"date": "2025-06-27", "name": "Muharram", "type": "Islamic"},
    {"date": "2025-07-07", "name": "Rath Yatra", "type": "Hindu"},
    {"date": "2025-08-09", "name": "Raksha Bandhan", "type": "Hindu"},
    {"date": "2025-08-15", "name": "Independence Day", "type": "National"},
    {"date": "2025-08-16", "name": "Janmashtami", "type": "Hindu"},
    {"date": "2025-09-05", "name": "Teachers Day", "type": "National"},
    {"date": "2025-09-06", "name": "Ganesh Chaturthi", "type": "Hindu"},
    {"date": "2025-09-16", "name": "Milad-un-Nabi", "type": "Islamic"},
    {"date": "2025-10-02", "name": "Gandhi Jayanti", "type": "National"},
    {"date": "2025-10-02", "name": "Navratri Begins", "type": "Hindu"},
    {"date": "2025-10-10", "name": "Dussehra", "type": "Hindu"},
    {"date": "2025-10-14", "name": "Karwa Chauth", "type": "Hindu"},
    {"date": "2025-10-20", "name": "Dhanteras", "type": "Hindu"},
    {"date": "2025-10-21", "name": "Naraka Chaturdashi", "type": "Hindu"},
    {"date": "2025-10-22", "name": "Diwali", "type": "Hindu"},
    {"date": "2025-10-23", "name": "Govardhan Puja", "type": "Hindu"},
    {"date": "2025-10-24", "name": "Bhai Dooj", "type": "Hindu"},
    {"date": "2025-11-05", "name": "Guru Nanak Jayanti", "type": "Sikh"},
    {"date": "2025-11-14", "name": "Children's Day", "type": "National"},
    {"date": "2025-12-25", "name": "Christmas Day", "type": "Christian"},
    {"date": "2025-12-31", "name": "New Year's Eve", "type": "Cultural"},
    # 2026
    {"date": "2026-01-01", "name": "New Year's Day", "type": "National"},
    {"date": "2026-01-14", "name": "Makar Sankranti", "type": "Hindu"},
    {"date": "2026-01-26", "name": "Republic Day", "type": "National"},
    {"date": "2026-02-22", "name": "Maha Shivratri", "type": "Hindu"},
    {"date": "2026-03-02", "name": "Basant Panchami", "type": "Hindu"},
    {"date": "2026-03-03", "name": "Holi", "type": "Hindu"},
    {"date": "2026-03-20", "name": "Eid-ul-Fitr", "type": "Islamic"},
    {"date": "2026-03-26", "name": "Ram Navami", "type": "Hindu"},
    {"date": "2026-03-30", "name": "Mahavir Jayanti", "type": "Jain"},
    {"date": "2026-04-03", "name": "Good Friday", "type": "Christian"},
    {"date": "2026-04-05", "name": "Easter Sunday", "type": "Christian"},
    {"date": "2026-04-14", "name": "Ambedkar Jayanti", "type": "National"},
    {"date": "2026-05-01", "name": "Labour Day", "type": "National"},
    {"date": "2026-05-27", "name": "Eid-ul-Adha", "type": "Islamic"},
    {"date": "2026-05-31", "name": "Buddha Purnima", "type": "Buddhist"},
    {"date": "2026-06-26", "name": "Muharram", "type": "Islamic"},
    {"date": "2026-06-29", "name": "Rath Yatra", "type": "Hindu"},
    {"date": "2026-07-29", "name": "Raksha Bandhan", "type": "Hindu"},
    {"date": "2026-08-05", "name": "Janmashtami", "type": "Hindu"},
    {"date": "2026-08-15", "name": "Independence Day", "type": "National"},
    {"date": "2026-09-05", "name": "Milad-un-Nabi", "type": "Islamic"},
    {"date": "2026-09-05", "name": "Teachers Day", "type": "National"},
    {"date": "2026-09-25", "name": "Ganesh Chaturthi", "type": "Hindu"},
    {"date": "2026-10-02", "name": "Gandhi Jayanti", "type": "National"},
    {"date": "2026-10-06", "name": "Navratri Begins", "type": "Hindu"},
    {"date": "2026-10-14", "name": "Dussehra", "type": "Hindu"},
    {"date": "2026-10-29", "name": "Dhanteras", "type": "Hindu"},
    {"date": "2026-10-30", "name": "Naraka Chaturdashi", "type": "Hindu"},
    {"date": "2026-10-31", "name": "Diwali", "type": "Hindu"},
    {"date": "2026-11-01", "name": "Govardhan Puja", "type": "Hindu"},
    {"date": "2026-11-02", "name": "Bhai Dooj", "type": "Hindu"},
    {"date": "2026-11-14", "name": "Children's Day", "type": "National"},
    {"date": "2026-11-24", "name": "Guru Nanak Jayanti", "type": "Sikh"},
    {"date": "2026-12-25", "name": "Christmas Day", "type": "Christian"},
    {"date": "2026-12-31", "name": "New Year's Eve", "type": "Cultural"},
]

_CACHED_SHEET = None

def init_db():
    global _CACHED_SHEET
    if _CACHED_SHEET is not None:
        return _CACHED_SHEET
    try:
        creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if creds_json:
            if creds_json.endswith('.json'):
                creds = Credentials.from_service_account_file(creds_json, scopes=SCOPES)
            else:
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
                ws = sheet.add_worksheet(title=rs, rows="1000", cols="25")
                logger.info(f"Created missing worksheet: {rs}")
                if rs == "Users":
                    ws.append_row(["user_id", "name", "email", "password_hash", "role", "created_by", "created_at"])
                elif rs == "Customers":
                    ws.append_row(["customer_id", "agent_id", "company_name", "owner_name", "whatsapp",
                                   "address", "logo_url", "photo1", "photo2", "photo3", "photo4", "photo5",
                                   "photo6", "photo7", "photo8", "photo9", "photo10",
                                   "subscription_end", "last_used_photo", "status"])
                elif rs == "Festivals":
                    ws.append_row(["festival_id", "date", "name", "type"])
                elif rs == "Video Logs":
                    ws.append_row(["log_id", "customer_id", "festival_id", "video_url", "sent_status", "sent_at"])
        
        # Seed default admin only if Users sheet is empty
        users_ws = sheet.worksheet("Users")
        if len(users_ws.get_all_records()) == 0:
            import bcrypt, uuid
            from datetime import datetime
            pw_hash = bcrypt.hashpw("Admin@1234".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            users_ws.append_row([str(uuid.uuid4()), "Super Admin", "admin@festivai.com", pw_hash, "Admin", "System", datetime.utcnow().isoformat()])
            logger.info("Seeded default Admin user: admin@festivai.com / Admin@1234")
            
        # Seed full festival calendar if Festivals sheet is empty
        festivals_ws = sheet.worksheet("Festivals")
        if len(festivals_ws.get_all_records()) == 0:
            import uuid
            rows = []
            for f in INDIAN_FESTIVALS_2025_2026:
                rows.append([str(uuid.uuid4()), f["date"], f["name"], f["type"]])
            # Batch insert for efficiency
            festivals_ws.append_rows(rows)
            logger.info(f"Seeded {len(rows)} festivals into the calendar.")
            
        _CACHED_SHEET = sheet
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
