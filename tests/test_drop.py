"""A native drop must collect data without calling Tk inside the callback."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from groove_windows_drop import NativeFolderDrop, WM_DROPFILES, WM_NULL, PM_REMOVE


class FakeWindowsAPI:
    def __init__(self):
        self.accepted={};self.finished=[];self.forwarded=[];self.removed=[]
        self.drop_paths=[]
    def make_proc(self, callback): return callback
    def install_hook(self, proc): self.proc=proc;return 44
    def remove_hook(self, hook): self.removed.append(hook)
    def parent(self, hwnd): return 30
    def exists(self, hwnd): return True
    def accept(self, hwnd, enabled): self.accepted[hwnd]=enabled
    def paths(self, drop): return self.drop_paths
    def finish(self, drop): self.finished.append(drop)
    def message(self, message): return message
    def next_hook(self, *args): self.forwarded.append(args);return 42


class Window:
    def __init__(self, hwnd, children=()): self.hwnd=hwnd;self.children=children
    def winfo_id(self): return self.hwnd
    def winfo_children(self): return self.children


class NativeDropTests(unittest.TestCase):
    def setUp(self):
        self.api=FakeWindowsAPI()
        self.app=Window(10,[Window(20)])
        for name in ('update_idletasks','after','after_idle','after_cancel',
                     'report_callback_exception','log'):
            setattr(self.app,name,Mock())
        self.app.after.return_value='timer'
        self.app.status=Mock()
        self.on_drop=Mock()
        self.drop=NativeFolderDrop(self.app,self.on_drop,self.api)
        self.addCleanup(self.drop.close)
        self.app.after.reset_mock();self.app.update_idletasks.reset_mock()

    def message(self, hwnd=20):
        return SimpleNamespace(hWnd=hwnd,message=WM_DROPFILES,wParam=99,lParam=0)

    def assert_no_tk_calls(self):
        for name in ('after','after_idle','after_cancel','update_idletasks',
                     'report_callback_exception','log'):
            getattr(self.app,name).assert_not_called()
        self.app.status.set.assert_not_called()
        self.on_drop.assert_not_called()

    def test_drop_never_calls_tk_until_timer_drain_and_close_removes_hook(self):
        self.api.drop_paths=['C:\\Music\\Björk {Live}', 'C:\\Music\\Song.mp3']
        self.assertEqual(self.api.accepted,{10:True,20:True,30:True})
        message=self.message()
        self.assertEqual(self.drop.handle_message(0,PM_REMOVE,message),42)
        self.assertEqual(message.message,WM_NULL)
        self.assertEqual(message.wParam,0)
        self.assertEqual(self.api.finished,[99])
        self.assert_no_tk_calls()
        self.drop.drain()
        self.on_drop.assert_called_once_with(self.api.drop_paths)
        self.app.after.assert_called_once_with(50,self.drop.drain)
        self.drop.close();self.drop.close()
        self.assertEqual(self.api.removed,[44])
        self.assertFalse(any(self.api.accepted.values()))
        self.app.after_cancel.assert_called_once_with('timer')

    def test_peek_negative_hook_code_and_other_window_are_left_untouched(self):
        message=self.message()
        self.drop.handle_message(0,0,message)  # PM_NOREMOVE
        self.drop.handle_message(-1,PM_REMOVE,message)
        self.drop.handle_message(0,PM_REMOVE,self.message(hwnd=100))
        self.assertEqual(message.message,WM_DROPFILES)
        self.assertFalse(self.api.finished)
        self.assertFalse(self.drop.pending)
        self.assert_no_tk_calls()
        self.drop.handle_message(0,PM_REMOVE,message)
        self.assertEqual(self.api.finished,[99])

    def test_bad_drop_releases_handle_without_tk_error_reporting_in_callback(self):
        self.api.paths=Mock(side_effect=OSError('invalid drop handle'))
        message=self.message()
        self.drop.handle_message(0,PM_REMOVE,message)
        self.assertEqual(self.api.finished,[99])
        self.assertEqual(message.message,WM_NULL)
        self.assert_no_tk_calls()
        self.drop.drain()
        self.app.log.assert_called_once()
        self.app.status.set.assert_called_once()
        self.on_drop.assert_not_called()
