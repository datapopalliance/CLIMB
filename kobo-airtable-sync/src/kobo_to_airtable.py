import os
import requests
import logging
import re
from datetime import datetime

# ✅ Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

TEST_ENVIRONMENT = True

# 📌 Retrieve secrets from environment variables
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

# ✅ Validate secrets
missing_vars = [var for var, val in {
    "KOBO_API_TOKEN": KOBO_API_TOKEN,
    "FORM_UID": FORM_UID,
    "BASE_ID": BASE_ID,
    "TABLE_ID": TABLE_ID,
    "AIRTABLE_API_KEY": AIRTABLE_API_KEY
}.items() if not val]

if missing_vars:
    logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
    exit(1)

# ✅ API URLs and Headers
KOBO_URL = f"https://kf.kobotoolbox.org/api/v2/assets/{FORM_UID}/data.json"
AIRTABLE_URL = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"

kobo_headers = {"Authorization": f"Token {KOBO_API_TOKEN}"}
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}

logger.info("🔹 Starting KoboToolbox to Airtable Sync...")

# Helper functions
def clean_phone_number(phone):
    return re.sub(r"[^\d]", "", phone) if phone else None

def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

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
                
                if "Kobo integration last processed time" in fields:
                    field_exists = True
                
                participant_id = safe_int(fields.get("ID de participant"))
                phone = fields.get("Numéro de téléphone")
                carrier = fields.get("Opérateur")
                last_processed_time = fields.get("Kobo integration last processed time")
                recrute_par = fields.get("Recruté par")
                
                if participant_id is not None:
                    existing_records[participant_id] = {
                        "record_id": record["id"],
                        "last_processed_time": last_processed_time,
                        "phone_numbers": [clean_phone_number(num) for num in re.split(r"[,/-]", phone)] if phone else [],
                        "phone": clean_phone_number(phone),
                        "carrier": carrier,
                        "recrute_par": safe_int(recrute_par) if recrute_par else None
                    }
            
            offset = data.get("offset")
            if not offset:
                break
        else:
            logger.error(f"❌ Error fetching Airtable records: {response.text}")
            break

    if not field_exists:
        logger.error("❌ Field 'Kobo integration last processed time' does not exist. Cannot determine records to update.")
        exit(1)
    
    return existing_records

def insert_recruit(name, phone, ref_id):
    ref_data = existing_airtable_records.get(ref_id, {})
    ref_phone = ref_data.get("phone", "")
    ref_carrier = ref_data.get("carrier", "")
    
    payload = {"records": [{"fields": {
        "Prénom": name,
        "Numéro de téléphone": phone,
        "Date de soumission": datetime.now().strftime("%Y-%m-%d"),
        "Recruté par": str(ref_id),
        "ref_phone": ref_phone,
        "ref_carrier": ref_carrier
    }}]}
    response = requests.post(AIRTABLE_URL, json=payload, headers=airtable_headers)
    
    if response.status_code == 200:
        records = response.json().get("records", [])
        if records:
            return records[0]["id"]
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
    kobo_data = response.json().get("results", []) if response.status_code == 200 else []
    logger.info(f"✅ Retrieved {len(kobo_data)} records from KoboToolbox.")
except requests.exceptions.RequestException as e:
    logger.error(f"❌ Error fetching data from KoboToolbox: {e}")
    exit(1)
    
# ✅ Step 3: Process Kobo Data
for entry in kobo_data:
    id_participant = safe_int(entry.get("id_participant"))
    id_ref = safe_int(entry.get("id_ref"))
    submission_time = entry.get("_submission_time")

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

    # ✅ Step 4: Process recruits
    recruit_ids = []
    for i in range(1, 4):
        recruit_name = entry.get(f"RECRUITMENT/RECRUIT{i}_NAME", "").strip()
        recruit_phone = clean_phone_number(entry.get(f"RECRUITMENT/RECRUIT{i}_PHONE", "").strip())
        
        if recruit_name and recruit_phone:
            existing_recruit_id = next((data["record_id"] for data in existing_airtable_records.values() if recruit_phone in data["phone_numbers"]), None)
            
            if existing_recruit_id:
                recruit_ids.append(existing_recruit_id)
            else:
                new_recruit_id = insert_recruit(recruit_name, recruit_phone, id_participant)
                if new_recruit_id:
                    recruit_ids.append(new_recruit_id)

    # 4️⃣ Update participant's "Recrues_ID" with new recruits
    if recruit_ids:
        update_payload = {"fields": {"Recrues_ID": recruit_ids}}
        update_response = requests.patch(f"{AIRTABLE_URL}/{record_id}", json=update_payload, headers=airtable_headers)

        if update_response.status_code == 200:
            logger.info(f"✅ Linked recruits {recruit_ids} to participant {id_participant}")
        else:
            logger.error(f"❌ Error updating 'Recrues_ID': {update_response.text}")

    # 5️⃣ Populate "Statut" field based on recruitment status
    statut = "Participant et recruteur" if recruit_ids else "Participant mais pas recruteur"
    statut_response = requests.patch(f"{AIRTABLE_URL}/{record_id}", json={"fields": {"Statut": statut}}, headers=airtable_headers)
    
    if statut_response.status_code == 200:
        logger.info(f"✅ Updated 'Statut' for participant {id_participant} to '{statut}'")
    else:
        logger.error(f"❌ Error updating 'Statut': {statut_response.text}")
        
logger.info("🎉 Kobo-to-Airtable sync completed successfully!")
