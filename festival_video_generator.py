"""
Festival Video Generation System  (Enhanced)
=============================================
Generates 1080x1080 MP4 greeting videos for festivals:
  - Ken-Burns zoom animation
  - Rich branded overlays (logo, company info, festival greeting)
  - Background music + gTTS voiceover mixed audio
  - Google Drive photo pool with no-consecutive-repeat logic
  - APScheduler daily cron  +  on-demand single-company generation
  - Batch mode: generate for a list of company IDs × a festival

Requirements:
    pip install moviepy opencv-python pillow gtts apscheduler \
                google-api-python-client google-auth-httplib2 \
                google-auth-oauthlib requests numpy
"""

from __future__ import annotations

import io
import logging
import os
import random
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ── Scheduling ────────────────────────────────────────────────────────────────
from apscheduler.schedulers.blocking import BlockingScheduler

# ── Video / Image ─────────────────────────────────────────────────────────────
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.audio.AudioClip import CompositeAudioClip
from moviepy.editor import AudioFileClip
from moviepy.video.VideoClip import VideoClip

# ── TTS ───────────────────────────────────────────────────────────────────────
from gtts import gTTS

# ── Google Drive ──────────────────────────────────────────────────────────────
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

CONFIG: dict = {
    "width": 1080,
    "height": 1080,
    "min_duration": 20,
    "max_duration": 30,
    "fps": 24,

    # Google Drive
    "service_account_file": "credentials.json",
    "drive_folder_id": os.getenv("DRIVE_FOLDER_ID", ""),

    # Assets
    "background_music": "assets/background_music.mp3",
    "font_bold":    "assets/fonts/Poppins-Bold.ttf",
    "font_regular": "assets/fonts/Poppins-Regular.ttf",

    # Overlay colours  (RGBA)
    "overlay_bg_color": (10, 10, 20, 190),
    "accent_color":     (255, 140, 0, 255),   # warm orange
    "text_color":       (255, 255, 255),

    # Output
    "output_dir": "output_videos",
    "tts_lang": "en",
}

# Festival greeting templates keyed by festival name (case-insensitive prefix match)
FESTIVAL_GREETINGS: dict[str, str] = {
    "diwali":       "May the Festival of Lights fill your life with prosperity and joy! 🪔",
    "holi":         "May your life be as colourful and joyful as Holi! 🎨",
    "eid":          "Eid Mubarak! May peace, love and happiness be with you always. ☪️",
    "christmas":    "Merry Christmas! May the season bring warmth, love, and happiness. 🎄",
    "new year":     "Happy New Year! Wishing you success, health, and happiness ahead. 🎊",
    "navratri":     "Navratri Greetings! May Goddess Durga bless you and your family. 🌸",
    "dussehra":     "Happy Dussehra! May good always triumph over evil in your life. 🏹",
    "raksha":       "Happy Raksha Bandhan! Celebrating the timeless bond of love. 🪢",
    "janmashtami":  "Happy Janmashtami! May Lord Krishna bless you with joy and wisdom. 🪈",
    "ganesh":       "Ganpati Bappa Morya! May Lord Ganesha remove all obstacles from your path. 🐘",
    "independence": "Happy Independence Day! Jai Hind! 🇮🇳",
    "republic":     "Happy Republic Day! Proud to be Indian. 🇮🇳",
    "onam":         "Happy Onam! May this harvest festival bring peace and prosperity. 🌺",
    "pongal":       "Happy Pongal! May this harvest season bring abundance to your life. 🌾",
    "default":      "Warm Festive Greetings from all of us to you and your family! 🎉",
}


# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("FestivalVideo")


# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def get_festival_greeting(festival_name: str) -> str:
    """Return a context-appropriate greeting for the given festival."""
    name_lower = festival_name.lower()
    for key, greeting in FESTIVAL_GREETINGS.items():
        if key in name_lower:
            return greeting
    return FESTIVAL_GREETINGS["default"]


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except (IOError, OSError):
        log.warning("Font not found: %s – using PIL default.", path)
        return ImageFont.load_default()


def _draw_rounded_rect(draw: ImageDraw.Draw, xy: tuple, radius: int,
                        fill: tuple) -> None:
    """Draw a rounded rectangle on a PIL ImageDraw canvas."""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)


# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE DRIVE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        CONFIG["service_account_file"],
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    return build("drive", "v3", credentials=creds)


def list_drive_photos(service, folder_id: str) -> list[dict]:
    query = (
        f"'{folder_id}' in parents "
        "and mimeType contains 'image/' "
        "and trashed = false"
    )
    results = service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])


def download_drive_photo(service, file_id: str) -> Image.Image:
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    return Image.open(buf).convert("RGB")


# ─────────────────────────────────────────────────────────────────────────────
# PHOTO SELECTION  (no consecutive repeat)
# ─────────────────────────────────────────────────────────────────────────────

def pick_photo(customer: dict, available_photos: list[dict]) -> dict:
    if not available_photos:
        raise ValueError("No photos available.")
    last = customer.get("last_used_photo")
    candidates = [p for p in available_photos if p["id"] != last]
    chosen = random.choice(candidates) if candidates else random.choice(available_photos)
    customer["last_used_photo"] = chosen["id"]
    return chosen


# ─────────────────────────────────────────────────────────────────────────────
# TEXT-TO-SPEECH
# ─────────────────────────────────────────────────────────────────────────────

def generate_voiceover(text: str, output_path: str) -> str:
    tts = gTTS(text=text, lang=CONFIG["tts_lang"], slow=False)
    tts.save(output_path)
    log.info("Voiceover saved: %s", output_path)
    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# BRANDED FRAME COMPOSER  (enhanced)
# ─────────────────────────────────────────────────────────────────────────────

