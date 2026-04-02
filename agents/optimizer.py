import json
import sys
from pathlib import Path

# 1. Configuration
ALERT_TRIGGERS = {"INVALID_NPI", "NDC_NOT_FOUND"}

ALERT_DESCRIPTIONS = {
    "INVALID_NPI": "Prescriber NPI is not 10 digits. Possible fraud or transcription error.",
    "NDC_NOT_FOUND": "NDC not in formulary. Verify if the drug is recalled or unlisted."
}

# 2. SQL Generator for Investigations
def suggest_npi_sql(npi, code):
    return f"SELECT * FROM claims WHERE prescriber_npi = '{npi}';"

# 3. The Main Alert Function
def print_manager_alerts(results):
    """Prints professional alerts and SQL traces for bad claims."""
    print("\n" + "="*70)
    print("🚨 PHARMACY AUDIT: MANAGER ALERT SYSTEM 🚨")
    print("="*70)
    
    alerts_fired = 0
    for res in results:
        if not res.get("passed", True):
            for error in res.get("errors", []):
                code = error.get("error_code")
                if code in ALERT_TRIGGERS:
                    alerts_fired += 1
                    npi = res.get("prescriber_npi", "UNKNOWN")
                    print(f"\n[ALERT #{alerts_fired}] Claim: {res['claim_id']}")
                    print(f"  ERROR: {code} - {error.get('message')}")
                    print(f"  SQL:   {suggest_npi_sql(npi, code)}")

    if alerts_fired == 0:
        print("\n✅ No critical alerts found.")
    else:
        print(f"\nTOTAL CRITICAL ALERTS: {alerts_fired}")
    print("="*70 + "\n")

# 4. Entry point for running from terminal
if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
            print_manager_alerts(data if isinstance(data, list) else [data])