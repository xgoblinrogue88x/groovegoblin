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

    def test_folder_drop_multiple_unicode_duplicates_invalid_and_busy_is_read_only(self):
        import tempfile
        a = self.app
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / 'Björk {Live} album'
            second = root / 'Other album'
            first.mkdir();second.mkdir()
            media = first / 'track.mp3'
            media.write_bytes(b'disposable fixture - not real audio')
            before = hashlib.sha256(media.read_bytes()).digest()
            with patch.object(a,'scan') as scan, patch.object(a,'run_background') as worker:
                self.assertTrue(a.drop_folder_paths([str(first),str(second),str(media),str(root/'missing')]))
                self.assertEqual(a.roots,[str(first.resolve()),str(second.resolve())])
                self.assertIn('Ignored 2',a.status.get())
                self.assertTrue(a.drop_folder_paths([str(first),str(first / '..' / first.name)]))
                self.assertEqual(len(a.roots),2)
                self.assertIn('already',a.status.get())
                self.assertFalse(a.drop_folder_paths([str(media)]))
                a.worker_busy=True
                self.assertFalse(a.drop_folder_paths([str(root)]))
                self.assertEqual(len(a.roots),2)
                a.worker_busy=False
                scan.assert_not_called();worker.assert_not_called()
            self.assertEqual(hashlib.sha256(media.read_bytes()).digest(),before)
            self.assertFalse(a.matched)
            with patch.object(self.module.filedialog,'askdirectory',return_value=str(first)):
                a.add_folder()
            self.assertEqual(len(a.roots),2)

    def test_filename_checkbox_preview_and_missing_number_review(self):
        from test_groove import GrooveTests
        from groove_core import scan_folders
        f=GrooveTests();f.setUp();self.addCleanup(f.tearDown)
        path=f.add_mp3('Album','old.mp3','Jump',artist='Van Halen')
        before=hashlib.sha256(path.read_bytes()).digest()
        a=self.app
        a.matched,errors=scan_folders([path.parent]);self.assertFalse(errors)
        album=a.matched[0];album.approved=True
        a.album_map={album.uid:album};a.opt_folders.set(False);a.opt_tags.set(False)
        a.populate_albums();a.refresh_preview()
        self.assertFalse(a.opt_filenames.get())
        a.filename_check.invoke()
        a.preview_tabs['Filenames'].invoke()
        rows=a.preview_tree.get_children();self.assertEqual(len(rows),1)
        self.assertEqual(a.preview_tree.item(rows[0],'values')[2],'01 - Van Halen - Jump.mp3')
        self.assertEqual(hashlib.sha256(path.read_bytes()).digest(),before)
        album.tracks[0].number=None
        a.refresh_preview();a.preview_tabs['Skipped'].invoke()
        self.assertEqual(len(a.preview_tree.get_children()),1)
        self.assertIn('track number',a.problems[0])
        self.assertIn('disabled',a.btn_apply.state())

    def test_drop_files_and_folders_adds_only_supported_items_without_scanning(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);folder=root/'Album {Live}';folder.mkdir()
            mp=root/'Björk - Song.MP3';mp.write_bytes(b'disposable test bytes')
            fl=root/'Other song.flac';fl.write_bytes(b'disposable test bytes')
            unsupported=root/'Notes.txt';unsupported.write_text('leave this alone')
            before={p:p.read_bytes() for p in (mp,fl,unsupported)}
            a=self.app
            with patch.object(a,'scan') as scan,patch.object(a,'run_background') as worker:
                self.assertTrue(a.drop_paths([str(mp),str(folder),str(fl),str(unsupported)]))
                self.assertEqual(a.roots,[str(mp.resolve()),str(folder.resolve()),str(fl.resolve())])
                self.assertIn('Ignored 1',a.status.get())
                self.assertTrue(a.drop_paths([str(mp),str(folder)]))
                self.assertEqual(len(a.roots),3)
                a.worker_busy=True
                self.assertFalse(a.drop_paths([str(root)]))
                self.assertEqual(len(a.roots),3)
                a.worker_busy=False
                scan.assert_not_called();worker.assert_not_called()
            for p,data in before.items():self.assertEqual(p.read_bytes(),data)

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
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            first=Path(temporary)/'one.mp3';second=Path(temporary)/'two.flac'
            first.write_bytes(b'first fixture');second.write_bytes(b'second fixture')
            paths=(str(first),str(second),str(first))
            with patch.object(self.module.filedialog,'askopenfilenames',return_value=paths):
                a.add_files()
            self.assertEqual(a.roots,[str(first.resolve()),str(second.resolve())])
