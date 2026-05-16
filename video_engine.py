import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS
from moviepy.editor import AudioFileClip, CompositeVideoClip, ImageClip, TextClip
import requests
import uuid
import logging
import tempfile

logger = logging.getLogger(__name__)

def download_image(url, save_path):
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return save_path
    except Exception as e:
        logger.error(f"Failed to download image from {url}: {e}")
        return None

def create_voiceover(company_name: str, festival_name: str, output_audio_path: str):
    try:
        text = f"Greetings from {company_name}! Wishing you a Happy {festival_name}!"
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(output_audio_path)
        return output_audio_path
    except Exception as e:
        logger.error(f"Failed to create voiceover: {e}")
        return None

def generate_video(customer_data: dict, festival_name: str, photo_index: int):
    try:
        temp_dir = tempfile.mkdtemp(prefix="video_temp_")
        
        company_name = customer_data.get("company_name", "Company")
        owner_name = customer_data.get("owner_name", "Owner")
        whatsapp = customer_data.get("whatsapp", "")
        address = customer_data.get("address", "")
        logo_url = customer_data.get("logo_url", "")
        
        photo_key = f"photo{photo_index}"
        photo_url = customer_data.get(photo_key)

        if not photo_url:
            logger.error("No photo URL provided for index")
            return None

        photo_path = os.path.join(temp_dir, "bg_photo.jpg")
        logo_path = os.path.join(temp_dir, "logo.png")
        
        download_image(photo_url, photo_path)
        if logo_url:
            download_image(logo_url, logo_path)

        audio_path = os.path.join(temp_dir, "voiceover.mp3")
        create_voiceover(company_name, festival_name, audio_path)

        if os.path.exists(photo_path):
            base_clip = ImageClip(photo_path).resize(width=1080)
            if base_clip.h < 1080:
                base_clip = base_clip.margin(top=(1080-base_clip.h)//2, bottom=(1080-base_clip.h)//2, color=(0,0,0))
            elif base_clip.h > 1080:
                base_clip = base_clip.crop(y1=(base_clip.h-1080)//2, y2=(base_clip.h+1080)//2)
        else:
            base_clip = ImageClip(np.zeros((1080, 1080, 3), dtype=np.uint8))
            
        audio_clip = AudioFileClip(audio_path)
        duration = max(20.0, audio_clip.duration + 2.0)
        if duration > 30.0:
            duration = 30.0
            
        base_clip = base_clip.set_duration(duration)
        base_clip = base_clip.set_audio(audio_clip)

        overlays = []
        
        if os.path.exists(logo_path):
            logo_clip = ImageClip(logo_path).resize(height=150).margin(right=20, top=20, opacity=0).set_pos(("right", "top")).set_duration(duration)
            overlays.append(logo_clip)

        def create_text(text, fontsize, color, pos):
            try:
                tc = TextClip(text, fontsize=fontsize, color=color, bg_color='rgba(0,0,0,0.5)')
                return tc.set_pos(pos).set_duration(duration)
            except Exception as e:
                logger.warning(f"Failed to create TextClip for {text}: {e}")
                return None
                
        # Add fadein to texts
        text_company = create_text(company_name, 60, 'white', ('center', 800))
        if text_company: overlays.append(text_company.crossfadein(1))
        
        text_owner = create_text(f"By: {owner_name}", 40, 'yellow', ('center', 880))
        if text_owner: overlays.append(text_owner.crossfadein(1.5))
        
        text_contact = create_text(f"WA: {whatsapp} | {address}", 30, 'white', ('center', 940))
        if text_contact: overlays.append(text_contact.crossfadein(2))
        
        # Simple zoom effect (10% over the duration)
        # Note: resize function takes time t and returns a scaling factor
        def zoom_in(t):
            return 1 + 0.1 * (t / duration)
            
        animated_bg = base_clip.resize(zoom_in).set_position('center').crop(x_center=540, y_center=540, width=1080, height=1080)
        
        final_video = CompositeVideoClip([animated_bg] + overlays)
        
        output_video_path = f"output_{uuid.uuid4().hex}.mp4"
        final_video.write_videofile(output_video_path, fps=24, codec="libx264", audio_codec="aac")
        
        return output_video_path

    except Exception as e:
        logger.error(f"Error generating video: {e}")
        return None

def get_next_photo_index(last_used: int) -> int:
    next_idx = last_used + 1
    if next_idx > 10:
        next_idx = 1
    return next_idx
