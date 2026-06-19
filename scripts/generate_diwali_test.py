import sys
import os

# Add parent directory to path so we can import video_engine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from video_engine import generate_video

customer = {
    "company_name": "FestivAI Sample Corp",
    "address": "456 Diwali Avenue, New Delhi, India",
    "whatsapp": "919876543210",
    "logo_url": ""  # Leave blank, engine will draw company name
}

festival = {
    "name": "Diwali",
    "template_url": r"d:\Projects\FestivAI-Delivery\Festival_Greeting_Templates_edited-03.png"
}

print("Generating Diwali test video...")
output_path = generate_video(customer, "Diwali", 0, festival)

if output_path:
    print(f"SUCCESS|{output_path}")
else:
    print("FAILED")
