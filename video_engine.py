"""
video_engine.py
---------------
Core video-generation engine used by main.py and scheduler.py.
Builds rich 1080×1080 branded MP4 festival greeting videos.
"""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
from typing import Optional

import cv2
import numpy as np
import requests
from gtts import gTTS
from moviepy.audio.AudioClip import CompositeAudioClip
from moviepy.editor import AudioFileClip
from moviepy.video.VideoClip import VideoClip
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

CONFIG = {
    "width": 720,
    "height": 720,
    "min_duration": 20,
    "max_duration": 30,
    "fps": 24,
    "background_music": "assets/background_music.mp3",
    "font_bold":    "assets/fonts/Poppins-Bold.ttf",
    "font_regular": "assets/fonts/Poppins-Regular.ttf",
    "overlay_bg_color": (5, 5, 20, 190),
    "accent_color":     (255, 130, 0),
    "text_color":       (255, 255, 255),
    "tts_lang": "en",
}

# ── Festival greeting lookup ──────────────────────────────────────────────────
GREETINGS: dict[str, str] = {
    "diwali":       "May light and prosperity fill your life! 🪔",
    "holi":         "May your life be colourful and joyful! 🎨",
    "eid":          "Eid Mubarak! Peace and blessings to you. ☪️",
    "christmas":    "Merry Christmas! Warmth, love, and joy. 🎄",
    "new year":     "Happy New Year! Here's to new beginnings! 🎊",
    "navratri":     "May Goddess Durga bless you! 🌸",
    "dussehra":     "May good triumph over evil in your life! 🏹",
    "raksha":       "Celebrating the timeless bond of love! 🪢",
    "janmashtami":  "Jai Shri Krishna! Joy and wisdom to you. 🪈",
    "ganesh":       "Ganpati Bappa Morya! Remove all obstacles! 🐘",
    "independence": "Jai Hind! Happy Independence Day! 🇮🇳",
    "republic":     "Proud to be Indian! Happy Republic Day! 🇮🇳",
    "onam":         "Happy Onam! Peace and abundance to you! 🌺",
    "pongal":       "Happy Pongal! Harvest season blessings! 🌾",
    "default":      "Warm Festive Greetings to you and your family! 🎉",
}


def get_greeting(festival_name: str) -> str:
    name_lower = festival_name.lower()
    for key, greeting in GREETINGS.items():
        if key in name_lower:
            return greeting
    return GREETINGS["default"]


# ── Font loader ───────────────────────────────────────────────────────────────

def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except (IOError, OSError):
        return ImageFont.load_default()


# ── Image fetch (URL or local path) ──────────────────────────────────────────

def get_image(url_or_path: str, save_path: Optional[str] = None) -> Optional[str]:
    if not url_or_path:
        return None
    if url_or_path.startswith("http"):
        if not save_path:
            save_path = f"temp_image_{uuid.uuid4().hex}.jpg"
        try:
            response = requests.get(url_or_path, stream=True, timeout=10)
            response.raise_for_status()
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return save_path
        except Exception as exc:
            logger.error("Failed to download image from %s: %s", url_or_path, exc)
            return None
    elif os.path.exists(url_or_path):
        return url_or_path
    return None


# ── Branded frame composer ────────────────────────────────────────────────────

