"""Exercise folder adding and the native message adapter with disposable data."""
import unittest
from unittest.mock import Mock
from groove_windows_drop import NativeFolderDrop, WM_DROPFILES, WM_NCDESTROY


class FakeWindowsAPI:
    def __init__(self):
        self.procs = {10: 110, 20: 120, 30: 130}
        self.accepted = {}
        self.finished = []
        self.forwarded = []
        self.drop_paths = []
    def make_proc(self, callback): return callback
    def parent(self, hwnd): return 30
    def exists(self, hwnd): return hwnd in self.procs
    def set_proc(self, hwnd, proc):
        previous = self.procs[hwnd];self.procs[hwnd] = proc;return previous
    def accept(self, hwnd, enabled): self.accepted[hwnd] = enabled
    def paths(self, drop): return self.drop_paths
    def finish(self, drop): self.finished.append(drop)
    def forward(self, *args): self.forwarded.append(args);return 42


class Window:
    def __init__(self, hwnd, children=()): self.hwnd=hwnd;self.children=children
    def winfo_id(self): return self.hwnd
    def winfo_children(self): return self.children


class NativeDropTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeWindowsAPI()
        self.app = Window(10, [Window(20)])
        self.app.update_idletasks = Mock()
        self.app.after_idle = Mock()
        self.app.report_callback_exception = Mock()
        self.on_drop = Mock()
        self.drop = NativeFolderDrop(self.app, self.on_drop, self.api)
        self.addCleanup(self.drop.close)

    def test_dispatch_releases_handle_and_queues_paths_then_restores_windows(self):
        self.api.drop_paths = ['C:\\Music\\Björk {Live}', 'C:\\Music\\Other Album']
        self.assertEqual(self.api.accepted,{10:True,20:True,30:True})
        self.assertEqual(self.drop.handle_message(20,WM_DROPFILES,99,0),0)
        self.assertEqual(self.api.finished,[99])
        self.on_drop.assert_not_called()
        self.app.after_idle.assert_called_once_with(self.on_drop,self.api.drop_paths)
        self.assertEqual(self.drop.handle_message(20,123,7,8),42)
        self.assertEqual(self.api.forwarded[-1],(120,20,123,7,8))
        self.drop.close()
        self.assertEqual(self.api.procs,{10:110,20:120,30:130})
        self.assertFalse(any(self.api.accepted.values()))

    def test_malformed_drop_releases_handle_and_destroyed_window_is_removed(self):
        self.api.paths = Mock(side_effect=OSError('invalid drop handle'))
        self.assertEqual(self.drop.handle_message(10,WM_DROPFILES,99,0),0)
        self.assertEqual(self.api.finished,[99])
        self.app.after_idle.assert_not_called()
        self.app.report_callback_exception.assert_called_once()
        self.drop.handle_message(20,WM_NCDESTROY,0,0)
        self.assertNotIn(20,self.drop.previous)
