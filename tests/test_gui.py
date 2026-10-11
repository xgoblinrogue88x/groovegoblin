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
    def test_remove_multiple_albums_keeps_other_matches_and_music(self):
        from types import SimpleNamespace
        from test_groove import GrooveTests
        from groove_core import scan_folders
        fixture=GrooveTests();fixture.setUp();self.addCleanup(fixture.tearDown)
        paths=[fixture.add_mp3(f'Library/Album {i}','song.mp3',f'Song {i}') for i in range(4)]
        before={p:p.read_bytes() for p in paths}
        a=self.app;a.roots=[str(fixture.root/'Library')]
        a.matched,issues=scan_folders(a.roots);self.assertFalse(issues)
        a.album_map={album.uid:album for album in a.matched}
        originals=list(a.matched)
        originals[1].album='Keep this approved match';originals[1].approved=True
        originals[1].lookup_results=[{'title':'Keep this search result'}]
        a.populate_albums();a.refresh_preview();a.update()
        tree=a.albums_tree
        tree.click(SimpleNamespace(x=100,y=16,state=0))
        tree.click(SimpleNamespace(x=100,y=80,state=4));a.update()
        removed={originals[0].uid,originals[2].uid}
        self.assertEqual(set(tree.selection()),removed)
        a.toggle_album_id(originals[0].uid);a.update()
        self.assertEqual(set(tree.selection()),removed)
        with patch.object(a,'scan',side_effect=AssertionError('Removal must not rescan')):
            a.remove_albums_button.invoke();a.update()
        self.assertEqual(a.matched,[originals[1],originals[3]])
        self.assertIs(a.matched[0],originals[1])
        self.assertTrue(originals[1].approved)
        self.assertEqual(originals[1].album,'Keep this approved match')
        self.assertEqual(originals[1].lookup_results,[{'title':'Keep this search result'}])
        self.assertFalse(removed & set(a.album_map))
        self.assertFalse(any(row.get('album_uid') in removed for row in a.preview_tree.data.values()))
        self.assertIsNone(a.selected_id);self.assertFalse(a.results_tree.get_children())
        self.assertEqual({p:p.read_bytes() for p in paths},before)
        tree.click(SimpleNamespace(x=100,y=16,state=0))
        tree.click(SimpleNamespace(x=100,y=48,state=1));a.update()
        self.assertEqual(len(tree.selection()),2)
        a.worker_busy=True;a.remove_selected_albums();self.assertEqual(len(a.matched),2)
        a.worker_busy=False;tree.selection_set(originals[1].uid);a.update()
        tree.body.event_generate('<Delete>');a.update()
        self.assertEqual(a.matched,[originals[3]])
        tree.body.event_generate('<Control-a>');a.update()
        self.assertEqual(tree.selection(),(originals[3].uid,))
        a.remove_albums_button.invoke();a.update()
        self.assertFalse(a.matched);self.assertFalse(a.albums_tree.get_children())
        self.assertFalse(a.actions)

    def test_mousewheel_scrolls_tables_headers_gutters_tracks_and_logs(self):
        from groove_widgets import Scrollbar
        a=self.app;a.geometry('1024x768');a.update();a._responsive.apply();a.update()
        for table in (a.albums_tree,a.preview_tree,a.results_tree):
            table.cover_provider=None
            for i in range(60):
                values=('✓','Artist','Old','New','2000',1,'READY','100%') if table.mode=='albums' else (('FOLDER','old','new','1') if table.mode=='preview' else ('Album','Artist','2000','Album',99))
                table.insert('','end',values=values)
            a.update()
            scroll=next(child for child in table.winfo_children() if isinstance(child,Scrollbar))
            targets=(table.body,scroll,table.head) if table.head.winfo_ismapped() else (table.body,scroll)
            for target in targets:
                table.body.yview_moveto(0);a.update()
                target.event_generate('<MouseWheel>',delta=-120);a.update()
                self.assertGreater(table.body.yview()[0],0,(table.mode,str(target)))
                self.assertAlmostEqual(table.body.yview()[0],1/60,places=5)
                target.event_generate('<MouseWheel>',delta=120);a.update()
                self.assertEqual(table.body.yview()[0],0)
            table.body.event_generate('<Button-5>');a.update()
            self.assertGreater(table.body.yview()[0],0)
            table.yview('moveto',.5);a.update();self.assertGreater(table.body.yview()[0],.3)
        a.tabs.select(a.track_editor);tree=a.track_editor.tree
        for i in range(60):tree.insert('','end',iid=f'wheel-{i}',values=('track',)*9)
        a.update();tree.yview_moveto(0)
        tree.event_generate('<MouseWheel>',delta=-120);a.update();self.assertGreater(tree.yview()[0],0)
        self.assertAlmostEqual(tree.yview()[0],1/60,places=5)
        tree.xview_moveto(0);tree.event_generate('<Shift-MouseWheel>',delta=-120);a.update()
        self.assertGreater(tree.xview()[0],0)
        a.tabs.select(a.tab_history)
        a.log_box.insert('end','Line\n'*100);a.log_box.yview_moveto(0);a.update()
        a.log_box.event_generate('<MouseWheel>',delta=-120);a.update()
        self.assertGreater(a.log_box.yview()[0],0)

    def test_wheel_large_and_fractional_deltas_scroll_one_row_without_class_acceleration(self):
        from groove_widgets import Scrollbar
        a=self.app;a.geometry('1024x768');a.update()
        table=a.albums_tree
        for i in range(80):table.insert('','end',values=('✓','Artist','Old','New','2000',1,'READY','100%'))
        a.tabs.select(a.track_editor);tree=a.track_editor.tree
        for i in range(80):tree.insert('','end',iid=f'fine-wheel-{i}',values=('track',)*9)
        a.update()
        for listing,view,targets,page in [
            (table.body,table.body.yview,(table.body,table.head,next(c for c in table.winfo_children() if isinstance(c,Scrollbar))),a.tab_albums),
            (tree,tree.yview,(tree,*[c for c in tree.master.winfo_children() if isinstance(c,Scrollbar)]),a.track_editor)]:
            a.tabs.select(page);a.update()
            for target in targets:
                listing.yview_moveto(0);a.update()
                target.event_generate('<MouseWheel>',delta=-480);a.update()
                self.assertAlmostEqual(view()[0],1/80,places=5)
                target.event_generate('<MouseWheel>',delta=480);a.update()
                self.assertEqual(view()[0],0)
                for _ in range(3):target.event_generate('<MouseWheel>',delta=-30);a.update()
                self.assertEqual(view()[0],0)
                target.event_generate('<MouseWheel>',delta=-30);a.update()
                self.assertAlmostEqual(view()[0],1/80,places=5)
                # Reversing a partial gesture must not consume the new direction.
                target.event_generate('<MouseWheel>',delta=-30)
                target.event_generate('<MouseWheel>',delta=120);a.update()
                self.assertEqual(view()[0],0)

    def test_tk9_touchpad_scroll_is_row_sized_in_canvas_and_editor(self):
        if int(str(self.app.tk.call('package','provide','Tk')).split('.')[0])<9:
            self.skipTest('TouchpadScroll requires Tk 9')
        a=self.app;a.geometry('1024x768');a.update()
        table=a.albums_tree
        for i in range(80):table.insert('','end',values=('✓','Artist','Old','New','2000',1,'READY','100%'))
        tree=a.track_editor.tree
        for i in range(80):tree.insert('','end',iid=f'pad-{i}',values=('track',)*9)
        for listing,height,page in [(table.body,table.rowheight,a.tab_albums),(tree,28,a.track_editor)]:
            a.tabs.select(page);a.update();listing.yview_moveto(0)
            # Tk packs signed X/Y pixel deltas into the event's delta field.
            listing.event_generate('<TouchpadScroll>',delta=(-height)&0xffff);a.update()
            self.assertAlmostEqual(listing.yview()[0],1/80,places=5)
            listing.event_generate('<TouchpadScroll>',delta=height);a.update()
            self.assertEqual(listing.yview()[0],0)
            listing.event_generate('<TouchpadScroll>',delta=(-height*5)&0xffff);a.update()
            self.assertAlmostEqual(listing.yview()[0],1/80,places=5)

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
                scan.assert_called_once();worker.assert_not_called()
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

    def test_drop_files_and_folders_starts_one_scan_for_new_supported_items(self):
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
                scan.assert_called_once();worker.assert_not_called()
            for p,data in before.items():self.assertEqual(p.read_bytes(),data)

    def test_drop_auto_scan_uses_settings_and_keeps_music_unchanged(self):
        from test_groove import GrooveTests
        f=GrooveTests();f.setUp();self.addCleanup(f.tearDown)
        included=f.add_mp3('Album','track.mp3','Song',artist='Artist',album='Album')
        nested=f.add_mp3('Album/Nested','other.mp3','Other Song',artist='Artist',album='Other Album')
        before={p:hashlib.sha256(p.read_bytes()).digest() for p in (included,nested)}
        a=self.app;a.auto_lookup.set(False);a.scan_subfolders.set(False)
        with patch.object(a.mb,'suggest') as lookup,patch.object(a,'apply') as apply:
            self.assertTrue(a.drop_paths([str(included.parent)]))
            self.assertTrue(a.worker_busy)
            deadline=time.monotonic()+5
            while a.worker_busy and time.monotonic()<deadline:
                a.update();time.sleep(.02)
            self.assertFalse(a.worker_busy)
            self.assertEqual(len(a.matched),1)
            self.assertEqual(a.matched[0].tracks[0].path,str(included))
            lookup.assert_not_called();apply.assert_not_called()
        for path,digest in before.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).digest(),digest)

    def test_workspace_and_footer_at_supported_sizes(self):
        a = self.app
        self.assertEqual(a._responsive.nav_text['scan'],'Scan & Rename')
        self.assertFalse(hasattr(a, 'workspace_canvas'))
        for width, height in [(800,600),(1024,768),(1213,813),(1536,1000),(1920,1080),(850,620),(800,600)]:
            a.geometry(f'{width}x{height}')
            a.update()
            a._responsive.apply()
            a.update()
            for widget in (a.btn_apply,a.remove_albums_button,a.album_entry,a.artist_entry,a.cover_box,a.preview_tree,a.results_tree,a.albums_tree,a._responsive.version,a.track_editor.player_cover,a.track_editor.now,a.track_editor.time,a.track_editor.progress,a.track_editor.volume,a.track_editor.audio_output_button,*a.track_editor.play_buttons,*a._responsive.toolbar,*a.nav_buttons.values(),*a._responsive.w['actions'].winfo_children()):
                self.assertTrue(widget.winfo_ismapped())
                if widget is a.remove_albums_button:
                    for item in widget.find_all():
                        if widget.type(item)=='text':self.assertLessEqual(widget.bbox(item)[2],widget.winfo_width())
                if widget in a.nav_buttons.values():
                    self.assertEqual(widget.text,a._responsive.nav_text[next(name for name,b in a.nav_buttons.items() if b is widget)])
                    for item in widget.find_all():
                        if widget.type(item)=='text':self.assertLessEqual(widget.bbox(item)[2],widget.winfo_width())
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