def build_branded_frame(
    photo: Image.Image,
    customer: dict,
    festival_name: str,
    frame_size: tuple[int, int] = (1080, 1080),
) -> Image.Image:
    """
    Compose a rich 1080×1080 branded frame with:
      - Full-bleed photo background (cover crop)
      - Radial vignette for cinematic depth
      - Top frosted bar with festival greeting
      - Orange accent lines (top + bottom)
      - Bottom dark gradient with company name, owner, WhatsApp, address
      - Festival name badge (bottom-right)
      - Company logo (top-right, white rounded container)
    """
    W, H = frame_size

    # 1. Background photo (cover crop)
    ratio = max(W / photo.width, H / photo.height)
    new_w, new_h = int(photo.width * ratio), int(photo.height * ratio)
    photo = photo.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - W) // 2
    top  = (new_h - H) // 2
    frame = photo.crop((left, top, left + W, top + H)).convert("RGBA")

    # 2. Vignette (radial dark edge)
    vignette_np = np.zeros((H, W, 4), dtype=np.uint8)
    cx, cy = W / 2.0, H / 2.0
    y_idx, x_idx = np.ogrid[:H, :W]
    dist = np.sqrt(((x_idx - cx) / (W / 2.0)) ** 2 + ((y_idx - cy) / (H / 2.0)) ** 2)
    alpha_ch = np.clip((dist - 0.5) / 0.5 * 150, 0, 150).astype(np.uint8)
    vignette_np[:, :, 3] = alpha_ch
    frame.alpha_composite(Image.fromarray(vignette_np, "RGBA"))

    # 3. Top frosted strip (greeting)
    top_h = 110
    top_strip = Image.new("RGBA", (W, top_h), (0, 0, 0, 0))
    ts_draw = ImageDraw.Draw(top_strip)
    for y in range(top_h):
        a = int(200 * (1 - y / top_h))
        ts_draw.line([(0, y), (W, y)], fill=(5, 5, 20, a))
    frame.alpha_composite(top_strip, dest=(0, 0))

    # 4. Orange accent line below top strip
    frame.alpha_composite(
        Image.new("RGBA", (W, 4), (*CONFIG["accent_color"], 255)),
        dest=(0, top_h),
    )

    # 5. Bottom gradient strip
    strip_h = 310
    bot_strip = Image.new("RGBA", (W, strip_h), (0, 0, 0, 0))
    bs_draw = ImageDraw.Draw(bot_strip)
    for y in range(strip_h):
        a = int(230 * (y / strip_h))
        bs_draw.line([(0, y), (W, y)], fill=(5, 5, 20, a))
    frame.alpha_composite(bot_strip, dest=(0, H - strip_h))

    # 6. Orange accent line at top of bottom strip
    frame.alpha_composite(
        Image.new("RGBA", (W, 3), (*CONFIG["accent_color"], 255)),
        dest=(0, H - strip_h),
    )

    draw = ImageDraw.Draw(frame)
    tc = CONFIG["text_color"]

    f_xl  = load_font(CONFIG["font_bold"],    62)
    f_lg  = load_font(CONFIG["font_bold"],    38)
    f_md  = load_font(CONFIG["font_bold"],    30)
    f_reg = load_font(CONFIG["font_regular"], 26)
    f_sm  = load_font(CONFIG["font_regular"], 22)
    f_gr  = load_font(CONFIG["font_bold"],    34)

    # 7. Greeting text (top strip)
    draw.text((24, 22), f"✦  {get_greeting(festival_name)}", font=f_gr, fill=tc)

    # 8. Branding block (bottom strip)
    bx = 28
    by = H - strip_h + 26

    # Company name (large, white)
    draw.text((bx, by), customer.get("company_name", "Company"), font=f_xl, fill=tc)

    # Owner (golden accent)
    draw.text((bx, by + 76),
              f"Owner: {customer.get('owner_name', '')}", font=f_lg,
              fill=(255, 200, 80))

    # Thin horizontal divider
    draw.line([(bx, by + 128), (W - bx, by + 128)],
              fill=(255, 255, 255, 60), width=1)

    # Contact info
    draw.text((bx, by + 142), f"📱  {customer.get('whatsapp', '')}",
              font=f_reg, fill=(220, 220, 240))
    draw.text((bx, by + 178), f"📍  {customer.get('address', '')}",
              font=f_reg, fill=(200, 200, 220))

    # 9. Festival badge (bottom-right pill)
    badge_text = f"🎉  Happy {festival_name}"
    bbox = draw.textbbox((0, 0), badge_text, font=f_md)
    bw = bbox[2] - bbox[0] + 30
    bh = bbox[3] - bbox[1] + 18
    badge_x = W - bw - 22
    badge_y = H - bh - 22
    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + bw, badge_y + bh],
        radius=14,
        fill=(255, 120, 0, 230),
    )
    draw.text((badge_x + 15, badge_y + 9), badge_text, font=f_md, fill=tc)

    # 10. Company logo (top-right)
    logo_src = customer.get("logo_url") or customer.get("logo_path") or ""
    if logo_src:
        tmp_logo = get_image(logo_src, f"temp_logo_{uuid.uuid4().hex}.png")
        if tmp_logo and os.path.exists(tmp_logo):
            try:
                logo = Image.open(tmp_logo).convert("RGBA")
                logo.thumbnail((148, 148), Image.LANCZOS)
                pad = 10
                lw, lh = logo.size
                bg = Image.new("RGBA", (lw + pad * 2, lh + pad * 2),
                               (255, 255, 255, 230))
                bg.alpha_composite(logo, dest=(pad, pad))
                frame.alpha_composite(bg, dest=(W - bg.width - 20, 18))
            except Exception as exc:
                logger.warning("Logo load failed: %s", exc)
                draw.text((W - 220, 22),
                          customer.get("company_name", "")[:14], font=f_sm, fill=tc)
            finally:
                if logo_src.startswith("http") and os.path.exists(tmp_logo):
                    os.remove(tmp_logo)
    else:
        draw.text((W - 220, 22),
                  customer.get("company_name", "")[:14], font=f_sm, fill=tc)

    return frame.convert("RGB")


