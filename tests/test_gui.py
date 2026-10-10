"""Run with a real/virtual display; exercises the actual Tk widgets."""
import hashlib
import importlib.util
import importlib.machinery
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'Tk display required')
class LayoutTests(unittest.TestCase):
    def setUp(self):
        loader = importlib.machinery.SourceFileLoader('groove_gui', str(ROOT / 'GrooveGoblin.pyw'))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.module = importlib.util.module_from_spec(spec)
        loader.exec_module(self.module)
        self.app = self.module.GrooveGoblin()
        self.app.update()

    def tearDown(self):
        for callback in self.app.tk.call('after', 'info'):
            self.app.after_cancel(callback)
        self.app.destroy()

    def test_workspace_and_footer_at_supported_sizes(self):
        a = self.app
        for width, height in [(800, 600), (1024, 768), (1920, 1080)]:
            a.geometry(f'{width}x{height}')
            a.update()
            self.assertTrue(a.btn_apply.winfo_ismapped())
            self.assertGreaterEqual(a.btn_apply.winfo_rootx(), a.winfo_rootx())
            self.assertLessEqual(a.btn_apply.winfo_rooty() + a.btn_apply.winfo_height(), a.winfo_rooty() + height)
            a.workspace_canvas.xview_moveto(1)
            a.workspace_canvas.yview_moveto(1)
            a.update()
            self.assertTrue(a.album_entry.winfo_ismapped())
            self.assertTrue(a.preview_tree.winfo_ismapped())
            self.assertTrue(a.results_tree.winfo_ismapped())
        a.tabs.select(a.tab_history)
        a.update()
        self.assertTrue(a.log_box.winfo_ismapped())
        a.tabs.select(a.tab_preview)
        a.update()
        self.assertTrue(a.preview_tree.winfo_ismapped())

    def test_scan_approve_filter_clear_is_read_only(self):
        # Existing helpers generate disposable test audio, never user music.
        from test_groove import GrooveTests
        fixture = GrooveTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        media = fixture.add_mp3('Album', 'track.mp3', 'Song', artist='Artist', album='Old')
        before = hashlib.sha256(media.read_bytes()).digest()
        a = self.app
        a.roots = [str(fixture.root)]
        a.auto_lookup.set(False)
        # If scan reads a Tk variable from the worker, fail that operation.
        import threading
        main = threading.get_ident()
        real_get = a.auto_lookup.get
        def checked_get():
            self.assertEqual(threading.get_ident(), main)
            return real_get()
        with patch.object(a.auto_lookup, 'get', side_effect=checked_get):
            a.scan()
            deadline = time.monotonic() + 5
            while a.worker_busy and time.monotonic() < deadline:
                a.update()
                time.sleep(.02)
        self.assertFalse(a.worker_busy)
        self.assertEqual(len(a.matched), 1)
        uid = a.matched[0].uid
        a.albums_tree.selection_set(uid)
        a.update()
        self.assertEqual(a.var_album.get(), 'Old')
        a.var_album.set('New Album')
        a.var_year.set('1990')
        a.save_match()
        self.assertTrue(a.matched[0].approved)
        self.assertNotIn('disabled', a.btn_apply.state())
        for filter_name, action in [('Folders', 'FOLDER'), ('Tags', 'TAGS')]:
            a.preview_filter.set(filter_name)
            a.refresh_preview()
            rows = a.preview_tree.get_children()
            self.assertTrue(rows)
            self.assertTrue(all(a.preview_tree.item(row, 'values')[0] == action for row in rows))
        self.assertEqual(before, hashlib.sha256(media.read_bytes()).digest())
        a.clear()
        self.assertEqual(a.var_album.get(), '')
        self.assertFalse(a.albums_tree.get_children())
        self.assertIn('disabled', a.btn_apply.state())
