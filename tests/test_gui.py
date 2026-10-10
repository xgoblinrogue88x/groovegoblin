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
        # Cancel root-owned callbacks through their owner; child widgets cancel
        # their own redraw callbacks on destruction.
        for callback in self.app.tk.call('after', 'info'):
            script, _ = self.app.tk.call('after', 'info', callback)
            if script.split()[0] in (self.app._tclCommands or []):
                self.app.after_cancel(callback)
        self.app.destroy()

    def test_workspace_and_footer_at_supported_sizes(self):
        a = self.app
        self.assertFalse(hasattr(a, 'workspace_canvas'))
        for width, height in [(800,600),(1024,768),(1213,813),(1536,1000),(1920,1080),(850,620),(800,600)]:
            a.geometry(f'{width}x{height}')
            a.update()
            a._responsive.apply()
            a.update()
            for widget in (a.btn_apply,a.album_entry,a.artist_entry,a.cover_box,a.preview_tree,a.results_tree,a.albums_tree,*a._responsive.toolbar,*a.nav_buttons.values(),*a._responsive.w['actions'].winfo_children()):
                self.assertTrue(widget.winfo_ismapped())
                x=widget.winfo_rootx()-a.winfo_rootx();y=widget.winfo_rooty()-a.winfo_rooty()
                if widget in a._responsive.buttons:
                    self.assertGreaterEqual(widget.winfo_height(),int(widget.cget('height'))-2,(width,height,str(widget)))
                self.assertGreaterEqual(x,0)
                self.assertGreaterEqual(y,0)
                self.assertLessEqual(x+widget.winfo_width(),width, (width,height,str(widget)))
                self.assertLessEqual(y+widget.winfo_height(),height, (width,height,str(widget)))
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

    def test_table_checkbox_bulk_selection_problem_filter_and_result_pick(self):
        from groove_core import Album
        a=self.app
        one=Album('one','/test/one',[],'One','Old','New','1990',approved=True)
        two=Album('two','/test/two',[],'Two','Old','New','2000',approved=False)
        a.matched=[one,two];a.album_map={x.uid:x for x in a.matched}
        a.populate_albums();a.update()
        a.albums_tree.body.event_generate('<Button-1>',x=15,y=16)
        a.update()
        self.assertFalse(one.enabled)
        self.assertEqual(a.selected_id,'one')
        a.toggle_all_albums();self.assertTrue(all(x.enabled for x in a.matched))
        a.show_problems.set(True);a.populate_albums();a.update()
        self.assertEqual(a.albums_tree.get_children(),('two',))
        a.show_problems.set(False);a.populate_albums()
        a.albums_tree.selection_set('two');a.update()
        two.lookup_results=[{'title':'Chosen','artist':'Two','year':'1985','id':'mock','type':'Album','score':90}]
        a.populate_results(two);a.update()
        width=a.results_tree.body.winfo_width()
        a.results_tree.body.event_generate('<Button-1>',x=width-30,y=33)
        a.update()
        self.assertTrue(two.approved);self.assertEqual(two.album,'Chosen')
        self.assertEqual(two.year,'1985')

    def test_add_files_uses_explicit_picker_paths(self):
        a=self.app
        with patch.object(self.module.filedialog, 'askopenfilenames', return_value=('one.mp3','two.flac','one.mp3')):
            a.add_files()
        self.assertEqual(a.roots,['one.mp3','two.flac'])