# ── Video generator ───────────────────────────────────────────────────────────

def generate_video(customer_data: dict, festival_name: str,
                   photo_index: int) -> Optional[str]:
    """
    Generate a branded festival greeting MP4 for one customer.
    Returns the output file path, or None on failure.
    """
    try:
        tmp_dir   = tempfile.mkdtemp(prefix="festivai_")
        W, H      = CONFIG["width"], CONFIG["height"]
        fps       = CONFIG["fps"]
        duration  = 22.0   # seconds

        # ── Pick photo ────────────────────────────────────────────────────────
        photo_key      = f"photo{photo_index}"
        photo_src      = customer_data.get(photo_key) or ""
        photo_path     = os.path.join(tmp_dir, "bg_photo.jpg")
        actual_photo   = get_image(photo_src, photo_path)

        if actual_photo and os.path.exists(actual_photo):
            try:
                photo_img = Image.open(actual_photo).convert("RGB")
            except Exception as exc:
                logger.error("Cannot open photo: %s", exc)
                photo_img = Image.new("RGB", (W, H), (25, 35, 70))
        else:
            logger.warning("Photo not found for index %s – using placeholder.", photo_index)
            photo_img = Image.new("RGB", (W, H), (25, 35, 70))

        # ── Voiceover ─────────────────────────────────────────────────────────
        tts_text = (
            f"Greetings from {customer_data.get('company_name', 'us')}! "
            f"Wishing you a wonderful {festival_name}. "
            f"Contact us at {customer_data.get('whatsapp', '')}."
        )
        audio_path = os.path.join(tmp_dir, "voiceover.mp3")
        try:
            gTTS(text=tts_text, lang=CONFIG["tts_lang"], slow=False).save(audio_path)
        except Exception as exc:
            logger.warning("TTS failed: %s", exc)
            audio_path = None

        # ── Build frame ───────────────────────────────────────────────────────
        branded    = build_branded_frame(photo_img, customer_data, festival_name, (W, H))
        branded_np = np.array(branded)

        # ── Ken-Burns make_frame ──────────────────────────────────────────────
        def make_frame(t: float) -> np.ndarray:
            scale   = 1.0 + 0.08 * (t / duration)
            new_w   = int(W * scale)
            new_h   = int(H * scale)
            resized = cv2.resize(branded_np, (new_w, new_h),
                                 interpolation=cv2.INTER_LINEAR)
            x0 = (new_w - W) // 2
            y0 = (new_h - H) // 2
            return resized[y0 : y0 + H, x0 : x0 + W]

        clip = VideoClip(make_frame, duration=duration).set_fps(fps)

        # ── Audio ─────────────────────────────────────────────────────────────
        audio_clips = []
        bg_path = CONFIG.get("background_music")
        if bg_path and os.path.exists(bg_path):
            try:
                audio_clips.append(
                    AudioFileClip(bg_path).subclip(0, duration).volumex(0.28)
                )
            except Exception as exc:
                logger.warning("BG music error: %s", exc)

        if audio_path and os.path.exists(audio_path):
            try:
                audio_clips.append(
                    AudioFileClip(audio_path).set_start(1.0).volumex(1.0)
                )
            except Exception as exc:
                logger.warning("Voiceover audio error: %s", exc)

        if audio_clips:
            clip = clip.set_audio(
                CompositeAudioClip(audio_clips).set_duration(duration)
            )

        # ── Write output ──────────────────────────────────────────────────────
        out_path = f"output_{uuid.uuid4().hex}.mp4"
        clip.write_videofile(
            out_path,
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            threads=1,
            preset="ultrafast",
            logger=None,
        )
        logger.info("Video created: %s", out_path)
        return out_path

    except Exception as exc:
        logger.error("Error generating video: %s", exc)
        return None


# ── Photo index cycling ───────────────────────────────────────────────────────

def get_next_photo_index(last_used: int) -> int:
    next_idx = (int(last_used or 0) % 10) + 1
    return next_idx
