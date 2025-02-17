import os
import requests
import logging
import re
from datetime import datetime

# ✅ Setup logging for execution tracking
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

# 📌 Retrieve secrets from GitHub Secrets (set in GitHub Actions)
KOBO_API_TOKEN = os.getenv("KOBO_API_TOKEN")
FORM_UID = os.getenv("FORM_UID")
BASE_ID = os.getenv("BASE_ID")
TABLE_ID = os.getenv("TABLE_ID")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")

# ✅ Validate secrets before execution
if not all([KOBO_API_TOKEN, FORM_UID, BASE_ID, TABLE_ID, AIRTABLE_API_KEY]):
    logger.error("❌ Missing one or more required environment variables!")
    exit(1)

# ✅ Construct API URLs
KOBO_URL = f"https://kf.kobotoolbox.org/api/v2/assets/{FORM_UID}/data.json"
AIRTABLE_URL = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"

# ✅ Set API Headers
kobo_headers = {"Authorization": f"Token {KOBO_API_TOKEN}"}
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}

logger.info("🔹 Starting KoboToolbox to Airtable Sync...")

# 🔹 Fetch Kobo Data
try:
    response = requests.get(KOBO_URL, headers=kobo_headers)
    response.raise_for_status()  # Raise error if response is not 200
    data = response.json().get("results", [])
    logger.info(f"✅ Retrieved {len(data)} records from KoboToolbox.")
except requests.exceptions.RequestException as e:
    logger.error(f"❌ Error fetching data from KoboToolbox: {e}")
    exit(1)


# ✅ Function to sanitize phone numbers (keep only digits)
def clean_phone_number(phone):
    return re.sub(r"\D", "", phone)  # Remove non-digit characters


# ✅ Function to fetch all existing Airtable records (ID & processed timestamp)
def fetch_existing_airtable_records():
    """Fetches all existing Airtable records to check for duplicates before updating."""
    response = requests.get(AIRTABLE_URL, headers=airtable_headers)
    if response.status_code == 200:
        records = response.json().get("records", [])
        existing_data = {}
        for record in records:
            fields = record.get("fields", {})
            id_participant = fields.get("ID de participant")
            last_processed_time = fields.get("Kobo integration last processed time", None)
            phone_number = fields.get("Numéro de téléphone")

            # Store by participant ID
            existing_data[id_participant] = {
                "record_id": record["id"],
                "last_processed_time": last_processed_time,
                "phone_number": clean_phone_number(phone_number) if phone_number else None
            }
        return existing_data
    else:
        logger.error("⚠️ Error fetching existing Airtable records:", response.text)
        return {}


# 🔹 Fetch all existing Airtable records
existing_records = fetch_existing_airtable_records()

# ✅ Validate that "Kobo integration last processed time" exists in Airtable
if not any("last_processed_time" in record for record in existing_records.values()):
    logger.error("❌ Field 'Kobo integration last processed time' does not exist. Cannot determine records to update.")
    exit(1)

# 🔹 Process Kobo Data
for entry in data:
    id_participant = entry.get("id_participant")  # Kobo participant ID
    id_ref = entry.get("id_ref")  # Recruited by
    submission_time = entry.get("_submission_time")  # Kobo timestamp

    # 1️⃣ Get existing Airtable record
    participant_data = existing_records.get(id_participant, {})
    participant_record_id = participant_data.get("record_id")
    last_processed_time = participant_data.get("last_processed_time")

    # 2️⃣ Skip already processed records
    if last_processed_time and submission_time <= last_processed_time:
        logger.info(f"⚠️ Skipping {id_participant}, already processed.")
        continue  # Skip if already processed

    if not participant_record_id:
        logger.info(f"⚠️ No existing participant found for ID {id_participant}, skipping...")
        continue

    logger.info(f"✅ Processing participant {id_participant}")

    # 3️⃣ Update "Recruté par"
    update_payload = {"fields": {"Recruté par": str(id_ref)}}
    update_response = requests.patch(f"{AIRTABLE_URL}/{participant_record_id}", json=update_payload, headers=airtable_headers)

    if update_response.status_code == 200:
        logger.info(f"✅ Updated 'Recruté par' for {id_participant}")
    else:
        logger.error(f"❌ Error updating 'Recruté par': {update_response.text}")

    # 4️⃣ Insert new recruits if they don't already exist
    recruit_ids = []
    for i in range(1, 4):  # Up to 3 recruits
        recruit_name = entry.get(f"RECRUITMENT/RECRUIT{i}_NAME", "").strip()
        recruit_phone = clean_phone_number(entry.get(f"RECRUITMENT/RECRUIT{i}_PHONE", ""))

        if recruit_name and recruit_phone:
            # Check if phone number already exists
            existing_recruit = next(
                (record_id for pid, record in existing_records.items() if record.get("phone_number") == recruit_phone),
                None
            )

            if existing_recruit:
                logger.info(f"🔄 Phone number {recruit_phone} already exists. Using existing record {existing_recruit}.")
                recruit_ids.append(existing_recruit)
            else:
                # Insert new recruit
                payload = {
                    "records": [{"fields": {"Prénom": recruit_name, "Numéro de téléphone": recruit_phone}}]
                }
                response = requests.post(AIRTABLE_URL, json=payload, headers=airtable_headers)

                if response.status_code == 200:
                    new_record_id = response.json()["records"][0]["id"]
                    logger.info(f"✅ Inserted new recruit: {recruit_name} - ID: {new_record_id}")
                    recruit_ids.append(new_record_id)
                else:
                    logger.error(f"❌ Error inserting recruit {recruit_name}: {response.text}")

    # 5️⃣ Update participant's "Recrues_ID" with new recruits
    if recruit_ids:
        update_payload = {"fields": {"Recrues_ID": recruit_ids}}
        update_response = requests.patch(f"{AIRTABLE_URL}/{participant_record_id}", json=update_payload, headers=airtable_headers)

        if update_response.status_code == 200:
            logger.info(f"✅ Linked recruits {recruit_ids} to participant {id_participant}")
        else:
            logger.error(f"❌ Error updating 'Recrues_ID': {update_response.text}")

    # 6️⃣ Update last processed timestamp
    update_payload = {"fields": {"Kobo integration last processed time": submission_time}}
    update_response = requests.patch(f"{AIRTABLE_URL}/{participant_record_id}", json=update_payload, headers=airtable_headers)

    if update_response.status_code == 200:
        logger.info(f"✅ Updated last processed time for {id_participant}")
    else:
        logger.error(f"❌ Error updating last processed time: {update_response.text}")

logger.info("🎉 Kobo-to-Airtable sync completed successfully!")
