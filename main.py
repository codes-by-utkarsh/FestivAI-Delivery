import uuid
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from auth import hash_password, verify_password, create_access_token, require_role
from database import init_db, get_users_sheet, get_customers_sheet
from scheduler import start_scheduler
from datetime import datetime
import dotenv
import os
from fastapi import UploadFile, File, Form
from typing import List, Optional, Union, Any
import logging
import cloud_storage

dotenv.load_dotenv(override=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="FestivAI Delivery API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files as static assets so frontend can preview logos/photos
uploads_dir = "uploads"
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class LoginData(BaseModel):
    email: str
    password: str

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str

class RegisterData(BaseModel):
    name: str
    email: str
    password: str
    role: str

class SendWhatsAppRequest(BaseModel):
    customer_id: Union[str, int]
    festival_name: str
    template_name: str = "hello_world"

class GenerateVideoRequest(BaseModel):
    customer_id: Union[str, int]
    festival_name: str

class BulkGenerateRequest(BaseModel):
    customer_ids: List[Union[str, int]]
    festival_name: str
    send_whatsapp: bool = False
    template_name: str = "hello_world"

class AddFestivalRequest(BaseModel):
    name: str
    date: str          # YYYY-MM-DD
    type: str = "Custom"


# ─── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup_event():
    init_db()
    start_scheduler()


# ─── Auth Endpoints ───────────────────────────────────────────────────────────

@app.post("/login")
def login(data: LoginData):
    sheet = init_db()
    if not sheet:
        raise HTTPException(status_code=500, detail="Database connection failed. Check server credentials.")

    users_ws = get_users_sheet(sheet)
    users = users_ws.get_all_records()

    for u in users:
        if u.get("email") == data.email:
            if verify_password(data.password, u.get("password_hash", "")):
                token = create_access_token({
                    "sub": u.get("email"),
                    "role": u.get("role"),
                    "user_id": u.get("user_id")
                })
                return {
                    "access_token": token,
                    "token_type": "bearer",
                    "role": u.get("role"),
                    "name": u.get("name"),
                    "email": u.get("email"),
                    "user_id": u.get("user_id")
                }
            else:
                raise HTTPException(status_code=401, detail="Incorrect password")

    raise HTTPException(status_code=401, detail="No account found with that email address")


@app.post("/register")
def register(user: RegisterData):
    if user.role == "Admin":
        raise HTTPException(
            status_code=403,
            detail="Admin accounts cannot be self-registered. Contact your system administrator."
        )

    sheet = init_db()
    if not sheet:
        raise HTTPException(status_code=500, detail="Database connection failed.")

    users_ws = get_users_sheet(sheet)
    users = users_ws.get_all_records()

    if any(u.get("email") == user.email for u in users):
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    agent_count = sum(1 for u in users if u.get("role") == "Agent")

    if user.role == "Agent" and agent_count >= 30:
        raise HTTPException(status_code=400, detail="Maximum Agent limit of 30 has been reached.")

    user_id = str(uuid.uuid4())
    pw_hash = hash_password(user.password)

    users_ws.append_row([
        user_id, user.name, user.email, pw_hash, user.role, "Self-Registered", datetime.utcnow().isoformat()
    ])

    token = create_access_token({"sub": user.email, "role": user.role, "user_id": user_id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "name": user.name,
        "email": user.email,
        "user_id": user_id
    }


# ─── User Management ──────────────────────────────────────────────────────────

@app.post("/users", dependencies=[Depends(require_role(["Admin"]))])
def create_user(user: UserCreate, current_user: dict = Depends(require_role(["Admin"]))):
    sheet = init_db()
    users_ws = get_users_sheet(sheet)
    users = users_ws.get_all_records()

    if any(u.get("email") == user.email for u in users):
        raise HTTPException(status_code=400, detail="Email already registered.")

    admin_count = sum(1 for u in users if u.get("role") == "Admin")
    agent_count = sum(1 for u in users if u.get("role") == "Agent")

    if user.role == "Admin" and admin_count >= 5:
        raise HTTPException(status_code=400, detail="Maximum Admin limit of 5 has been reached.")
    if user.role == "Agent" and agent_count >= 30:
        raise HTTPException(status_code=400, detail="Maximum Agent limit of 30 has been reached.")

    user_id = str(uuid.uuid4())
    pw_hash = hash_password(user.password)

    users_ws.append_row([
        user_id, user.name, user.email, pw_hash, user.role,
        current_user.get("user_id"), datetime.utcnow().isoformat()
    ])

    return {"message": "User created successfully", "user_id": user_id}


@app.get("/users-list", dependencies=[Depends(require_role(["Admin"]))])
def get_users_list(current_user: dict = Depends(require_role(["Admin"]))):
    sheet = init_db()
    users_ws = get_users_sheet(sheet)
    users = users_ws.get_all_records()
    return {
        "users": [
            {
                "user_id": u.get("user_id"),
                "name": u.get("name"),
                "email": u.get("email"),
                "role": u.get("role"),
                "created_at": u.get("created_at")
            }
            for u in users
        ]
    }


@app.get("/me", dependencies=[Depends(require_role(["Admin", "Agent"]))])
def get_me(current_user: dict = Depends(require_role(["Admin", "Agent"]))):
    sheet = init_db()
    users_ws = get_users_sheet(sheet)
    users = users_ws.get_all_records()
    for u in users:
        if str(u.get("user_id")) == str(current_user.get("user_id")):
            return {
                "name": u.get("name"),
                "email": u.get("email"),
                "role": u.get("role"),
                "user_id": u.get("user_id")
            }
    return current_user


# ─── Customer Management ──────────────────────────────────────────────────────

@app.get("/customers", dependencies=[Depends(require_role(["Admin", "Agent"]))])
def get_customers(current_user: dict = Depends(require_role(["Admin", "Agent"]))):
    sheet = init_db()
    customers_ws = get_customers_sheet(sheet)
    raw_customers = customers_ws.get_all_records()

    # Filter out empty/blank rows from Google Sheets
    customers = [c for c in raw_customers if c.get("customer_id")]
    logger.info(f"[get_customers] Called by user_id: '{current_user.get('user_id')}', role: '{current_user.get('role')}'. Total raw customers: {len(raw_customers)}")
    if raw_customers:
        logger.info(f"[get_customers] First raw customer keys: {list(raw_customers[0].keys())}")
        logger.info(f"[get_customers] First raw customer data: {raw_customers[0]}")

    if current_user.get("role") == "Agent":
        agent_id = str(current_user.get("user_id"))
        filtered_customers = []
        for c in customers:
            c_agent = str(c.get("agent_id"))
            logger.info(f"[get_customers] Comparing customer '{c.get('company_name')}' agent_id '{c_agent}' == current user '{agent_id}'")
            if c_agent == agent_id:
                filtered_customers.append(c)
        customers = filtered_customers
        logger.info(f"[get_customers] Agent filtered customers count: {len(customers)}")

    # Compute active status dynamically based on subscription_end
    today = datetime.utcnow().strftime("%Y-%m-%d")
    for c in customers:
        sub_end = str(c.get("subscription_end", ""))
        c["is_active"] = bool(sub_end and today <= sub_end)

    return {"customers": customers}


@app.post("/customers", dependencies=[Depends(require_role(["Admin", "Agent"]))])
def create_customer(
    company_name: str = Form(...),
    owner_name: str = Form(...),
    whatsapp: str = Form(...),
    address: str = Form(...),
    subscription_end: str = Form(...),
    logo: UploadFile = File(...),
    photos: List[UploadFile] = File(...),
    current_user: dict = Depends(require_role(["Admin", "Agent"]))
):
    if len(photos) < 8 or len(photos) > 10:
        raise HTTPException(status_code=400, detail="You must provide between 8 and 10 company photos.")

    # Validate WhatsApp number format
    wa_number = whatsapp.strip().replace("+", "").replace(" ", "").replace("-", "")
    if not wa_number.isdigit() or len(wa_number) < 10:
        raise HTTPException(status_code=400, detail="Invalid WhatsApp number. Use format: 919876543210")

    # Save logo
    logo_ext = os.path.splitext(logo.filename)[1] if logo.filename else ".jpg"
    logo_filename = f"logo_{uuid.uuid4().hex}{logo_ext}"
    logo_content = logo.file.read()
    logo_url = cloud_storage.upload_image(logo_content, logo_filename, logo.content_type or "image/jpeg")

    # Save photos
    photo_urls = [""] * 10
    for i, photo in enumerate(photos):
        if i >= 10:
            break
        p_ext = os.path.splitext(photo.filename)[1] if photo.filename else ".jpg"
        p_filename = f"photo_{uuid.uuid4().hex}{p_ext}"
        photo_content = photo.file.read()
        p_url = cloud_storage.upload_image(photo_content, p_filename, photo.content_type or "image/jpeg")
        photo_urls[i] = p_url

    sheet = init_db()
    customers_ws = get_customers_sheet(sheet)
    customer_id = str(uuid.uuid4())

    row = [
        customer_id,
        current_user.get("user_id"),
        company_name,
        owner_name,
        wa_number,
        address,
        logo_url,
        *photo_urls,
        subscription_end,
        0,
        "Active"
    ]
    logger.info(f"[create_customer] Appending customer '{company_name}' with agent_id: '{current_user.get('user_id')}'")
    customers_ws.append_row(row)

    logger.info(f"Onboarded new customer: {company_name} (ID: {customer_id})")
    return {"message": "Company onboarded successfully!", "customer_id": customer_id}


# ─── Festival Calendar ────────────────────────────────────────────────────────

@app.get("/festivals", dependencies=[Depends(require_role(["Admin", "Agent"]))])
def get_festivals(current_user: dict = Depends(require_role(["Admin", "Agent"]))):
    sheet = init_db()
    festivals_ws = sheet.worksheet("Festivals")
    festivals = festivals_ws.get_all_records()
    festivals.sort(key=lambda x: str(x.get("date") or ""))
    return {"festivals": festivals}


@app.post("/festivals", dependencies=[Depends(require_role(["Admin", "Agent"]))])
def add_festival(
    req: AddFestivalRequest,
    current_user: dict = Depends(require_role(["Admin", "Agent"]))
):
    """Add a custom festival to the calendar."""
    sheet = init_db()
    if not sheet:
        raise HTTPException(status_code=500, detail="Database connection failed.")
    festivals_ws = sheet.worksheet("Festivals")
    festival_id = str(uuid.uuid4())
    festivals_ws.append_row([festival_id, req.date, req.name, req.type])
    return {"message": "Festival added.", "festival_id": festival_id}


# ─── Video Generation ─────────────────────────────────────────────────────────

@app.post("/generate-video", dependencies=[Depends(require_role(["Admin", "Agent"]))])
def generate_video_endpoint(
    req: GenerateVideoRequest,
    current_user: dict = Depends(require_role(["Admin", "Agent"]))
):
    """Generate a festival video for a customer (without sending via WhatsApp)."""
    sheet = init_db()
    if not sheet:
        raise HTTPException(status_code=500, detail="Database connection failed.")

    customers_ws = get_customers_sheet(sheet)
    customers = customers_ws.get_all_records()
    customer = next((c for c in customers if str(c.get("customer_id")) == req.customer_id), None)

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    # Agents can only generate videos for their own customers
    if current_user.get("role") == "Agent" and str(customer.get("agent_id")) != str(current_user.get("user_id")):
        raise HTTPException(status_code=403, detail="You can only generate videos for your own customers.")

    from video_engine import generate_video, get_next_photo_index

    last_used_photo = int(customer.get("last_used_photo") or 0)
    next_photo_idx = get_next_photo_index(last_used_photo)

    video_path = generate_video(customer, req.festival_name, next_photo_idx)
    if not video_path:
        raise HTTPException(status_code=500, detail="Video generation failed. Check server logs.")

    # Update last used photo index
    for idx, c in enumerate(customers):
        if str(c.get("customer_id")) == req.customer_id:
            customers_ws.update_cell(idx + 2, 19, next_photo_idx)
            break

    return {
        "message": "Video generated successfully.",
        "video_path": video_path,
        "photo_used": next_photo_idx
    }


# ─── WhatsApp Dispatch ────────────────────────────────────────────────────────

@app.post("/send-whatsapp", dependencies=[Depends(require_role(["Admin", "Agent"]))])
def send_whatsapp_direct(
    req: SendWhatsAppRequest,
    current_user: dict = Depends(require_role(["Admin", "Agent"]))
):
    """Generate a video and send it via WhatsApp to the customer."""
    sheet = init_db()
    if not sheet:
        raise HTTPException(status_code=500, detail="Database connection failed.")

    customers_ws = get_customers_sheet(sheet)
    customers = customers_ws.get_all_records()

    customer = next((c for c in customers if str(c.get("customer_id")) == req.customer_id), None)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    # Agents can only dispatch for their own customers
    if current_user.get("role") == "Agent" and str(customer.get("agent_id")) != str(current_user.get("user_id")):
        raise HTTPException(status_code=403, detail="You can only dispatch videos for your own customers.")

    # Check subscription is active
    today = datetime.utcnow().strftime("%Y-%m-%d")
    sub_end = str(customer.get("subscription_end", ""))
    if not sub_end or today > sub_end:
        raise HTTPException(status_code=400, detail=f"Customer subscription has expired (ended: {sub_end or 'N/A'}).")

    from video_engine import generate_video, get_next_photo_index
    from scheduler import upload_video_to_meta, send_whatsapp_video

    last_used_photo = int(customer.get("last_used_photo") or 0)
    next_photo_idx = get_next_photo_index(last_used_photo)

    # Generate video
    video_path = generate_video(customer, req.festival_name, next_photo_idx)
    if not video_path:
        raise HTTPException(status_code=500, detail="Video generation failed. Check that customer photos are accessible.")

    # Upload to Meta Cloud API
    media_id = upload_video_to_meta(video_path)
    if not media_id:
        if os.path.exists(video_path):
            os.remove(video_path)
        raise HTTPException(
            status_code=502,
            detail="Failed to upload video to Meta WhatsApp Cloud API. Verify your WHATSAPP_TOKEN and API URL."
        )

    # Send via WhatsApp
    success = send_whatsapp_video(customer.get("whatsapp"), media_id, template_name=req.template_name)
    if os.path.exists(video_path):
        os.remove(video_path)

    # Log the attempt regardless of success/failure
    logs_ws = sheet.worksheet("Video Logs")
    festivals_ws = sheet.worksheet("Festivals")
    festivals = festivals_ws.get_all_records()
    festival_match = next((f for f in festivals if f.get("name") == req.festival_name), None)
    festival_id = festival_match.get("festival_id") if festival_match else "manual"

    log_id = str(uuid.uuid4())
    logs_ws.append_row([
        log_id,
        req.customer_id,
        festival_id,
        media_id or "Upload Failed",
        "Sent" if success else "Failed",
        datetime.utcnow().isoformat()
    ])

    # Update last used photo index
    for idx, c in enumerate(customers):
        if str(c.get("customer_id")) == req.customer_id:
            customers_ws.update_cell(idx + 2, 19, next_photo_idx)
            break

    if not success:
        raise HTTPException(
            status_code=502,
            detail="Video uploaded to Meta but WhatsApp message delivery failed. Check your template name and recipient number."
        )

    return {
        "message": "Festival video generated and delivered via WhatsApp successfully!",
        "media_id": media_id,
        "photo_used": next_photo_idx,
        "sent_to": customer.get("whatsapp")
    }


# ─── Bulk Video Generation ────────────────────────────────────────────────────

@app.post("/bulk-generate-videos", dependencies=[Depends(require_role(["Admin", "Agent"]))])
def bulk_generate_videos(
    req: BulkGenerateRequest,
    current_user: dict = Depends(require_role(["Admin", "Agent"]))
):
    """
    Generate festival videos for multiple selected companies.
    Optionally send via WhatsApp immediately after generation.
    Returns per-company result summary.
    """
    sheet = init_db()
    if not sheet:
        raise HTTPException(status_code=500, detail="Database connection failed.")

    customers_ws = get_customers_sheet(sheet)
    all_customers = customers_ws.get_all_records()
    logs_ws = sheet.worksheet("Video Logs")
    festivals_ws = sheet.worksheet("Festivals")
    festivals = festivals_ws.get_all_records()
    festival_match = next((f for f in festivals if f.get("name") == req.festival_name), None)
    festival_id = festival_match.get("festival_id") if festival_match else "manual"

    from video_engine import generate_video, get_next_photo_index
    from scheduler import upload_video_to_meta, send_whatsapp_video

    results = []
    today = datetime.utcnow().strftime("%Y-%m-%d")

    for cid in req.customer_ids:
        customer = next(
            (c for c in all_customers if str(c.get("customer_id")) == cid), None
        )
        if not customer:
            results.append({"customer_id": cid, "status": "error", "detail": "Not found"})
            continue

        # RBAC: Agents can only process their own customers
        if current_user.get("role") == "Agent" and \
           str(customer.get("agent_id")) != str(current_user.get("user_id")):
            results.append({"customer_id": cid, "status": "error",
                            "detail": "Forbidden – not your customer"})
            continue

        # Subscription check
        sub_end = str(customer.get("subscription_end", ""))
        if not sub_end or today > sub_end:
            results.append({"customer_id": cid, "company_name": customer.get("company_name"),
                            "status": "skipped", "detail": "Subscription expired"})
            continue

        last_used  = int(customer.get("last_used_photo") or 0)
        next_idx   = get_next_photo_index(last_used)
        video_path = generate_video(customer, req.festival_name, next_idx)

        if not video_path:
            results.append({"customer_id": cid, "company_name": customer.get("company_name"),
                            "status": "error", "detail": "Video generation failed"})
            continue

        # Update photo index in DB
        for idx, c in enumerate(all_customers):
            if str(c.get("customer_id")) == cid:
                customers_ws.update_cell(idx + 2, 19, next_idx)
                break

        if not req.send_whatsapp:
            results.append({"customer_id": cid, "company_name": customer.get("company_name"),
                            "status": "generated", "video_path": video_path})
            continue

        # Upload + send WhatsApp
        media_id = upload_video_to_meta(video_path)
        if os.path.exists(video_path):
            os.remove(video_path)

        wa_success = False
        if media_id:
            wa_success = send_whatsapp_video(
                customer.get("whatsapp"), media_id, template_name=req.template_name
            )

        log_id = str(uuid.uuid4())
        logs_ws.append_row([
            log_id, cid, festival_id,
            media_id or "Upload Failed",
            "Sent" if wa_success else "Failed",
            datetime.utcnow().isoformat()
        ])

        results.append({
            "customer_id": cid,
            "company_name": customer.get("company_name"),
            "whatsapp": customer.get("whatsapp"),
            "status": "sent" if wa_success else "upload_failed",
            "media_id": media_id,
        })

    sent   = sum(1 for r in results if r.get("status") == "sent")
    gen    = sum(1 for r in results if r.get("status") == "generated")
    errors = sum(1 for r in results if r.get("status") in ("error", "upload_failed"))

    return {
        "festival": req.festival_name,
        "total": len(req.customer_ids),
        "sent": sent,
        "generated": gen,
        "errors": errors,
        "results": results,
    }


# ─── Dashboard Stats ──────────────────────────────────────────────────────────

@app.get("/stats", dependencies=[Depends(require_role(["Admin", "Agent"]))])
def get_stats(current_user: dict = Depends(require_role(["Admin", "Agent"]))):
    sheet = init_db()
    customers_ws = get_customers_sheet(sheet)
    users_ws = get_users_sheet(sheet)
    logs_ws = sheet.worksheet("Video Logs")

    customers = customers_ws.get_all_records()
    users = users_ws.get_all_records()
    logs = logs_ws.get_all_records()

    today = datetime.utcnow().strftime("%Y-%m-%d")

    if current_user.get("role") == "Agent":
        my_customer_ids = {str(c.get("customer_id")) for c in customers if str(c.get("agent_id")) == str(current_user.get("user_id"))}
        customers = [c for c in customers if str(c.get("customer_id")) in my_customer_ids]
        logs = [l for l in logs if str(l.get("customer_id")) in my_customer_ids]

    active_customers = sum(
        1 for c in customers
        if c.get("subscription_end") and today <= str(c.get("subscription_end"))
    )

    return {
        "total_companies": len(customers),
        "active_companies": active_customers,
        "active_agents": len([u for u in users if u.get("role") == "Agent"]),
        "videos_generated": len(logs),
        "whatsapp_sent": len([l for l in logs if l.get("sent_status") == "Sent"])
    }


# ─── Delivery Logs ────────────────────────────────────────────────────────────

@app.get("/logs", dependencies=[Depends(require_role(["Admin", "Agent"]))])
def get_logs(current_user: dict = Depends(require_role(["Admin", "Agent"]))):
    sheet = init_db()
    logs_ws = sheet.worksheet("Video Logs")
    customers_ws = get_customers_sheet(sheet)
    festivals_ws = sheet.worksheet("Festivals")

    logs = logs_ws.get_all_records()
    customers = {str(c.get("customer_id")): c for c in customers_ws.get_all_records()}
    festivals = {str(f.get("festival_id")): f.get("name") for f in festivals_ws.get_all_records()}

    result = []
    for l in logs:
        cid = str(l.get("customer_id"))
        fid = str(l.get("festival_id"))
        cust = customers.get(cid, {})

        if current_user.get("role") == "Agent" and str(cust.get("agent_id")) != str(current_user.get("user_id")):
            continue

        result.append({
            "log_id": l.get("log_id"),
            "company_name": cust.get("company_name", "Unknown Company"),
            "whatsapp": cust.get("whatsapp", "N/A"),
            "festival_name": festivals.get(fid, l.get("festival_id", "Festival")),
            "sent_status": l.get("sent_status"),
            "sent_at": l.get("sent_at"),
            "media_id": l.get("video_url", "")
        })

    # Sort by most recent first
    result.sort(key=lambda x: str(x.get("sent_at") or ""), reverse=True)
    return {"logs": result}


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "FestivAI Delivery API", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
