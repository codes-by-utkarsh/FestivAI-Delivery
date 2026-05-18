import os
import uuid
from datetime import datetime
import dotenv
import sys

# Allow running from scripts/ or project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, get_users_sheet
from auth import hash_password

dotenv.load_dotenv()


def create_initial_admin(
    name: str = "Super Admin",
    email: str = "admin@festivai.com",
    password: str = "Admin@1234"
):
    sheet = init_db()
    if not sheet:
        print("❌ Database not initialized. Check your credentials.json and .env file.")
        return

    users_ws = get_users_sheet(sheet)
    users = users_ws.get_all_records()

    if any(u.get("email") == email for u in users):
        print(f"⚠️  Admin user '{email}' already exists in the database.")
        return

    # Check admin cap
    admin_count = sum(1 for u in users if u.get("role") == "Admin")
    if admin_count >= 5:
        print("❌ Maximum Admin limit of 5 has been reached.")
        return

    user_id = str(uuid.uuid4())
    pw_hash = hash_password(password)

    users_ws.append_row([
        user_id, name, email, pw_hash, "Admin", "System", datetime.utcnow().isoformat()
    ])

    print("=" * 50)
    print("✅ Admin user created successfully!")
    print(f"   Name    : {name}")
    print(f"   Email   : {email}")
    print(f"   Password: {password}")
    print(f"   User ID : {user_id}")
    print("=" * 50)
    print("⚠️  Please change the password after first login!")


if __name__ == "__main__":
    # Allow custom args: python create_admin.py [name] [email] [password]
    args = sys.argv[1:]
    kwargs = {}
    if len(args) >= 1:
        kwargs["name"] = args[0]
    if len(args) >= 2:
        kwargs["email"] = args[1]
    if len(args) >= 3:
        kwargs["password"] = args[2]
    create_initial_admin(**kwargs)
