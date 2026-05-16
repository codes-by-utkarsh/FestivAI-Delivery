import os
import uuid
from datetime import datetime
import dotenv
from database import init_db, get_users_sheet
from auth import hash_password

dotenv.load_dotenv()

def create_initial_admin():
    sheet = init_db()
    if not sheet:
        print("Database not initialized. Check your credentials.")
        return

    users_ws = get_users_sheet(sheet)
    users = users_ws.get_all_records()

    admin_email = "admin@example.com"
    admin_password = "adminpassword123"

    if any(u.get("email") == admin_email for u in users):
        print(f"Admin user {admin_email} already exists.")
        return

    user_id = str(uuid.uuid4())
    pw_hash = hash_password(admin_password)

    users_ws.append_row([
        user_id, "Super Admin", admin_email, pw_hash, "Admin", "System", datetime.utcnow().isoformat()
    ])

    print("========================================")
    print("Initial Admin created successfully!")
    print(f"Email: {admin_email}")
    print(f"Password: {admin_password}")
    print("========================================")

if __name__ == "__main__":
    create_initial_admin()
