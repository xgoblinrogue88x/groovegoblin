import hashlib
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Tk display required')
class LiteTests(unittest.TestCase):
    def setUp(self):
        edition=patch.dict(os.environ,{'GROOVE_GOBLIN_EDITION':'LITE'})
        edition.start();self.addCleanup(edition.stop)
        path=Path(__file__).resolve().parents[1]/'GrooveGoblin.pyw'
        loader=importlib.machinery.SourceFileLoader('groove_lite_test_app',str(path))
        self.module=importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name,loader))
        loader.exec_module(self.module)
        self.app=self.module.GrooveGoblin();self.app.maxsize(4096,2160);self.app.update()
        from test_groove import GrooveTests
        self.fixture=GrooveTests();self.fixture.setUp();self.addCleanup(self.fixture.tearDown)
        self.module.DATA=self.fixture.root/'program'
        self.app.track_editor.storage_base=self.module.DATA

    def tearDown(self):
        self.app.track_editor.player.close()
        for callback in self.app.tk.call('after','info'):
            script,_=self.app.tk.call('after','info',callback)
            if script.split()[0] in (self.app._tclCommands or []):self.app.after_cancel(callback)
        self.app.destroy()

    def test_one_action_row_hidden_panels_and_expanded_lists_at_remote_sizes(self):
        a=self.app;w=a._responsive.w
        for width,height in ((800,540),(1088,550),(1024,768),(1920,1080),(900,540)):
            a.geometry(f'{width}x{height}');a.update();a._responsive.apply();a.update()
            self.assertEqual(len({b.winfo_rooty() for b in a.lite_buttons}),1)
            for button in a.lite_buttons:
                self.assertTrue(button.winfo_ismapped())
                self.assertLessEqual(button.winfo_rootx()+button.winfo_width(),a.winfo_rootx()+a.winfo_width())
            for key in ('toolbar','preview','player','opts','controls'):
                self.assertFalse(w[key].winfo_ismapped(),key)
            self.assertGreater(a.albums_tree.winfo_height(),a._desktop.winfo_height()*.5)
            self.assertGreater(a.results_tree.winfo_height(),100)
            for button in w['actions'].winfo_children():
                self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),w['details'].body.winfo_rooty()+w['details'].body.winfo_height())
            self.assertLess(w['details'].winfo_rooty()-a.lite_toolbar.winfo_rooty(),55)
        for page in (a.track_editor,a.lookup_page,a.tab_history,a.tab_albums):
            a.tabs.select(page);a.update();self.assertFalse(w['player'].winfo_ismapped())
        self.assertIn('LITE',a.title())

    def load(self):
        from groove_core import scan_folders
        paths=[self.fixture.add_mp3('MP3','old.mp3','Song'),self.fixture.add_flac('FLAC','old.flac','Song')]
        a=self.app;a.auto_lookup.set(False)
        a.matched,_=scan_folders([self.fixture.root])
        for album in a.matched:album.album='Correct Album';album.year='2001';album.approved=True
        a.album_map={album.uid:album for album in a.matched};a.populate_albums();a.refresh_preview()
        return paths

    def test_forced_defaults_confirmation_and_cancel_leave_media_untouched(self):
        a=self.app;paths=self.load();before={p:p.read_bytes() for p in paths}
        self.assertTrue(all(v.get() for v in (a.opt_filenames,a.opt_folders,a.opt_tags,a.journal_required)))
        with patch('tkinter.messagebox.askyesno',return_value=False) as confirm,patch.object(a,'run_background') as work:
            a.apply();work.assert_not_called()
        self.assertIn(a.file_format.get(),confirm.call_args.args[1])
        self.assertIn(a.folder_format.get(),confirm.call_args.args[1])
        self.assertEqual(before,{p:p.read_bytes() for p in paths})
        self.assertFalse(self.module.DATA.exists())
        for album in a.matched:album.approved=False
        a.refresh_preview();self.assertFalse(a.btn_apply.disabled)
        with patch('tkinter.messagebox.showwarning') as warning,patch.object(a,'run_background') as work:
            a.apply();work.assert_not_called()
        self.assertIn('Approve or exclude',warning.call_args.args[1])
        self.assertNotIn('Preview Changes',warning.call_args.args[1])
        self.assertEqual(before,{p:p.read_bytes() for p in paths})

    def wait(self):
        deadline=time.monotonic()+10
        while self.app.worker_busy and time.monotonic()<deadline:self.app.update();time.sleep(.02)
        self.app.update();self.assertFalse(self.app.worker_busy)

    def test_lite_file_folder_tag_apply_and_undo_preserves_tags_and_audio(self):
        from groove_core import newest_journal
        from groove_manual import read_track
        from mutagen.flac import FLAC
        a=self.app;paths=self.load()
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        flac=next(p for p in paths if p.suffix=='.flac')
        tags=dict(FLAC(flac));audio_md5=FLAC(flac).info.md5_signature
        plans=list(a.actions)
        with patch('tkinter.messagebox.askyesno',return_value=True),patch('tkinter.messagebox.showinfo'):
            a.apply();self.wait()
            self.assertIsNotNone(newest_journal(self.module.DATA))
            for album in plans:
                for track in album['tracks']:
                    target=Path(album['dest_folder'])/track['new_name']
                    self.assertTrue(target.is_file());self.assertNotEqual(target,Path(track['old_path']))
                    self.assertEqual(read_track(target)['album'],'Correct Album')
            a.undo();self.wait()
        # Organizer undo restores tag values; FLAC padding need not be identical.
        self.assertEqual(dict(FLAC(flac)),tags)
        self.assertEqual(FLAC(flac).info.md5_signature,audio_md5)
        for path in paths:
            if path.suffix=='.mp3':self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before[path])
