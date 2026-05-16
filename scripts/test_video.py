import os
import sys
from video_engine import generate_video

def test_video_engine():
    # 1. Create dummy assets
    print("Creating dummy assets for testing...")
    os.makedirs("test_assets", exist_ok=True)
    
    # We will use public placeholder images for testing
    customer_data = {
        "company_name": "Test Company Ltd",
        "owner_name": "John Doe",
        "whatsapp": "+1234567890",
        "address": "123 Tech Street, Mumbai",
        "logo_url": "https://via.placeholder.com/150/0000FF/808080?Text=Logo",
        "photo1": "https://via.placeholder.com/1080/FF0000/FFFFFF?Text=Company+Photo"
    }
    
    print("Generating video... This may take a minute.")
    try:
        video_path = generate_video(customer_data, "Diwali", photo_index=1)
        if video_path and os.path.exists(video_path):
            print(f"Success! Video generated at: {os.path.abspath(video_path)}")
        else:
            print("Video generation failed.")
    except Exception as e:
        print(f"Error during video generation: {e}")
        print("\nNOTE: If you get an ImageMagick error on Windows, you must install ImageMagick")
        print("and check 'Install legacy utilities (e.g. convert)'.")

if __name__ == "__main__":
    test_video_engine()
