import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cfri.pipeline import stable_sample, transform


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.raw = pd.DataFrame({
            "Date received": ["2025-01-05", "bad-date", "2025-02-01"],
            "Product": ["Credit card", "Mortgage", "Debt collection"],
            "Issue": ["Fees", "Payment", "Communication"],
            "Consumer complaint narrative": ["Unexpected fee appeared on my statement.", None, "Collector called repeatedly."],
            "Company": ["Bank A", "Bank B", "Agency C"],
            "State": ["MA", "NY", "CA"],
            "Date sent to company": ["2025-01-06", "2025-01-08", "2025-02-03"],
            "Timely response?": ["Yes", "No", "Yes"],
            "Complaint ID": [101, 102, 103],
        })

    def test_transform_validates_and_derives_features(self):
        result = transform(self.raw)
        self.assertEqual(len(result), 2)
        self.assertEqual(result["response_days"].tolist(), [1, 2])
        self.assertEqual(result["is_timely"].tolist(), [1, 1])
        self.assertEqual(result["has_narrative"].tolist(), [1, 1])

    def test_stable_sample_is_bounded_and_deterministic(self):
        clean = transform(self.raw)
        first = stable_sample(clean, pd.DataFrame(), 1)
        second = stable_sample(clean, pd.DataFrame(), 1)
        self.assertEqual(len(first), 1)
        self.assertEqual(first["complaint_id"].iloc[0], second["complaint_id"].iloc[0])


if __name__ == "__main__":
    unittest.main()

