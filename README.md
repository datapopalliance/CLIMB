# 📌 KoboToolbox to Airtable Sync

This repository automates the process of synchronizing data from **KoboToolbox** to **Airtable**. The script fetches survey responses from KoboToolbox, processes participant and recruiter records, checks for duplicates, and updates Airtable accordingly.

## 🚀 Features & Updates

✅ **Ensures records are not processed multiple times**
   - Uses `Kobo integration last processed time` in Airtable to track updates.
   - Skips records if they have already been processed.

✅ **Ensures participant IDs match between Kobo and Airtable**
   - Coerces `ID de participant` from both sources to integers before comparing.

✅ **Handles duplicate phone numbers correctly**
   - Cleans phone numbers (removes spaces, dashes, slashes, etc.).
   - Checks for existing numbers in Airtable before inserting new recruits.

✅ **Improved logging & error handling**
   - Stops execution if `Kobo integration last processed time` field does not exist.
   - Provides detailed logs for debugging.

---

## 📂 Repository Structure
```
CLIMB/
├── kobo-airtable-sync/
│   ├── src/
│   │   ├── kobo_to_airtable.py   # 🔥 Main script
│   ├── config/
│   │   ├── config.json           # Configurations (API keys, etc.)
│   ├── docs/
│   │   ├── README.md             # 📌 This document
│   ├── requirements.txt          # 📦 Python dependencies
│   ├── .env                      # 🔑 Environment variables (not in repo)
├── .github/workflows/
│   ├── kobo_to_airtable.yml  # 🛠️ GitHub Actions workflow
```

---

## ⚙️ Setup & Configuration

### **1️⃣ Install dependencies**
```sh
pip install -r requirements.txt
```

### **2️⃣ Set up environment variables**
Define the following secrets in **GitHub Actions** or in a `.env` file:
```sh
KOBO_API_TOKEN=your_kobo_api_token
FORM_UID=your_kobo_form_uid
BASE_ID=your_airtable_base_id
TABLE_ID=your_airtable_table_id
AIRTABLE_API_KEY=your_airtable_api_key
```

### **3️⃣ Run the script locally**
```sh
python kobo-airtable-sync/src/kobo_to_airtable.py
```

### **4️⃣ Automate with GitHub Actions**
- Ensure `kobo_to_airtable.yml` is in `.github/workflows/`
- Trigger manually or set up a schedule

---

## 🔍 Workflow Overview

```plaintext
1️⃣ Fetch unprocessed records from KoboToolbox.
2️⃣ Find the corresponding participant in Airtable.
3️⃣ Update "Recruté par" field.
4️⃣ Process recruits:
   - If phone number exists → Link existing record.
   - If phone number does not exist → Insert new recruit.
5️⃣ Update "Recrues_ID" with new recruits.
6️⃣ Update "Statut" field.
7️⃣ Update "Kobo integration last processed time" in Airtable.
```

---

## 🚑 Troubleshooting

- **"No existing participant found" error?** Ensure IDs are integers in both Kobo and Airtable.
- **Repeated records?** Check for duplicate phone numbers in Airtable.
- **GitHub Actions not triggering?** Ensure `workflow_dispatch` is included in `kobo_to_airtable.yml`.

---
