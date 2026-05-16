import os
import requests
from dotenv import load_dotenv
load_dotenv()

from scheduler import upload_video_to_meta

def run_test():
    phone_number = input("Enter your WhatsApp phone number with country code (e.g., 919876543210): ").replace("+", "").strip()
    video_file = input("Enter the path to a test .mp4 file: ")
    
    if not os.path.exists(video_file):
        print(f"Error: Could not find video file at {video_file}")
        return
        
    print("\n1. Uploading video to Meta...")
    media_id = upload_video_to_meta(video_file)
    
    if media_id:
        print(f"Success! Meta returned Media ID: {media_id}")
        
        # To bypass the template format error for testing, we will send a direct video message.
        # This requires an active 24-hour messaging window (you must message the bot first).
        headers = {
            "Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "video",
            "video": {
                "id": media_id,
                "caption": "✨ Here is your automated festival video!"
            }
        }
        
        print("\n2. Sending direct WhatsApp video message...")
        response = requests.post(os.getenv('WHATSAPP_API_URL'), headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            print("\n✅ WhatsApp sent successfully! Check your phone.")
        else:
            print(f"\n❌ Failed to send WhatsApp. Meta Error:\n{response.text}")
    else:
        print("\n❌ Failed to upload video to Meta.")

if __name__ == "__main__":
    run_test()
