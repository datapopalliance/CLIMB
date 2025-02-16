import requests

# 📌 KoboToolbox API Details
KOBO_API_TOKEN = "767a060368dea8db5a949cab15bed40753abd45c"
FORM_UID = "aUVPm42x6bpkWiESvQXzs3"
KOBO_URL = f"https://kf.kobotoolbox.org/api/v2/assets/{FORM_UID}/data.json"
kobo_headers = {"Authorization": f"Token {KOBO_API_TOKEN}"}

# 📌 Airtable API Details
AIRTABLE_API_KEY = "patY0PejDAEnhe3s1.21ea552a4087a748adedb348960dd29f8292405da7ab73f9d1474d53fe40340f"
BASE_ID = "appLI5Xn8lZVRx7EV"
TABLE_ID = "tblw2ybgsuQAJ4Wwx"
AIRTABLE_URL = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
airtable_headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}

# 🔹 Step 1: Fetch Data from KoboToolbox
response = requests.get(KOBO_URL, headers=kobo_headers)
if response.status_code == 200:
    data = response.json().get("results", [])
else:
    print("⚠️ Error fetching data from KoboToolbox:", response.text)
    data = []

# Function to find existing participant record in Airtable
def find_airtable_record(participant_id):
    query_params = {"filterByFormula": f"{{ID de participant}} = '{participant_id}'"}
    response = requests.get(AIRTABLE_URL, headers=airtable_headers, params=query_params)

    if response.status_code == 200:
        records = response.json().get("records", [])
        if records:
            return records[0]["id"]  # Return Airtable record ID
    return None

# Function to insert a new recruit and return its Airtable "ID de participant"
def insert_recruit(name, phone):
    payload = {
        "records": [{
            "fields": {
                "Prénom": name,
                "Numéro de téléphone": phone
            }
        }]
    }
    response = requests.post(AIRTABLE_URL, json=payload, headers=airtable_headers)

    if response.status_code == 200:
        records = response.json().get("records", [])
        if records:
            return records[0]["id"]  # Return Airtable-generated ID
    print(f"❌ Error inserting recruit {name}: {response.text}")
    return None

# 🔹 Step 2: Process Kobo Data
for entry in data:
    id_participant = entry.get("id_participant")  # Kobo participant ID
    id_ref = entry.get("id_ref")  # Recruited by

    # 1️⃣ Find participant record in Airtable
    participant_record_id = find_airtable_record(id_participant)

    if participant_record_id:
        print(f"✅ Found Airtable record for participant {id_participant}: {participant_record_id}")

        # 2️⃣ Update "Recruté par"
        update_payload = {"fields": {"Recruté par": str(id_ref)}}
        update_response = requests.patch(f"{AIRTABLE_URL}/{participant_record_id}", json=update_payload, headers=airtable_headers)

        if update_response.status_code == 200:
            print(f"✅ Updated 'Recruté par' for {id_participant}")
        else:
            print(f"❌ Error updating 'Recruté par': {update_response.text}")

        # 3️⃣ Insert new recruits & collect their IDs
        recruit_ids = []
        for i in range(1, 4):  # Up to 3 recruits
            recruit_name = entry.get(f"RECRUITMENT/RECRUIT{i}_NAME", "").strip()
            recruit_phone = entry.get(f"RECRUITMENT/RECRUIT{i}_PHONE", "").strip()

            if recruit_name:
                new_recruit_id = insert_recruit(recruit_name, recruit_phone)
                if new_recruit_id:
                    recruit_ids.append(new_recruit_id)

        # 4️⃣ Update participant's "Recrues_ID" with new recruits
        if recruit_ids:
            update_payload = {"fields": {"Recrues_ID": recruit_ids}}
            update_response = requests.patch(f"{AIRTABLE_URL}/{participant_record_id}", json=update_payload, headers=airtable_headers)

            if update_response.status_code == 200:
                print(f"✅ Linked recruits {recruit_ids} to participant {id_participant}")
            else:
                print(f"❌ Error updating 'Recrues_ID': {update_response.text}")
    else:
        print(f"⚠️ No existing participant found for ID {id_participant}, skipping...")
