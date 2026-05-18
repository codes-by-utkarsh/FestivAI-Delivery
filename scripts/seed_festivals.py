import os
import uuid
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dotenv
dotenv.load_dotenv()

from database import init_db, get_festivals_sheet, INDIAN_FESTIVALS_2025_2026


def seed_festivals(force: bool = False):
    sheet = init_db()
    if not sheet:
        print("❌ Database could not be initialized. Check credentials.json and .env.")
        return

    festivals_ws = get_festivals_sheet(sheet)
    existing = festivals_ws.get_all_records()

    if len(existing) > 0 and not force:
        print(f"⚠️  Festivals already seeded ({len(existing)} records). Use --force to re-seed.")
        return

    if force and len(existing) > 0:
        print(f"⚠️  Force mode: clearing {len(existing)} existing records...")
        festivals_ws.clear()
        festivals_ws.append_row(["festival_id", "date", "name", "type"])

    rows = []
    for f in INDIAN_FESTIVALS_2025_2026:
        rows.append([str(uuid.uuid4()), f["date"], f["name"], f["type"]])

    # Batch insert
    festivals_ws.append_rows(rows)
    print(f"✅ Successfully seeded {len(rows)} Indian festivals (2025-2026)!")


if __name__ == "__main__":
    force = "--force" in sys.argv
    seed_festivals(force=force)
