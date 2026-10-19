"""Model-free tests: claim-lock headers/status must not become Paper A inference rows."""
import csv
from pathlib import Path
import subprocess
import sys
import unittest

OUT = Path(__file__).resolve().parent

class ClaimLockTrace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, str(OUT/'trace_blast_radius.py')], check=True, capture_output=True)
        cls.rows = list(csv.DictReader((OUT/'blast_radius_locked.csv').open()))

    def test_headers_are_not_result_rows(self):
        self.assertNotIn('Item', [r['subject'] for r in self.rows])

    def test_paper_b_status_has_no_legacy_paper_a_writer(self):
        row = next(r for r in self.rows if r['subject']=='1. 42 countries')
        self.assertIn('paper_b/', row['producing_script'])
        self.assertNotIn('ksenias_base8', row['run_id'])

if __name__ == '__main__':
    unittest.main()
