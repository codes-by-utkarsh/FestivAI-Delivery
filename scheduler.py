import os
import logging
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import pytz
from database import init_db, get_customers_sheet, get_festivals_sheet, get_video_logs_sheet
from video_engine import generate_video, get_next_photo_index
import uuid

logger = logging.getLogger(__name__)



def upload_video_to_meta(video_path: str) -> str:
    WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
    WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
    if not WHATSAPP_API_URL or not WHATSAPP_TOKEN:
        logger.error("WhatsApp credentials not configured (WHATSAPP_API_URL / WHATSAPP_TOKEN missing in .env). Cannot upload media.")
        return None
    media_url = WHATSAPP_API_URL.replace("/messages", "/media")
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}"
    }
    try:
        with open(video_path, 'rb') as f:
            files = {
                'file': (os.path.basename(video_path), f, 'video/mp4')
            }
            data = {
                'type': 'video/mp4',
                'messaging_product': 'whatsapp'
            }
            response = requests.post(media_url, headers=headers, files=files, data=data, timeout=30)
            
        if response.status_code == 200:
            media_id = response.json().get('id')
            logger.info(f"Successfully uploaded video to Meta. Media ID: {media_id}")
            return media_id
        else:
            logger.error(f"Failed to upload media to Meta: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Media upload exception: {e}")
        return None

def send_whatsapp_video(whatsapp_number: str, media_id: str, template_name: str = "hello_world") -> bool:
    WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
    WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
    if not WHATSAPP_API_URL or not WHATSAPP_TOKEN:
        logger.error("WhatsApp credentials not configured. Cannot send message.")
        return False
    if not media_id:
        logger.error("No valid media_id provided. Cannot send WhatsApp message.")
        return False

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Meta requires a pre-approved template for business-initiated messages.
    # The payload dynamically attaches the uploaded video's media_id to the template header.
    payload = {
        "messaging_product": "whatsapp",
        "to": whatsapp_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en_US"},
            "components": [
                {
                    "type": "header",
                    "parameters": [{"type": "video", "video": {"id": media_id}}]
                }
            ]
        }
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload, timeout=10)
            if response.status_code in [200, 201]:
                return True
            else:
                logger.error(f"WhatsApp API error: {response.text}")
        except Exception as e:
            logger.error(f"Request failed: {e}")
    return False

def daily_job():
    logger.info("Starting daily background job")
    try:
        sheet = init_db()
        if not sheet:
            logger.error("DB not initialized, skipping job.")
            return

        festivals_ws = get_festivals_sheet(sheet)
        customers_ws = get_customers_sheet(sheet)
        logs_ws = get_video_logs_sheet(sheet)
        
        tomorrow_date = (datetime.now(pytz.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
        festivals = festivals_ws.get_all_records()
        tomorrow_festivals = [f for f in festivals if f.get("date") == tomorrow_date]
        
        if not tomorrow_festivals:
            logger.info("No festivals tomorrow. Job finished.")
            return
            
        customers = customers_ws.get_all_records()
        today_date = datetime.now(pytz.utc).strftime("%Y-%m-%d")
        
        active_customers = []
        for idx, c in enumerate(customers):
            sub_end = c.get("subscription_end")
            if sub_end and today_date <= sub_end and c.get("status", "Active") == "Active":
                active_customers.append((idx + 2, c)) 
                
        for festival in tomorrow_festivals:
            festival_name = festival.get("name")
            festival_id = festival.get("festival_id")
            
            for row_num, customer in active_customers:
                customer_id = customer.get("customer_id")
                last_used_photo = int(customer.get("last_used_photo") or 0)
                next_photo_idx = get_next_photo_index(last_used_photo)
                
                video_path = generate_video(customer, festival_name, next_photo_idx)
                
                if video_path:
                    customers_ws.update_cell(row_num, 19, next_photo_idx)
                    
                    media_id = upload_video_to_meta(video_path)
                    success = send_whatsapp_video(customer.get("whatsapp"), media_id)
                    
                    log_id = str(uuid.uuid4())
                    logs_ws.append_row([
                        log_id, customer_id, festival_id, media_id or "Upload Failed",
                        "Sent" if success else "Failed", datetime.now(pytz.utc).isoformat()
                    ])
                    
                    if os.path.exists(video_path):
                        os.remove(video_path)
                        
    except Exception as e:
        logger.error(f"Error in daily job: {e}")

def start_scheduler():
    scheduler = BackgroundScheduler(timezone=pytz.utc)
    scheduler.add_job(daily_job, 'cron', hour=0, minute=0)
    scheduler.start()
    logger.info("Scheduler started.")
