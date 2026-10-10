"""Keep a fatal native/Tk error isolated from the rest of the test suite."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


class WindowsDropSmokeTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='nt','Windows message loop required')
    def test_posted_native_drop_survives_mainloop_and_adds_paths(self):
        script=Path(__file__).with_name('windows_drop_smoke.py')
        result=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('Windows drop smoke passed',result.stdout)
