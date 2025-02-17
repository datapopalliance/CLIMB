# **Kobo to Airtable Sync**  

This repository automates the integration of **KoboToolbox** responses into **Airtable**, ensuring that new survey data is processed and updated efficiently.

More details available [in this Google Doc](https://docs.google.com/document/d/1DH3-7dv5KrfUQT29mKUVag_GMvHy_JPLqctZ1BNwaas/edit?tab=t.0)

## **Overview**  
- **Fetches** new survey responses from **KoboToolbox**.  
- **Updates** existing participant records in **Airtable**.  
- **Inserts** new recruits and links them to the correct participant.  
- **Prevents duplicates** by checking the last processed timestamp.  
- **Runs automatically** via GitHub Actions on a **cron schedule**.

## **Airtable Changes**  
The script modifies Airtable records as follows:  
- Updates **"Recruté par"** for each participant.  
- Inserts new recruit records with **"Prénom"** and **"Numéro de téléphone"**.  
- Links new recruit IDs to the original participant under **"Recrues_ID"**.  
- Updates **"Kobo integration last processed time"** to prevent duplicate processing.

## **Automation with GitHub Actions**  
- **Runs hourly** using a cron job (`0 * * * *`).  
- Can also be **triggered manually** via the GitHub Actions UI.  
- **Ensures reliability** by automating data sync.

## **Secure Credentials**  
- API keys and tokens are **not hardcoded**.  
- They are securely stored in **GitHub Secrets** (`Settings → Secrets and variables → Actions`).  
- The script retrieves credentials from **environment variables** during execution.

## **Repository Structure**  
```
📂 kobo-to-airtable-sync
│── .github/
│   └── workflows/
│       └── sync_kobo_to_airtable.yml  # GitHub Actions automation
│── scripts/
│   └── kobo_to_airtable.py            # Main integration script
│── README.md                           # Documentation
│── requirements.txt                     # Python dependencies
```

## **Setup & Deployment**  
1. **Clone the repository**  
   ```sh
   git clone https://github.com/your-username/kobo-to-airtable-sync.git
   cd kobo-to-airtable-sync
   ```
2. **Install dependencies**  
   ```sh
   pip install -r requirements.txt
   ```
3. **Run the script manually** (for testing)  
   ```sh
   python scripts/kobo_to_airtable.py
   ```
4. **Automated Execution**  
   - GitHub Actions runs it every hour.  
   - Modify `.github/workflows/sync_kobo_to_airtable.yml` to change the schedule.

---

**This integration ensures seamless synchronization between KoboToolbox and Airtable, enabling real-time data updates without manual intervention. 🚀**
