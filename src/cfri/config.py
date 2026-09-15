from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "outputs"
MODEL_DIR = ROOT / "models"

CFPB_URL = "https://files.consumerfinance.gov/ccdb/complaints.csv.zip"
RAW_ZIP = RAW_DIR / "complaints.csv.zip"
PROCESSED_CSV = PROCESSED_DIR / "complaints.csv.gz"
DATABASE = PROCESSED_DIR / "complaints.db"

DEFAULT_START_DATE = "2024-01-01"
DEFAULT_MAX_ROWS = 250_000
RANDOM_STATE = 42

CANONICAL_COLUMNS = {
    "date_received": "date_received",
    "product": "product",
    "sub_product": "sub_product",
    "issue": "issue",
    "sub_issue": "sub_issue",
    "consumer_complaint_narrative": "narrative",
    "company_public_response": "company_public_response",
    "company": "company",
    "state": "state",
    "zip_code": "zip_code",
    "tags": "tags",
    "consumer_consent_provided": "consumer_consent",
    "submitted_via": "submitted_via",
    "date_sent_to_company": "date_sent_to_company",
    "company_response_to_consumer": "company_response",
    "timely_response": "timely_response",
    "consumer_disputed": "consumer_disputed",
    "complaint_id": "complaint_id",
}

