from database import init_db, get_festivals_sheet
import uuid

def seed_festivals():
    sheet = init_db()
    if not sheet:
        print("Database could not be initialized.")
        return

    festivals_ws = get_festivals_sheet(sheet)
    existing = festivals_ws.get_all_records()
    if len(existing) > 0:
        print("Festivals already seeded.")
        return

    festivals = [
        {"date": "2026-01-14", "name": "Makar Sankranti", "type": "Hindu"},
        {"date": "2026-01-26", "name": "Republic Day", "type": "National"},
        {"date": "2026-03-03", "name": "Holi", "type": "Hindu"},
        {"date": "2026-08-15", "name": "Independence Day", "type": "National"},
        {"date": "2026-10-02", "name": "Gandhi Jayanti", "type": "National"},
        {"date": "2026-10-18", "name": "Dussehra", "type": "Hindu"},
        {"date": "2026-11-08", "name": "Diwali", "type": "Hindu"},
        # Add more as required. Dates are placeholders for 2026.
    ]

    for f in festivals:
        festivals_ws.append_row([str(uuid.uuid4()), f["date"], f["name"], f["type"]])

    print("Festivals seeded successfully!")

if __name__ == "__main__":
    seed_festivals()
