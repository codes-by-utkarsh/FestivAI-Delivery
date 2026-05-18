# Production API & Integration Guide

This document outlines the architectural specifications and step-by-step instructions to transition the **SimplyPromised Festival Video Platform** from local development/MVP to a fully secured, production-grade cloud deployment.

---

## 🏗️ 1. Architecture & Security Hardening

### CORS Hardening (`main.py`)
In local development, CORS is configured to `allow_origins=["*"]`. Before deploying to production (e.g., AWS, Render, Railway), you must restrict this to your exact frontend domain:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dashboard.simplypromised.com"], # Replace with production domain
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### Environment Security
Ensure your production environment variables (`.env`) are securely injected via your hosting provider's secret manager (e.g., AWS Secrets Manager, Render Environment Secrets). **Never commit `.env` or `credentials.json` to GitHub.**

---

## 🔌 2. Transitioning 3rd-Party APIs to Production

### A. Google Sheets Database (`database.py`)
1. **Production Service Account**: Ensure the `credentials.json` attached to your production server belongs to a dedicated Google Cloud Service Account with domain-wide or strict sheet-level permissions.
2. **Rate Limiting**: `gspread` makes API calls per read/write. If scaling past 500+ active companies, implement a Redis caching layer for `get_all_records()` in `database.py`.

### B. Google Drive API (Replacing Local Uploads)
To persist company logos and photos in the cloud instead of the local `uploads/` folder:
1. Enable the **Google Drive API** in your Google Cloud Console.
2. Share a dedicated Google Drive folder with your Service Account email.
3. Update `create_customer` in `main.py` to upload files via the Google Drive API:
```python
# Example snippet for Google Drive API upload replacement
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

def upload_to_drive(file_path, file_name, folder_id):
    creds = Credentials.from_service_account_file('credentials.json')
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    media = MediaFileUpload(file_path, mimetype='image/jpeg')
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('webViewLink') # Store this link in Google Sheets
```

### C. Meta WhatsApp Cloud API
To move out of Meta's Sandbox mode and send messages to any customer without whitelisting:
1. Go to **Meta Business Suite** -> **Business Settings** -> **WhatsApp Accounts**.
2. Connect a dedicated, permanent business phone number.
3. Complete **Business Verification** (uploading business license/tax ID).
4. Create a **System User** in Business Settings, assign it Admin access to your WhatsApp app, and generate a **Permanent Access Token** (replace `WHATSAPP_TOKEN` in `.env`).

---

## 💻 3. Frontend Integration: Admin On-Demand WhatsApp Dispatch

We have exposed a production-ready endpoint in `main.py` (`POST /send-whatsapp`) that allows Admins to bypass the midnight cron job and instantly generate and deliver a video to any customer directly from the React UI.

### API Specification
*   **Endpoint**: `POST /send-whatsapp`
*   **Headers**: `Authorization: Bearer <JWT_TOKEN>`
*   **Payload**:
```json
{
  "customer_id": "uuid-of-the-customer",
  "festival_name": "Diwali",
  "template_name": "festival_video"
}
```

### React Frontend Implementation (`App.jsx`)
To wire this up to a "Send Now" button inside your Companies or Videos tab, add the following handler to your React code:

```javascript
// Add this function inside App.jsx
const handleSendDirectWhatsApp = async (customerId, festivalName) => {
  try {
    const token = localStorage.getItem('token');
    alert(`Generating video for ${festivalName} and dispatching to WhatsApp... This may take 30-60 seconds.`);
    
    const res = await fetch('https://api.simplypromised.com/send-whatsapp', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        customer_id: customerId,
        festival_name: festivalName,
        template_name: "festival_video" // Make sure this template is approved in Meta
      })
    });

    if (res.ok) {
      const data = await res.json();
      alert('✅ Video successfully generated and delivered to the customer!');
    } else {
      const err = await res.json();
      alert(`❌ Failed to send WhatsApp: ${err.detail}`);
    }
  } catch (error) {
    alert('❌ Network error while connecting to the video engine server.');
  }
};
```

### UI Button Example
Attach this handler to a button inside your company card or festival list:
```jsx
<button 
  onClick={() => handleSendDirectWhatsApp(company.customer_id, "Eid-ul-Adha")}
  className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-2 shadow"
>
  <i className="fa-brands fa-whatsapp text-sm"></i> Instant Dispatch
</button>
```

---

## 🚀 4. Deployment Checklist & Cloud Hosting Guide

We have pre-configured the repository for automated deployment on **Vercel** (Frontend) and **Render** (Backend).

### A. Backend Deployment (Render)
1. [ ] **Blueprint Setup**: Log into Render, go to **Blueprints**, and connect your GitHub repository. Render will automatically read `render.yaml` and configure the FastAPI web service.
2. [ ] **Environment Variables**: In the Render dashboard, go to your Web Service -> **Environment** and add:
   * `JWT_SECRET`
   * `SPREADSHEET_ID`
   * `WHATSAPP_TOKEN`
   * `WHATSAPP_API_URL`
3. [ ] **Service Account Key**: Upload `credentials.json` via Render Secret Files (mounting it to the root) or store its contents in an environment variable if adapted in `database.py`.
4. [ ] **FFmpeg & Binaries**: Our `requirements.txt` includes `imageio-ffmpeg` to ensure standalone FFmpeg binaries are automatically provided in Render's Python 3 environment without requiring system-level apt packages. Note: `video_engine.py` uses pure PIL (`ImageDraw`, `ImageFont`) for text rendering, avoiding ImageMagick dependencies entirely!

### B. Frontend Deployment (Vercel)
1. [ ] **Project Setup**: Log into Vercel, click **Add New Project**, and import your GitHub repository.
2. [ ] **Root Directory**: Configure the Root Directory to `frontend_app` in the Vercel project import settings (recommended). If left at the repository root, our root `vercel.json` will automatically direct Vercel to build `frontend_app` and serve `frontend_app/dist`.
3. [ ] **Environment Variable**: Add `VITE_API_URL` in Vercel's Environment Variables setting, pointing to your live Render backend URL (e.g., `https://festivai-delivery-backend.onrender.com`).
4. [ ] **SPA Routing**: Vercel will automatically apply `vercel.json` to rewrite all client-side navigation to `/index.html`, preventing 404 errors on direct page loads.

### C. Meta & Database Finalization
1. [ ] **Database**: Verify Google Sheet sharing permissions with your Google Cloud Service Account email address.
2. [ ] **Meta Dashboard**: Submit your WhatsApp video template (e.g., `hello_world` or `festival_video`) for review and ensure your permanent token is active.
