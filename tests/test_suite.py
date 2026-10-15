import os
import unittest
from unittest.mock import Mock,patch
import test_gui
from groove_suite import SuiteLauncher
from groove_modes import MODE_LABELS


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Tk display required')
class SuiteTests(unittest.TestCase):
    def setUp(self):
        self.app=SuiteLauncher();self.app.maxsize(4096,2160);self.app.update()

    tearDown=test_gui.LayoutTests.tearDown

    def test_logo_and_three_ordered_purple_launch_buttons_fit_when_resized(self):
        a=self.app;self.assertEqual(tuple(a.launch_buttons),('desktop','lite','mobile'))
        for size in ('320x460','440x650','600x800','360x540'):
            a.geometry(size);a.update();previous=a.logo_label
            self.assertGreaterEqual(a.logo.width(),100);self.assertGreaterEqual(a.logo.height(),120)
            for mode,b in a.launch_buttons.items():
                self.assertTrue(b.primary);self.assertFalse(b.blue)
                label=b.find_withtag('wrapped-label')[0]
                self.assertEqual(b.itemcget(label,'text'),'Launch '+MODE_LABELS[mode])
                self.assertEqual(b.itemcget(label,'fill'),'#ffffff')
                x1,y1,x2,y2=b.bbox(label)
                self.assertGreaterEqual(x1,4);self.assertGreaterEqual(y1,4)
                self.assertLessEqual(x2,b.winfo_width()-4);self.assertLessEqual(y2,b.winfo_height()-4)
                self.assertGreaterEqual(b.winfo_rooty(),previous.winfo_rooty()+previous.winfo_height())
                self.assertLessEqual(b.winfo_rooty()+b.winfo_height(),a.winfo_rooty()+a.winfo_height())
                previous=b
                with patch.object(a._mode_switch,'start') as start:b.invoke();start.assert_called_once_with(mode)

    def test_each_launch_waits_for_its_correct_child_and_failure_keeps_launcher(self):
        a=self.app;c=a._mode_switch
        for mode in MODE_LABELS:
            child=Mock(pid=7331);child.poll.return_value=None
            with patch('groove_modes.launch_command',return_value=['target.exe']),patch('groove_modes.subprocess.Popen',return_value=child),patch.object(a,'destroy') as close:
                a.launch_buttons[mode].invoke();close.assert_not_called()
                self.assertTrue(c.active)
                c.ready.write_text('{"pid":7331,"mode":"wrong"}');c.poll();close.assert_not_called()
                c.ready.write_text('{"pid":7331,"mode":"'+mode+'"}');c.poll()
                close.assert_called_once();self.assertTrue(c.success)
            for b in c.buttons:b.state(['!disabled'])
        with patch('groove_modes.launch_command',side_effect=FileNotFoundError('Missing EXE')),patch('groove_modes.messagebox.showerror'),patch.object(a,'destroy') as close:
            a.launch_buttons['lite'].invoke();close.assert_not_called();self.assertFalse(c.active)
            self.assertTrue(all(not b.disabled for b in c.buttons))