def build_branded_frame(
    photo: Image.Image,
    customer: dict,
    festival_name: str,
    frame_size: tuple[int, int] = (1080, 1080),
) -> Image.Image:
    """
    Compose a rich 1080×1080 branded frame:
      • Full-bleed festival photo background (cover crop)
      • Subtle vignette for depth
      • Bottom dark gradient strip with company info
      • Top frosted strip with festival greeting + accent line
      • Company logo (top-right, rounded container)
      • Orange accent bar + divider lines
    """
    W, H = frame_size

    # ── 1. Background photo (cover crop) ────────────────────────────────────
    ratio = max(W / photo.width, H / photo.height)
    new_size = (int(photo.width * ratio), int(photo.height * ratio))
    photo = photo.resize(new_size, Image.LANCZOS)
    left = (photo.width - W) // 2
    top  = (photo.height - H) // 2
    frame = photo.crop((left, top, left + W, top + H)).convert("RGBA")

    # ── 2. Vignette overlay (radial dark edges) ──────────────────────────────
    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    for r in range(min(W, H) // 2, 0, -8):
        alpha = int(120 * (1 - r / (min(W, H) / 2)))
        vd.ellipse(
            [W // 2 - r, H // 2 - r, W // 2 + r, H // 2 + r],
            fill=(0, 0, 0, 0),
        )
    # Simple corner vignette via a composited dark radial gradient
    vignette_np = np.zeros((H, W, 4), dtype=np.uint8)
    cx, cy = W / 2, H / 2
    y_idx, x_idx = np.ogrid[:H, :W]
    dist = np.sqrt(((x_idx - cx) / (W / 2)) ** 2 + ((y_idx - cy) / (H / 2)) ** 2)
    alpha_chan = np.clip((dist - 0.55) / 0.45 * 140, 0, 140).astype(np.uint8)
    vignette_np[:, :, 3] = alpha_chan
    vignette_pil = Image.fromarray(vignette_np, "RGBA")
    frame.alpha_composite(vignette_pil)

    # ── 3. Top gradient strip (greeting) ─────────────────────────────────────
    top_h = 110
    top_strip = Image.new("RGBA", (W, top_h), (0, 0, 0, 0))
    for y in range(top_h):
        alpha = int(200 * (1 - y / top_h))
        ImageDraw.Draw(top_strip).line([(0, y), (W, y)], fill=(5, 5, 15, alpha))
    frame.alpha_composite(top_strip, dest=(0, 0))

    # Accent line under top strip
    accent_bar = Image.new("RGBA", (W, 4), CONFIG["accent_color"])
    frame.alpha_composite(accent_bar, dest=(0, top_h))

    # ── 4. Bottom gradient strip (branding) ──────────────────────────────────
    strip_h = 300
    bottom_strip = Image.new("RGBA", (W, strip_h), (0, 0, 0, 0))
    for y in range(strip_h):
        alpha = int(220 * (y / strip_h))
        ImageDraw.Draw(bottom_strip).line([(0, y), (W, y)], fill=(5, 5, 15, alpha))
    frame.alpha_composite(bottom_strip, dest=(0, H - strip_h))

    # Accent line above bottom strip
    frame.alpha_composite(
        Image.new("RGBA", (W, 3), CONFIG["accent_color"]),
        dest=(0, H - strip_h),
    )

    draw = ImageDraw.Draw(frame)
    tc = CONFIG["text_color"]

    font_bold_xl  = load_font(CONFIG["font_bold"],    60)
    font_bold_lg  = load_font(CONFIG["font_bold"],    40)
    font_bold_md  = load_font(CONFIG["font_bold"],    30)
    font_reg      = load_font(CONFIG["font_regular"], 26)
    font_greeting = load_font(CONFIG["font_bold"],    34)
    font_small    = load_font(CONFIG["font_regular"], 22)

    # ── 5. Festival greeting (top strip) ─────────────────────────────────────
    greeting = get_festival_greeting(festival_name)
    draw.text((24, 22), f"✦  {greeting}", font=font_greeting, fill=tc)

    # ── 6. Branding text (bottom strip) ──────────────────────────────────────
    bx = 28
    by = H - strip_h + 28
    company_name = customer.get("company_name", "Company")
    owner_name   = customer.get("owner_name", "Owner")
    whatsapp     = customer.get("whatsapp", "")
    address      = customer.get("address", "")

    draw.text((bx, by),       company_name, font=font_bold_xl, fill=tc)
    draw.text((bx, by + 72),  f"Owner: {owner_name}", font=font_bold_lg,
              fill=(255, 200, 100))
    # Thin divider
    draw.line([(bx, by + 122), (W - bx, by + 122)], fill=(255, 255, 255, 60), width=1)

    draw.text((bx, by + 136), f"📱  {whatsapp}", font=font_reg, fill=(220, 220, 230))
    draw.text((bx, by + 170), f"📍  {address}",  font=font_reg, fill=(200, 200, 215))

    # Festival name badge (bottom-right)
    badge_text = f"🎉  Happy {festival_name}"
    bbox = draw.textbbox((0, 0), badge_text, font=font_bold_md)
    bw = bbox[2] - bbox[0] + 28
    bh = bbox[3] - bbox[1] + 16
    badge_x = W - bw - 24
    badge_y = H - 52
    _draw_rounded_rect(draw, (badge_x, badge_y, badge_x + bw, badge_y + bh),
                        radius=12, fill=(255, 120, 0, 220))
    draw.text((badge_x + 14, badge_y + 8), badge_text, font=font_bold_md, fill=tc)

    # ── 7. Company Logo (top-right) ──────────────────────────────────────────
    logo_path = customer.get("logo_url") or customer.get("logo_path") or ""
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo.thumbnail((150, 150), Image.LANCZOS)
            # White rounded background for logo
            pad = 10
            lw, lh = logo.size
            bg = Image.new("RGBA", (lw + pad * 2, lh + pad * 2), (255, 255, 255, 230))
            bg.alpha_composite(logo, dest=(pad, pad))
            frame.alpha_composite(bg, dest=(W - bg.width - 20, 18))
        except Exception as exc:
            log.warning("Logo load failed: %s", exc)
            draw.text((W - 220, 22), company_name[:14], font=font_small, fill=tc)
    else:
        # Text logo fallback
        draw.text((W - 220, 22), company_name[:14], font=font_small, fill=tc)

    return frame.convert("RGB")


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO ASSEMBLY
# ─────────────────────────────────────────────────────────────────────────────

def create_video(
    customer: dict,
    festival_name: str,
    photo_img: Image.Image,
    output_path: str,
    duration: int = 25,
) -> str:
    """
    Build the final MP4:
      • Ken-Burns zoom-in animation (scale 1.0 → 1.08)
      • Background music (0.3× volume) + gTTS voiceover (1.0×, starts at 1 s)
    """
    W, H = CONFIG["width"], CONFIG["height"]
    fps   = CONFIG["fps"]

    with tempfile.TemporaryDirectory() as tmp:

        # ── 1. Voiceover ────────────────────────────────────────────────────
        tts_text = (
            f"Greetings from {customer.get('company_name', 'us')}! "
            f"Wishing you a wonderful {festival_name}. "
            f"{get_festival_greeting(festival_name)} "
            f"Contact us at {customer.get('whatsapp', '')}."
        )
        vo_path = os.path.join(tmp, "voiceover.mp3")
        try:
            generate_voiceover(tts_text, vo_path)
        except Exception as exc:
            log.warning("Voiceover failed: %s", exc)
            vo_path = None

        # ── 2. Branded frame → numpy array ───────────────────────────────────
        branded    = build_branded_frame(photo_img, customer, festival_name, (W, H))
        branded_np = np.array(branded)

        # ── 3. Ken-Burns make_frame ───────────────────────────────────────────
        def make_frame(t: float) -> np.ndarray:
            progress = t / duration
            scale    = 1.0 + 0.08 * progress
            new_w    = int(W * scale)
            new_h    = int(H * scale)
            resized  = cv2.resize(branded_np, (new_w, new_h),
                                  interpolation=cv2.INTER_LINEAR)
            x0 = (new_w - W) // 2
            y0 = (new_h - H) // 2
            return resized[y0 : y0 + H, x0 : x0 + W]

        clip = VideoClip(make_frame, duration=duration).set_fps(fps)

        # ── 4. Audio mix ──────────────────────────────────────────────────────
        audio_clips: list = []
        bg_path = CONFIG.get("background_music")
        if bg_path and os.path.exists(bg_path):
            try:
                bg = AudioFileClip(bg_path).subclip(0, duration).volumex(0.28)
                audio_clips.append(bg)
            except Exception as exc:
                log.warning("BG music failed: %s", exc)

        if vo_path and os.path.exists(vo_path):
            try:
                vo = AudioFileClip(vo_path).set_start(1.0).volumex(1.0)
                audio_clips.append(vo)
            except Exception as exc:
                log.warning("Voiceover audio failed: %s", exc)

        if audio_clips:
            clip = clip.set_audio(
                CompositeAudioClip(audio_clips).set_duration(duration)
            )

        # ── 5. Write ──────────────────────────────────────────────────────────
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        clip.write_videofile(
            output_path,
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            logger=None,
        )
        log.info("Video saved → %s", output_path)

    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# HIGH-LEVEL HELPERS  (used by scheduler + batch API)
# ─────────────────────────────────────────────────────────────────────────────

def _get_photo_for_customer(
    customer: dict,
    drive_svc=None,
    all_drive_photos: Optional[list] = None,
) -> Image.Image:
    """
    Try photos in this order:
      1. Local photo slots (photo1…photo10) stored in customer dict
      2. Google Drive folder photo pool
      3. Solid-colour placeholder
    """
    # Local photos stored as absolute paths in the customer record
    for i in range(1, 11):
        path = customer.get(f"photo{i}", "")
        if path and os.path.exists(path):
            try:
                return Image.open(path).convert("RGB")
            except Exception:
                continue

    # Drive fallback
    if drive_svc and all_drive_photos:
        try:
            chosen = pick_photo(customer, all_drive_photos)
            return download_drive_photo(drive_svc, chosen["id"])
        except Exception as exc:
            log.warning("Drive photo fetch failed: %s", exc)

    # Placeholder
    log.warning("No photo found for %s – using placeholder.", customer.get("company_name"))
    return Image.new("RGB", (1080, 1080), (30, 40, 80))


def generate_for_customer(
    customer: dict,
    festival_name: str,
    drive_svc=None,
    all_drive_photos: Optional[list] = None,
    output_dir: Optional[str] = None,
) -> Optional[str]:
    """
    Generate a single branded video for one customer × one festival.
    Returns the output file path on success, None on failure.
    """
    output_dir = output_dir or CONFIG["output_dir"]
    os.makedirs(output_dir, exist_ok=True)

    try:
        photo_img = _get_photo_for_customer(customer, drive_svc, all_drive_photos)
        duration  = random.randint(CONFIG["min_duration"], CONFIG["max_duration"])
        date_str  = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = customer.get("company_name", "company").replace(" ", "_")
        safe_fest = festival_name.replace(" ", "_")
        filename  = f"{date_str}_{safe_name}_{safe_fest}_{uuid.uuid4().hex[:6]}.mp4"
        out_path  = os.path.join(output_dir, filename)

        create_video(customer, festival_name, photo_img, out_path, duration)
        return out_path

    except Exception as exc:
        log.exception("Video generation failed for %s / %s: %s",
                      customer.get("company_name"), festival_name, exc)
        return None


def batch_generate(
    customers: list[dict],
    festival_name: str,
    output_dir: Optional[str] = None,
) -> dict[str, Optional[str]]:
    """
    Generate videos for multiple customers for a single festival.
    Returns a mapping of customer_id → output_path (or None on failure).
    """
    drive_svc, all_photos = None, []
    folder_id = CONFIG.get("drive_folder_id", "")
    if folder_id:
        try:
            drive_svc  = get_drive_service()
            all_photos = list_drive_photos(drive_svc, folder_id)
            log.info("Drive pool: %d photos.", len(all_photos))
        except Exception as exc:
            log.warning("Drive unavailable: %s", exc)

    results: dict[str, Optional[str]] = {}
    for customer in customers:
        cid = customer.get("customer_id", str(uuid.uuid4()))
        log.info("Generating: %s × %s", customer.get("company_name"), festival_name)
        results[cid] = generate_for_customer(
            customer, festival_name, drive_svc, all_photos, output_dir
        )

    return results


# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE DATA  (for standalone testing)
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_FESTIVALS = [
    {"name": "Diwali",       "date": "2025-10-22"},
    {"name": "Holi",         "date": "2025-03-13"},
    {"name": "Eid-ul-Fitr",  "date": "2025-03-31"},
    {"name": "Christmas",    "date": "2025-12-25"},
    {"name": "New Year",     "date": "2026-01-01"},
    {"name": "Navratri",     "date": "2025-10-02"},
    {"name": "Dussehra",     "date": "2025-10-10"},
    {"name": "Janmashtami",  "date": "2025-08-16"},
    {"name": "Ganesh Chaturthi", "date": "2025-09-06"},
    {"name": "Independence Day", "date": "2025-08-15"},
]

SAMPLE_CUSTOMERS = [
    {
        "customer_id": "C001",
        "active": True,
        "company_name": "Sharma Traders",
        "owner_name": "Ramesh Sharma",
        "whatsapp": "+919876543210",
        "address": "12, MG Road, Sagar, MP",
        "logo_url": "",
        "last_used_photo": None,
    },
    {
        "customer_id": "C002",
        "active": True,
        "company_name": "Patel Enterprises",
        "owner_name": "Suresh Patel",
        "whatsapp": "+918765432109",
        "address": "45, Station Road, Bhopal, MP",
        "logo_url": "",
        "last_used_photo": None,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULER JOB
# ─────────────────────────────────────────────────────────────────────────────

def get_tomorrow_festivals() -> list[dict]:
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return [f for f in SAMPLE_FESTIVALS if f["date"] == tomorrow]


def daily_job() -> None:
    """
    Daily cron job: generate + save videos for all festivals tomorrow.
    In production, replace SAMPLE_CUSTOMERS / SAMPLE_FESTIVALS with your
    database queries (see database.py / scheduler.py).
    """
    log.info("=== Festival Video Job Started ===")
    festivals = get_tomorrow_festivals()

    if not festivals:
        log.info("No festivals tomorrow. Skipping.")
        return

    log.info("Festivals tomorrow: %s", [f["name"] for f in festivals])
    active = [c for c in SAMPLE_CUSTOMERS if c.get("active")]

    for festival in festivals:
        results = batch_generate(active, festival["name"])
        for cid, path in results.items():
            if path:
                log.info("✅  %s → %s", cid, path)
            else:
                log.warning("❌  Failed for customer %s", cid)

    log.info("=== Festival Video Job Complete ===")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def start_scheduler() -> None:
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(daily_job, "cron", hour=0, minute=0, id="festival_video_job")
    log.info("Scheduler started – daily at midnight IST. Press Ctrl+C to stop.")

    # Run immediately on startup for testing
    daily_job()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")


if __name__ == "__main__":
    start_scheduler()
