import os
from pathlib import Path
import subprocess
import sys
import unittest


@unittest.skipUnless(os.name=='nt','Windows OLE required')
class NativeOutgoingDragTests(unittest.TestCase):
    def test_native_shell_copy_move_and_cancel(self):
        script=Path(__file__).with_name('windows_drag_shell_smoke.py')
        try:result=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,timeout=60)
        except subprocess.TimeoutExpired as error:
            self.fail('Native Shell timeout: '+repr(error.stdout)+'\n'+repr(error.stderr))
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('OLE cancellation passed',result.stdout)

    def test_real_gui_drag_to_shell_folder_in_all_modes(self):
        script=Path(__file__).with_name('windows_drag_gui_smoke.py')
        for mode in ('desktop','lite','mobile'):
            with self.subTest(mode=mode):
                result=subprocess.run([sys.executable,str(script),mode],capture_output=True,text=True,timeout=45)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn('Shell move passed in '+mode,result.stdout)
