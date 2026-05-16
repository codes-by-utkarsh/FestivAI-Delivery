import uuid
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from auth import hash_password, verify_password, create_access_token, require_role
from database import init_db, get_users_sheet, get_customers_sheet
from scheduler import start_scheduler
from datetime import datetime
import dotenv
import os
from fastapi import UploadFile, File, Form
from typing import List

dotenv.load_dotenv()

app = FastAPI(title="Festival Video Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginData(BaseModel):
    email: str
    password: str

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str

class SendWhatsAppRequest(BaseModel):
    customer_id: str
    festival_name: str
    template_name: str = "hello_world"

@app.on_event("startup")
def startup_event():
    init_db()
    start_scheduler()

@app.post("/login")
def login(data: LoginData):
    sheet = init_db()
    if not sheet:
        raise HTTPException(status_code=500, detail="DB Error")

    users_ws = get_users_sheet(sheet)
    users = users_ws.get_all_records()
    
    for u in users:
        if u.get("email") == data.email:
            if verify_password(data.password, u.get("password_hash")):
                token = create_access_token({"sub": u.get("email"), "role": u.get("role"), "user_id": u.get("user_id")})
                return {"access_token": token, "token_type": "bearer", "role": u.get("role")}
            else:
                raise HTTPException(status_code=401, detail="Incorrect password")
                
    raise HTTPException(status_code=401, detail="User not found")

@app.post("/users", dependencies=[Depends(require_role(["Admin"]))])
def create_user(user: UserCreate, current_user: dict = Depends(require_role(["Admin"]))):
    sheet = init_db()
    users_ws = get_users_sheet(sheet)
    
    users = users_ws.get_all_records()
    if any(u.get("email") == user.email for u in users):
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # Check max limits
    admin_count = sum(1 for u in users if u.get("role") == "Admin")
    agent_count = sum(1 for u in users if u.get("role") == "Agent")
    
    if user.role == "Admin" and admin_count >= 5:
        raise HTTPException(status_code=400, detail="Maximum Admin limit reached (5)")
    if user.role == "Agent" and agent_count >= 30:
        raise HTTPException(status_code=400, detail="Maximum Agent limit reached (30)")
        
    user_id = str(uuid.uuid4())
    pw_hash = hash_password(user.password)
    
    users_ws.append_row([
        user_id, user.name, user.email, pw_hash, user.role, current_user.get("user_id"), datetime.utcnow().isoformat()
    ])
    
    return {"message": "User created successfully", "user_id": user_id}

@app.get("/customers", dependencies=[Depends(require_role(["Admin", "Agent"]))])
def get_customers(current_user: dict = Depends(require_role(["Admin", "Agent"]))):
    sheet = init_db()
    customers_ws = get_customers_sheet(sheet)
    customers = customers_ws.get_all_records()
    
    if current_user.get("role") == "Agent":
        customers = [c for c in customers if str(c.get("agent_id")) == str(current_user.get("user_id"))]
        
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
        raise HTTPException(status_code=400, detail="Must provide between 8 and 10 photos.")
    
    # Process uploads to local (simulating Google Drive for MVP)
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    logo_path = os.path.join(upload_dir, f"{uuid.uuid4()}_{logo.filename}")
    with open(logo_path, "wb") as f:
        f.write(logo.file.read())
        
    photo_urls = [""] * 10
    for i, photo in enumerate(photos):
        if i >= 10: break
        p_path = os.path.join(upload_dir, f"{uuid.uuid4()}_{photo.filename}")
        with open(p_path, "wb") as f:
            f.write(photo.file.read())
        # To simulate a public URL, we save the relative path or an absolute path
        # In a real app, you would upload to Drive and return the link here.
        photo_urls[i] = os.path.abspath(p_path)
        
    sheet = init_db()
    customers_ws = get_customers_sheet(sheet)
    customer_id = str(uuid.uuid4())
    
    # Map back to 10 photo cols + others
    # logo_url, photo1-photo10, subscription_end, last_used_photo, status
    row = [
        customer_id, current_user.get("user_id"), company_name, owner_name, whatsapp,
        address, os.path.abspath(logo_path), *photo_urls, subscription_end, 0, "Active"
    ]
    customers_ws.append_row(row)
    
    return {"message": "Customer onboarded successfully", "customer_id": customer_id}

@app.post("/send-whatsapp", dependencies=[Depends(require_role(["Admin"]))])
def send_whatsapp_direct(req: SendWhatsAppRequest, current_user: dict = Depends(require_role(["Admin"]))):
    sheet = init_db()
    if not sheet:
        raise HTTPException(status_code=500, detail="DB Error")
        
    customers_ws = get_customers_sheet(sheet)
    customers = customers_ws.get_all_records()
    
    customer = next((c for c in customers if str(c.get("customer_id")) == req.customer_id), None)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    # Generate video
    from video_engine import generate_video, get_next_photo_index
    from scheduler import upload_video_to_meta, send_whatsapp_video
    
    last_used_photo = int(customer.get("last_used_photo") or 0)
    next_photo_idx = get_next_photo_index(last_used_photo)
    
    video_path = generate_video(customer, req.festival_name, next_photo_idx)
    if not video_path:
        raise HTTPException(status_code=500, detail="Failed to generate video")
        
    # Upload to Meta
    media_id = upload_video_to_meta(video_path)
    if not media_id:
        if os.path.exists(video_path): os.remove(video_path)
        raise HTTPException(status_code=500, detail="Failed to upload video to Meta Cloud")
        
    # Send WhatsApp
    success = send_whatsapp_video(customer.get("whatsapp"), media_id, template_name=req.template_name)
    if os.path.exists(video_path): os.remove(video_path)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to dispatch WhatsApp message via Meta API")
        
    # Update last used photo in sheet
    for idx, c in enumerate(customers):
        if str(c.get("customer_id")) == req.customer_id:
            customers_ws.update_cell(idx + 2, 19, next_photo_idx)
            break
            
    return {"message": "WhatsApp video generated and dispatched successfully", "media_id": media_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
