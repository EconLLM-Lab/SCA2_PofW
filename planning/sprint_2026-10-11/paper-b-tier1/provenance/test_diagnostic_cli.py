"""Model-free regression tests for bounded diagnostic controls."""
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name('evaluate_stream.py')

class DiagnosticCLI(unittest.TestCase):
    def test_explicit_controls_are_available_without_loading_model(self):
        done = subprocess.run([sys.executable, str(SCRIPT), '--help'], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        for flag in ['--compute-dtype', '--no-double-quant', '--quant-type', '--tag']:
            self.assertIn(flag, done.stdout)

    def test_unknown_quantization_type_is_rejected(self):
        done = subprocess.run([sys.executable, str(SCRIPT), '--mode', 'nf4', '--arm', 'base',
                               '--quant-type', 'invented'], capture_output=True, text=True)
        self.assertEqual(done.returncode, 2)
        self.assertIn('invalid choice', done.stderr)

if __name__ == '__main__':
    unittest.main()
