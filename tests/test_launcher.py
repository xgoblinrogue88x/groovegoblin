"""Startup probe regression and real Windows native-argument validation."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'Launch-GrooveGoblin.ps1'

class LauncherTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'Tk display required')
    def test_probes_survive_legacy_powershell_quote_removal(self):
        probes = re.findall(r"-c '([^'\r\n]+)'", SCRIPT.read_text())
        self.assertGreaterEqual(len(probes), 4)
        for probe in probes:
            # Reproduce the quote loss seen when Windows PowerShell 5.1 passes
            # print("Tk window check passed") to python.exe as a native argument.
            with self.subTest(probe=probe):
                result = subprocess.run([sys.executable, '-c', probe.replace('"', '')],
                                        capture_output=True, text=True, timeout=15)
                # The virtual-environment probe intentionally returns 1 in a venv.
                expected = int(sys.prefix != sys.base_prefix) if 'sys.prefix == sys.base_prefix' in probe else 0
                self.assertEqual(result.returncode, expected, result.stderr)

    @unittest.skipUnless(os.name == 'nt' and shutil.which('powershell.exe'),
                         'Windows PowerShell is required for the native launch check')
    def test_windows_powershell_exact_interpreter_prerequisites(self):
        result = subprocess.run(['powershell.exe', '-NoLogo', '-NoProfile',
                                 '-ExecutionPolicy', 'Bypass', '-File', str(SCRIPT),
                                 '-CheckOnly', '-PythonPath', sys.executable],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Startup prerequisites passed.', result.stdout)
