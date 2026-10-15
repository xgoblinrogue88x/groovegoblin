import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
import test_gui
import test_lite
import groove_modes
import groove_runtime


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Tk display required')
class ModeTests(unittest.TestCase):
    setUp=test_gui.LayoutTests.setUp
    tearDown=test_gui.LayoutTests.tearDown

    def test_default_full_layout_and_blue_label_fit_through_resizing(self):
        a=self.app
        self.assertFalse(a.is_lite)
        self.assertEqual(a.title().split(' - ')[0],'Groove Goblin 1.5')
        for width,height in ((800,600),(1088,550),(1920,1080),(900,650)):
            a.geometry(f'{width}x{height}');a.update();a._responsive.apply();a.update()
            for key in ('preview','player','opts'):self.assertTrue(a._responsive.w[key].winfo_ismapped(),key)
            for page in (a.track_editor,a.lookup_page,a.tab_history,a.dashboard):
                a.tabs.select(page);a.update();b=a.desktop_mode_button
                self.assertTrue(b.winfo_ismapped());self.assertTrue(b.blue)
                label=b.find_withtag('blue-label')[0];self.assertEqual(b.itemcget(label,'text'),'Switch to Mobile Remote Mode')
                x1,y1,x2,y2=b.bbox(label)
                self.assertGreaterEqual(x1,4);self.assertGreaterEqual(y1,4)
                self.assertLessEqual(x2,b.winfo_width()-4);self.assertLessEqual(y2,b.winfo_height()-4)
        self.assertFalse(a.opt_filenames.get())

    def test_switch_blocked_while_busy_and_unsaved_cancel_keeps_current_app(self):
        a=self.app;c=a._mode_switch
        with patch('groove_modes.subprocess.Popen') as spawn,patch.object(a,'destroy') as close,patch('groove_modes.messagebox.showinfo'):
            a.worker_busy=True;c.start('mobile');spawn.assert_not_called();close.assert_not_called()
        a.worker_busy=False;a.track_editor.pending={'unsaved':{'title':'Edited'}}
        with patch('groove_modes.messagebox.askyesno',return_value=False),patch('groove_modes.subprocess.Popen') as spawn,patch.object(a,'destroy') as close:
            c.start('mobile');spawn.assert_not_called();close.assert_not_called()
        a.track_editor.pending={}

    def test_startup_handshake_closes_only_after_correct_child_is_ready(self):
        a=self.app;c=a._mode_switch;child=Mock(pid=7331);child.poll.return_value=None
        with patch('groove_modes.launch_command',return_value=['target.exe']),patch('groove_modes.subprocess.Popen',return_value=child) as spawn,patch.object(a,'destroy') as close:
            c.start('mobile');c.start('mobile');self.assertEqual(spawn.call_count,1)
            close.assert_not_called();self.assertTrue(c.active)
            self.assertIsNotNone(c.overlay)
            work=Mock()
            with patch('tkinter.messagebox.showinfo'):a.run_background(work)
            work.assert_not_called();self.assertFalse(a.worker_busy)
            c.ready.write_text(json.dumps({'pid':999,'mode':'mobile'}));c.poll();close.assert_not_called()
            c.ready.write_text(json.dumps({'pid':7331,'mode':'mobile'}));c.poll();close.assert_called_once()
            self.assertTrue(c.success);self.assertFalse(c.active)
            self.assertIsNone(c.temporary)
            self.assertIsNone(c.overlay)

    def test_missing_exe_child_exit_and_timeout_keep_current_window(self):
        a=self.app;c=a._mode_switch
        with patch('groove_modes.launch_command',side_effect=FileNotFoundError('missing')),patch.object(a,'destroy') as close,patch('groove_modes.messagebox.showerror'):
            c.start('mobile');close.assert_not_called();self.assertFalse(c.active)
        for exited in (True,False):
            child=Mock(pid=7331);child.poll.return_value=1 if exited else None
            with patch('groove_modes.launch_command',return_value=['target.exe']),patch('groove_modes.subprocess.Popen',return_value=child),patch.object(a,'destroy') as close,patch('groove_modes.messagebox.showerror'):
                c.start('mobile');c.deadline=0;c.poll();close.assert_not_called();self.assertFalse(c.active)
                self.assertFalse(a.desktop_mode_button.disabled)
                if not exited:child.terminate.assert_called_once()


class ModeRuntimeTests(unittest.TestCase):
    def test_default_mode_and_source_launch_commands(self):
        from groove_version import is_lite
        with patch.dict(os.environ,{'GROOVE_GOBLIN_EDITION':'FULL'}),patch.object(sys,'argv',['GrooveGoblin.pyw']):
            self.assertFalse(is_lite())
            self.assertEqual(groove_modes.launch_command('mobile')[-1],'--mobile')
        with patch.object(sys,'argv',['GrooveGoblin.pyw','--mobile']):self.assertTrue(is_lite())

    def test_installed_modes_share_data_and_legacy_mobile_undo_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            with patch.object(sys,'frozen',True,create=True),patch.dict(os.environ,{'LOCALAPPDATA':str(root/'user')}):
                for mode in ('FULL','MOBILE'):
                    with patch.dict(os.environ,{'GROOVE_GOBLIN_EDITION':mode}),patch.object(sys,'executable',str(root/'GrooveGoblin.exe')):
                        self.assertEqual(groove_runtime.data_dir(),root/'user/GrooveGoblin')
                legacy=root/'legacy/GrooveGoblinLite';legacy.mkdir(parents=True);(legacy/'undo.json').write_text('keep')
                with patch.dict(os.environ,{'LOCALAPPDATA':str(root/'legacy')}),patch.object(sys,'executable',str(root/'GrooveGoblinMobile.exe')):
                    self.assertEqual(groove_runtime.data_dir(),legacy);self.assertEqual((legacy/'undo.json').read_text(),'keep')


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Tk display required')
class MobileSwitchTests(unittest.TestCase):
    setUp=test_lite.LiteTests.setUp
    tearDown=test_lite.LiteTests.tearDown

    def test_mobile_settings_blue_button_shows_full_label_and_targets_desktop(self):
        a=self.app;a.geometry('360x640');a.update();a._responsive.apply();a.update();a.show_settings();a.update()
        b=a.settings_switch_button;self.assertTrue(b.winfo_ismapped());self.assertTrue(b.blue)
        label=b.find_withtag('blue-label')[0];self.assertEqual(b.itemcget(label,'text'),'Switch to Desktop Mode')
        x1,y1,x2,y2=b.bbox(label)
        self.assertGreaterEqual(x1,4);self.assertGreaterEqual(y1,4)
        self.assertLessEqual(x2,b.winfo_width()-4);self.assertLessEqual(y2,b.winfo_height()-4)
        self.assertLessEqual(b.winfo_rooty()+b.winfo_height(),a.settings_window.winfo_rooty()+a.settings_window.winfo_height())
        with patch.object(a._mode_switch,'start') as switch:b.invoke();switch.assert_called_once_with('desktop')
        self.assertNotIn('LITE',a.title());a.settings_window.destroy()
