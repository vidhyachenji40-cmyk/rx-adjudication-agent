import json


def audit_claim(claim):
    audit_report = []

    # Rule 1: NPI Length (Must be 10 digits)
    npi = str(claim.get("prescriber_npi", ""))
    if len(npi) != 10:
        claim["notes"] = "INVALID_NPI"
        audit_report.append(f"NPI '{npi}' is {len(npi)} digits — flagged as INVALID_NPI.")

    # Rule 2: Dosage Math
    try:
        qty = int(claim.get("quantity", 0))
        dosage = float(claim.get("daily_dosage", 1))
        expected_days = int(qty / dosage)

        if int(claim.get("days_supply", 0)) != expected_days:
            audit_report.append(f"days_supply corrected to {expected_days}.")
            claim["days_supply"] = expected_days
    except Exception as e:
        audit_report.append(f"Math error: {str(e)}")

    claim["audit_report"] = audit_report
    return claim


def audit_claims_batch(claims: list[dict]) -> list[dict]:
    """
    Run audit_claim over a list of claims and return results in the
    format expected by optimizer.py:
      { claim_id, prescriber_npi, passed, errors: [{error_code, field, message, healed}] }
    """
    results = []
    for raw in claims:
        claim = dict(raw)
        audited = audit_claim(claim)

        errors = []

        if audited.get("notes") == "INVALID_NPI":
            errors.append({
                "field": "prescriber_npi",
                "error_code": "INVALID_NPI",
                "message": next(
                    (m for m in audited["audit_report"] if "INVALID_NPI" in m), "Invalid NPI."
                ),
                "healed": False,
            })

        ndc = str(audited.get("ndc", ""))
        if ndc == "NDC_NOT_FOUND" or audited.get("notes") == "NDC_NOT_FOUND":
            errors.append({
                "field": "ndc",
                "error_code": "NDC_NOT_FOUND",
                "message": f"NDC '{ndc}' not found in formulary.",
                "healed": False,
            })

        results.append({
            "claim_id": audited.get("claim_id", "UNKNOWN"),
            "prescriber_npi": audited.get("prescriber_npi", "UNKNOWN"),
            "passed": len(errors) == 0,
            "error_count": len(errors),
            "errors": errors,
            "healed_claim": audited if len(errors) == 0 else {},
        })

    return results


if __name__ == "__main__":
    test_claim = {
        "claim_id": "RX-999",
        "drug_name": "Simvastatin",
        "prescriber_npi": "9876",
        "quantity": "90",
        "daily_dosage": 1,
        "days_supply": 30,
    }
    print(json.dumps(audit_claim(test_claim), indent=2))