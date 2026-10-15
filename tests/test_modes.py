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
from groove_version import __version__


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Tk display required')
class ModeTests(unittest.TestCase):
    setUp=test_gui.LayoutTests.setUp
    tearDown=test_gui.LayoutTests.tearDown

    def test_full_layout_has_no_main_screen_switches_and_fits_after_navigation(self):
        a=self.app
        self.assertEqual(a.app_mode,'desktop');self.assertFalse(a.is_lite)
        self.assertEqual(a.title().split(' - ')[0],'Groove Goblin '+__version__)
        self.assertEqual(a._mode_switch.buttons,[])
        self.assertFalse(hasattr(a,'desktop_mode_button'))
        for width,height in ((800,600),(1088,550),(1920,1080),(900,650)):
            a.geometry(f'{width}x{height}');a.update();a._responsive.apply();a.update()
            for key in ('preview','player','opts'):self.assertTrue(a._responsive.w[key].winfo_ismapped(),key)
            for page in (a.track_editor,a.lookup_page,a.tab_history,a.dashboard):
                a.tabs.select(page);a.update();sidebar=a._responsive.w['sidebar']
                for widget in (a.nav_buttons['about'],a.sidebar_player_panel,a._responsive.version):
                    self.assertGreaterEqual(widget.winfo_rooty(),sidebar.winfo_rooty())
                    self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),sidebar.winfo_rooty()+sidebar.winfo_height())
        self.assertFalse(a.opt_filenames.get())

    def test_desktop_settings_switch_order_style_and_targets(self):
        check_settings(self,('mobile','lite'))

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
                self.assertFalse(c.active)
                if not exited:child.terminate.assert_called_once()


class ModeRuntimeTests(unittest.TestCase):
    def test_default_mode_and_source_launch_commands(self):
        from groove_version import is_lite,initial_mode,MODE_EXECUTABLES,SUITE_EXECUTABLE
        with patch.dict(os.environ,{'GROOVE_GOBLIN_EDITION':'FULL'}),patch.object(sys,'argv',['GrooveGoblin.pyw']):
            self.assertFalse(is_lite())
            self.assertEqual(groove_modes.launch_command('mobile')[-1],'--mobile')
        for mode in ('desktop','lite','mobile'):
            with patch.object(sys,'argv',['GrooveGoblin.pyw','--'+mode]):
                self.assertEqual(initial_mode(),mode)
                self.assertEqual(is_lite(),mode!='desktop')
                self.assertEqual(groove_modes.launch_command(mode)[-1],'--'+mode)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve()
            for filename in MODE_EXECUTABLES.values():(root/filename).touch()
            with patch.object(sys,'frozen',True,create=True),patch.object(sys,'argv',['app']):
                for mode,filename in {**MODE_EXECUTABLES,'suite':SUITE_EXECUTABLE}.items():
                    with patch.object(sys,'executable',str(root/filename)):
                        self.assertEqual(initial_mode(),mode)
                        for target,destination in MODE_EXECUTABLES.items():
                            self.assertEqual(groove_modes.launch_command(target),[str(root/destination)])
                with patch.object(sys,'executable',str(root/SUITE_EXECUTABLE)):
                    (root/MODE_EXECUTABLES['lite']).unlink()
                    with self.assertRaises(FileNotFoundError):groove_modes.launch_command('lite')

    def test_installed_modes_share_data_and_legacy_mobile_undo_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            with patch.object(sys,'frozen',True,create=True),patch.dict(os.environ,{'LOCALAPPDATA':str(root/'user')}):
                for mode in ('FULL','LITE','MOBILE'):
                    with patch.dict(os.environ,{'GROOVE_GOBLIN_EDITION':mode}),patch.object(sys,'executable',str(root/'GrooveGoblin.exe')):
                        self.assertEqual(groove_runtime.data_dir(),root/'user/GrooveGoblin')
                legacy=root/'legacy/GrooveGoblinLite';legacy.mkdir(parents=True);(legacy/'undo.json').write_text('keep')
                with patch.dict(os.environ,{'LOCALAPPDATA':str(root/'legacy')}),patch.object(sys,'executable',str(root/'GrooveGoblinMobile.exe')):
                    self.assertEqual(groove_runtime.data_dir(),legacy);self.assertEqual((legacy/'undo.json').read_text(),'keep')


def check_settings(case,targets):
    a=case.app
    a.show_settings();a.update()
    case.assertEqual(tuple(a.settings_switch_buttons),targets)
    search=a.settings_search_button
    previous=search
    for target,button in a.settings_switch_buttons.items():
        case.assertTrue(button.winfo_ismapped());case.assertTrue(button.primary);case.assertFalse(button.blue)
        case.assertEqual(button.winfo_width(),search.winfo_width())
        case.assertEqual(button.winfo_height(),search.winfo_height())
        case.assertGreaterEqual(button.winfo_rooty(),previous.winfo_rooty()+previous.winfo_height())
        label=button.find_withtag('wrapped-label')[0]
        case.assertEqual(button.itemcget(label,'text'),'Switch to '+groove_modes.MODE_LABELS[target])
        case.assertEqual(button.itemcget(label,'fill'),'#ffffff')
        x1,y1,x2,y2=button.bbox(label)
        case.assertGreaterEqual(x1,4);case.assertGreaterEqual(y1,4)
        case.assertLessEqual(x2,button.winfo_width()-4);case.assertLessEqual(y2,button.winfo_height()-4)
        with patch.object(a._mode_switch,'start') as switch:button.invoke();switch.assert_called_once_with(target)
        previous=button
    # At small heights the form scrolls to expose every complete button.
    for width,height in ((300,280),(480,560)):
        a.settings_window.geometry(f'{width}x{height}');a.update()
        a.settings_canvas.yview_moveto(1);a.update()
        last=a.settings_switch_buttons[targets[-1]]
        case.assertLessEqual(last.winfo_rooty()+last.winfo_height(),a.settings_window.winfo_rooty()+a.settings_window.winfo_height())
    a.settings_window.destroy()
    case.assertTrue(all(not b.winfo_exists() for b in a._mode_switch.buttons))


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Tk display required')
class MobileSwitchTests(unittest.TestCase):
    edition_name='MOBILE'
    setUp=test_lite.LiteTests.setUp
    tearDown=test_lite.LiteTests.tearDown

    def test_mobile_settings_purple_switches_show_full_labels(self):
        a=self.app;self.assertEqual(a.app_mode,'mobile')
        self.assertIn('Mobile Mode',a.title());self.assertNotIn('Remote Mode',a.title())
        a.geometry('360x640');a.update();a._responsive.apply();a.update()
        self.assertEqual(a._mode_switch.buttons,[])
        check_settings(self,('desktop','lite'))


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Tk display required')
class LiteSwitchTests(unittest.TestCase):
    setUp=test_lite.LiteTests.setUp
    tearDown=test_lite.LiteTests.tearDown

    def test_lite_settings_purple_switches_show_full_labels(self):
        self.assertEqual(self.app.app_mode,'lite');self.assertFalse(hasattr(self.app,'_phone'))
        self.assertEqual(self.app._mode_switch.buttons,[])
        check_settings(self,('mobile','desktop'))
