import unittest
from agents.validator import audit_claims_batch

class TestPharmacyValidator(unittest.TestCase):
    def test_npi_validation(self):
        # NPI too short → INVALID_NPI in errors, claim not passed
        bad_npi = [{"claim_id": "T1", "prescriber_npi": "123", "quantity": 10, "daily_dosage": 1, "days_supply": 10}]
        result = audit_claims_batch(bad_npi)
        self.assertFalse(result[0]["passed"])
        self.assertEqual(result[0]["errors"][0]["error_code"], "INVALID_NPI")

    def test_dosage_healing(self):
        # Test case: Wrong days_supply (10/2 should be 5, but input says 10)
        wrong_math = [{"claim_id": "T2", "prescriber_npi": "1234567890", "quantity": 10, "daily_dosage": 2, "days_supply": 10}]
        result = audit_claims_batch(wrong_math)
        self.assertTrue(result[0]["passed"])
        self.assertEqual(result[0]["healed_claim"]["days_supply"], 5)

if __name__ == "__main__":
    unittest.main()