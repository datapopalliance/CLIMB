import os
import requests
import logging
import re
from datetime import datetime

# ✅ Setup logging for execution tracking
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

TEST_ENVIRONMENT = True

# 📌 Retrieve secrets from GitHub Secrets (set in GitHub Actions)
if TEST_ENVIRONMENT:
    KOBO_API_TOKEN = os.getenv("KOBO_API_TOKEN")
    FORM_UID = os.getenv("KOBO_FORM_UID_RDS")
    BASE_ID = os.getenv("RDS_CLIMB_TEST_BASE_ID")
    TABLE_ID = os.getenv("RDS_CLIMB_TEST_TABLE_ID")
    AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
else:
    KOBO_API_TOKEN = os.getenv("KOBO_API_TOKEN")
    FORM_UID = os.getenv("FORM_UID")
    BASE_ID = os.getenv("BASE_ID")
    TABLE_ID = os.getenv("TABLE_ID")
    AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")

# ✅ Validate secrets before execution
missing_vars = [var for var in ["KOBO_API_TOKEN", "FORM_UID", "BASE_ID", "TABLE_ID", "AIRTABLE_API_KEY"] if not locals()[var]]
if missing_vars:
    logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
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

# Function to clean phone numbers (remove spaces, dashes, slashes, and keep only digits)
def clean_phone_number(phone):
    if phone:
        return re.sub(r"[^\d]", "", phone)
    return None

# Function to safely convert a value to an integer
def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

# Function to fetch all existing Airtable records
def fetch_existing_airtable_records():
    existing_records = {}
    field_exists = False
    offset = None
    
    while True:
        params = {"offset": offset} if offset else {}
        response = requests.get(AIRTABLE_URL, headers=airtable_headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            for record in data.get("records", []):
                fields = record.get("fields", {})

                # Check if "Kobo integration last processed time" exists
                if "Kobo integration last processed time" in fields:
                    field_exists = True

                participant_id = safe_int(fields.get("ID de participant"))  # Coerce to integer
                phone = fields.get("Numéro de téléphone")
                carrier = fields.get("Opérateur")  # New: Get carrier
                last_processed_time = fields.get("Kobo integration last processed time")

                if participant_id is not None:
                    existing_records[participant_id] = {
                        "record_id": record["id"],
                        "last_processed_time": last_processed_time,
                        "phone_numbers": [clean_phone_number(num) for num in re.split(r"[,/-]", phone)] if phone else [],
                        "carrier": carrier
                    }

            offset = data.get("offset")
            if not offset:
                break
        else:
            logger.error(f"❌ Error fetching existing Airtable records: {response.text}")
            break

    # If field does not exist, stop execution
    if not field_exists:
        logger.error("❌ Field 'Kobo integration last processed time' does not exist. Cannot determine records to update.")
        exit(1)

    return existing_records

# Function to insert a new recruit and return its Airtable "ID de participant"
def insert_recruit(name, phone, ref_phone, ref_carrier):
    payload = {
        "records": [{
            "fields": {
                "Prénom": name,
                "Numéro de téléphone": phone,
                "Date de soumission": datetime.utcnow().isoformat(),  # ✅ New: Set current date
                "ref_phone": ref_phone,  # ✅ New: Lookup reference phone
                "ref_carrier": ref_carrier  # ✅ New: Lookup reference carrier
            }
        }]
    }
    response = requests.post(AIRTABLE_URL, json=payload, headers=airtable_headers)

    if response.status_code == 200:
        records = response.json().get("records", [])
        if records:
            return records[0]["id"]  # Return Airtable-generated ID
    logger.error(f"❌ Error inserting recruit {name}: {response.text}")
    return None

# ✅ Step 1: Fetch all existing Airtable records
logger.info("🔹 Fetching existing Airtable records...")
existing_airtable_records = fetch_existing_airtable_records()
logger.info(f"✅ Fetched {len(existing_airtable_records)} records from Airtable.")

# ✅ Step 2: Fetch Kobo Data
try:
    response = requests.get(KOBO_URL, headers=kobo_headers)
    response.raise_for_status()
    kobo_data = response.json().get("results", [])
    logger.info(f"✅ Retrieved {len(kobo_data)} records from KoboToolbox.")
except requests.exceptions.RequestException as e:
    logger.error(f"❌ Error fetching data from KoboToolbox: {e}")
    exit(1)

# ✅ Step 3: Process Kobo Data
for entry in kobo_data:
    id_participant = safe_int(entry.get("id_participant"))  # Coerce Kobo ID to integer
    id_ref = safe_int(entry.get("id_ref"))  # Recruited by (convert to int)
    submission_time = entry.get("_submission_time")  # Kobo timestamp

    # ✅ Check if participant exists in Airtable
    participant_data = existing_airtable_records.get(id_participant)

    if not participant_data:
        logger.warning(f"⚠️ No existing participant found for ID {id_participant}, skipping...")
        continue

    record_id = participant_data["record_id"]
    last_processed_time = participant_data["last_processed_time"]

    # ✅ Compare submission time with last processed time
    if last_processed_time and submission_time <= last_processed_time:
        logger.info(f"⚠️ Skipping {id_participant}, already processed.")
        continue

    logger.info(f"✅ Processing participant {id_participant}...")

    # ✅ Step 4: Lookup "ref_phone" and "ref_carrier"
    ref_phone = None
    ref_carrier = None
    if id_ref in existing_airtable_records:
        ref_phone = existing_airtable_records[id_ref].get("phone_numbers", [None])[0]  # Get first phone if exists
        ref_carrier = existing_airtable_records[id_ref].get("carrier")

    # ✅ Step 5: Process recruits
    recruit_ids = []
    for i in range(1, 4):  # Up to 3 recruits
        recruit_name = entry.get(f"RECRUITMENT/RECRUIT{i}_NAME", "").strip()
        recruit_phone = clean_phone_number(entry.get(f"RECRUITMENT/RECRUIT{i}_PHONE", "").strip())

        if recruit_name and recruit_phone:
            # Check if recruit already exists in Airtable by phone number
            existing_recruit_id = None
            for participant, data in existing_airtable_records.items():
                if recruit_phone in data["phone_numbers"]:
                    existing_recruit_id = data["record_id"]
                    break

            if existing_recruit_id:
                logger.info(f"🔹 Recruit {recruit_name} already exists, linking to existing record.")
                recruit_ids.append(existing_recruit_id)
            else:
                new_recruit_id = insert_recruit(recruit_name, recruit_phone, ref_phone, ref_carrier)
                if new_recruit_id:
                    recruit_ids.append(new_recruit_id)

    logger.info("🎉 Kobo-to-Airtable sync completed successfully!")
