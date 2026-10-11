"""Real Tk Track Editor workflow on disposable tracks; no writes to user media."""
import hashlib
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch
from PIL import Image
from groove_manual import read_track
from groove_version import __version__


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Tk display required')
class TrackEditorTests(unittest.TestCase):
    def test_audio_output_device_selection_test_sound_and_failure_feedback(self):
        from tkinter import ttk
        from groove_widgets import Button,Check
        e=self.editor;a=self.app
        with patch.object(e.player,'output_devices',return_value=['Speakers','Headphones']):
            e.audio_output_button.invoke();a.update()
        dialog=e.audio_dialog
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        widgets=list(descendants(dialog))
        combo=next(w for w in widgets if isinstance(w,ttk.Combobox))
        self.assertEqual(combo.cget('values'),('System default','Speakers','Headphones'))
        combo.set('Headphones')
        next(w for w in widgets if isinstance(w,Check)).variable.set(True)
        buttons={w.text:w for w in widgets if isinstance(w,Button)}
        with patch.object(e.player,'configure_output') as configure,patch.object(e.player,'test_sound') as tone:
            buttons['Test Sound'].invoke();a.update()
            configure.assert_called_once_with('Headphones',compatibility=True);tone.assert_called_once()
        with patch.object(e.player,'configure_output',side_effect=RuntimeError('Output disconnected')):
            buttons['Reconnect'].invoke();a.update()
        messages=[w for w in widgets if w.winfo_class()=='Label' and w.cget('textvariable')]
        self.assertTrue(any('Output disconnected' in a.getvar(w.cget('textvariable')) for w in messages))
        for size in ('520x350','560x350'):
            dialog.geometry(size);a.update()
            for widget in (combo,*buttons.values()):
                self.assertTrue(widget.winfo_ismapped())
                self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(),dialog.winfo_rootx()+dialog.winfo_width())
                self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),dialog.winfo_rooty()+dialog.winfo_height())
        dialog.destroy()

    def setUp(self):
        from test_gui import LayoutTests
        from test_groove import GrooveTests
        self.gui=LayoutTests();self.gui.setUp()
        self.app=self.gui.app;self.editor=self.app.track_editor
        self.f=GrooveTests();self.f.setUp();self.addCleanup(self.f.tearDown);self.addCleanup(self.gui.tearDown)
        self.paths=[self.f.add_mp3('Album','first.mp3','First'),self.f.add_flac('Album','second.flac','Second')]
        self.editor.storage_base=self.f.root/'program'
        self.editor.records={str(p):read_track(p) for p in self.paths};self.editor.refresh()
        self.app.tabs.select(self.editor);self.app.update()

    def wait(self):
        deadline=time.monotonic()+6
        while self.app.worker_busy and time.monotonic()<deadline:
            self.app.update();time.sleep(.02)
        self.app.update();self.assertFalse(self.app.worker_busy)

    def test_batch_and_individual_edits_artwork_save_and_undo(self):
        e=self.editor;before={p:hashlib.sha256(p.read_bytes()).digest() for p in self.paths}
        e.tree.selection_set([str(p) for p in self.paths]);e.selection_changed()
        self.assertEqual(e.vars['title'].get(),'') # mixed values remain untouched
        e.vars['album'].set('Batch Album');e.stage_fields()
        self.assertEqual(len(e.pending),2)
        self.assertNotIn('title',e.pending[str(self.paths[0])])
        e.tree.selection_set(str(self.paths[0]));e.selection_changed();e.vars['title'].set('Only First');e.stage_fields()
        self.assertEqual(e.pending[str(self.paths[0])]['title'],'Only First')
        self.assertNotIn('title',e.pending[str(self.paths[1])])
        image=self.f.root/'art.png';Image.new('RGB',(20,20),'blue').save(image)
        e.tree.selection_set([str(p) for p in self.paths])
        with patch('groove_track_editor.filedialog.askopenfilename',return_value=str(image)):e.choose_artwork()
        for p,hashed in before.items():self.assertEqual(hashlib.sha256(p.read_bytes()).digest(),hashed)
        with patch.object(e,'review_changes',return_value=True):e.save()
        self.wait()
        self.assertFalse(e.pending)
        for p in self.paths:self.assertEqual(read_track(p)['album'],'Batch Album');self.assertEqual(read_track(p)['front_cover_count'],1)
        self.assertEqual(read_track(self.paths[0])['title'],'Only First');self.assertEqual(read_track(self.paths[1])['title'],'Second')
        with patch('groove_track_editor.messagebox.askyesno',return_value=True):e.undo()
        self.wait()
        for p,hashed in before.items():self.assertEqual(hashlib.sha256(p.read_bytes()).digest(),hashed)

    def test_pause_keeps_batch_playlist_after_skipping(self):
        e=self.editor;e.tree.selection_set([str(p) for p in self.paths])
        e.player.playlist=[e.records[str(p)] for p in self.paths];e.player.index=1;e.player.state='paused'
        with patch.object(e.player,'toggle') as toggle,patch.object(e.player,'play') as play:
            e.play_pause();toggle.assert_called_once();play.assert_not_called()
        e.player.state='stopped'

    def test_cancelled_review_keeps_staging_and_music_unchanged(self):
        e=self.editor;e.tree.selection_set(str(self.paths[0]));e.selection_changed()
        before=self.paths[0].read_bytes();e.vars['artist'].set('New Artist');e.stage_fields()
        with patch.object(e,'review_changes',return_value=False):e.save()
        self.assertFalse(self.app.worker_busy);self.assertTrue(e.pending)
        self.assertEqual(self.paths[0].read_bytes(),before)
        e.discard_selected();self.assertFalse(e.pending)

    def test_inline_cell_edit_and_about_version(self):
        from types import SimpleNamespace
        e=self.editor;path=str(self.paths[0]);e.tree.selection_set(path);e.tree.see(path);self.app.update()
        bbox=e.tree.bbox(path,'title');self.assertTrue(bbox)
        e.begin_inline(SimpleNamespace(x=bbox[0]+5,y=bbox[1]+5))
        self.assertIsNotNone(e.inline)
        e.inline.delete(0,'end');e.inline.insert(0,'Inline title');e.inline.focus_force();self.app.update()
        e.inline.event_generate('<Return>');self.app.update()
        self.assertEqual(e.pending[path]['title'],'Inline title')
        self.assertEqual(read_track(path)['title'],'First')
        self.app.nav_buttons['about'].invoke();self.app.update()
        dialog=self.app._about_window
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        labels=[w for w in descendants(dialog) if w.winfo_class()=='Label']
        self.assertTrue(any(__version__ in w.cget('text') for w in labels))
        self.app.show_about();self.assertIs(self.app._about_window,dialog)
        for size in ('560x520','620x540'):
            dialog.geometry(size);self.app.update()
            for label in labels:
                self.assertGreaterEqual(label.winfo_height(),label.winfo_reqheight(),label.cget('text'))
                self.assertLessEqual(label.winfo_rooty()+label.winfo_height(),label.master.winfo_rooty()+label.master.winfo_height(),label.cget('text'))
        dialog.destroy()

    def test_presets_update_live_previews_and_use_approved_album(self):
        from groove_core import scan_folders
        a=self.app;a.matched,_=scan_folders([self.paths[0].parent])
        album=a.matched[0];album.album='Preset Album';album.year='1997';album.approved=True
        a.album_map={album.uid:album};a.opt_filenames.set(True);a.opt_tags.set(False)
        a.file_format.set('Artist - Album - ## - Title')
        a.file_format_box.event_generate('<<ComboboxSelected>>')
        a.set_preview_filter('Filenames')
        row=a.preview_tree.get_children()[0]
        self.assertEqual(a.preview_tree.item(row,'values')[2],'Other Artist - Preset Album - 01 - First.mp3')
        a.folder_format.set('Artist - Year - Album');a.folder_format_box.event_generate('<<ComboboxSelected>>')
        a.set_preview_filter('Folders');row=a.preview_tree.get_children()[0]
        self.assertTrue(a.preview_tree.item(row,'values')[2].endswith(album.artist+' - 1997 - Preset Album'))

    def test_album_tag_only_apply_refreshes_loaded_editor_signature(self):
        from groove_core import scan_folders
        from groove_manual import plan_manual
        a=self.app;e=self.editor;path=str(self.paths[0])
        a.matched,_=scan_folders([self.paths[0].parent])
        album=a.matched[0];album.album='Corrected Album';album.year='2001';album.approved=True
        a.album_map={album.uid:album};a.opt_folders.set(False);a.opt_filenames.set(False)
        e.pending[path]={'title':'Still staged'}
        with patch.object(self.gui.module,'BASE',e.storage_base),patch('tkinter.messagebox.askyesno',return_value=True),patch('tkinter.messagebox.showinfo'):
            a.apply();self.wait()
            self.assertEqual(e.records[path]['album'],'Corrected Album')
            self.assertEqual(e.records[path]['signature'],read_track(path)['signature'])
            plans,issues=plan_manual(e.records,e.pending);self.assertFalse(issues);self.assertEqual(len(plans),1)
            a.undo();self.wait()
        self.assertEqual(e.records[path]['album'],'Bad Album')
        self.assertEqual(e.pending[path]['title'],'Still staged')

    def test_album_rename_and_undo_keep_editor_paths_and_staged_edits(self):
        from groove_core import scan_folders
        a=self.app;e=self.editor;old=str(self.paths[0]);original=self.paths[0].read_bytes()
        a.matched,_=scan_folders([self.paths[0].parent])
        album=a.matched[0];album.album='Organized';album.year='2001';album.approved=True
        a.album_map={album.uid:album};a.opt_filenames.set(True);a.opt_tags.set(False)
        a.roots=[str(self.paths[0].parent)];e.pending[old]={'title':'Staged title'}
        with patch.object(self.gui.module,'BASE',e.storage_base),patch('tkinter.messagebox.askyesno',return_value=True),patch('tkinter.messagebox.showinfo'):
            a.apply();self.wait()
            moved=[p for p in e.records if Path(p).suffix=='.mp3'][0]
            self.assertNotEqual(old,moved);self.assertTrue(Path(moved).is_file())
            self.assertEqual(e.pending[moved]['title'],'Staged title')
            self.assertEqual(Path(moved).read_bytes(),original)
            a.undo();self.wait()
        self.assertIn(old,e.records);self.assertNotIn(moved,e.records)
        self.assertEqual(e.pending[old]['title'],'Staged title')
        self.assertEqual(self.paths[0].read_bytes(),original)

    def test_drop_on_editor_loads_directly_without_organizer_scan_or_saving(self):
        a=self.app;e=self.editor;a.auto_lookup.set(False)
        path=self.f.add_mp3('New Album','new.mp3','New song')
        before=path.read_bytes()
        original_matched=list(a.matched);original_roots=list(a.roots)
        old=str(self.paths[0]);e.pending[old]={'title':'Keep staged title'}
        with patch.object(a,'scan',side_effect=AssertionError('Editor drops must not scan organizer input')):
            self.assertTrue(a.drop_paths([str(path)]));self.wait()
        self.assertIn(str(path),e.records)
        self.assertEqual(path.read_bytes(),before)
        self.assertEqual(a.matched,original_matched);self.assertEqual(a.roots,original_roots)
        self.assertEqual(e.pending[old],{'title':'Keep staged title'})

    def test_editor_add_buttons_and_folder_drops_append_tracks_independently(self):
        a=self.app;e=self.editor
        direct=self.f.add_mp3('Direct','one.mp3','Direct song')
        album=self.f.add_flac('Dropped album','two.flac','Album song')
        nested=self.f.add_mp3('Dropped album/Subfolder','three.mp3','Nested song')
        before={p:p.read_bytes() for p in (direct,album,nested,*self.paths)}
        a.auto_lookup.set(True)
        with patch.object(a,'scan',side_effect=AssertionError('Direct additions must not change organizer scan')),patch.object(a,'worker_match_albums',side_effect=AssertionError('Direct additions must stay offline')):
            with patch('groove_track_editor.filedialog.askopenfilenames',return_value=(str(direct),)):
                e.top_buttons[0].invoke();self.wait()
            self.assertIn(str(direct),e.records)
            a.scan_subfolders.set(False)
            with patch('groove_track_editor.filedialog.askdirectory',return_value=str(album.parent)):
                e.top_buttons[1].invoke();self.wait()
            self.assertIn(str(album),e.records);self.assertNotIn(str(nested),e.records)
            a.scan_subfolders.set(True)
            self.assertTrue(a.drop_paths([str(album.parent),str(album),str(direct)]));self.wait()
            self.assertIn(str(nested),e.records)
            self.assertEqual(len(e.records),5)
        self.assertFalse(a.roots);self.assertFalse(a.matched)
        self.assertEqual({p:p.read_bytes() for p in before},before)

    def test_wav_drop_scans_imports_and_pcm_editor_blocks_embedded_edits(self):
        import shutil,subprocess
        from groove_formats import FILE_PATTERN
        a=self.app;e=self.editor;a.auto_lookup.set(False)
        wav=self.f.root/'new.wav'
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(self.f.mastermp3),'-y',str(wav)],check=True)
        original=wav.read_bytes();self.assertIn('*.wma',FILE_PATTERN);self.assertIn('*.dsf',FILE_PATTERN)
        self.assertTrue(a.drop_paths([str(wav)]));self.wait()
        self.assertIn(str(wav),e.records);self.assertEqual(wav.read_bytes(),original)
        e.tree.selection_set(str(wav));e.selection_changed();e.vars['title'].set('WAV title');e.stage_fields()
        self.assertEqual(e.pending[str(wav)]['title'],'WAV title');self.assertEqual(wav.read_bytes(),original)
        pcm=self.f.root/'raw.pcm';pcm.write_bytes(b'\0'*17640)
        e.records[str(pcm)]=read_track(pcm);e.refresh();e.tree.selection_set(str(pcm));e.selection_changed()
        self.assertTrue(e.entries['title'].instate(['disabled']))
        self.assertFalse(e.entries['filename'].instate(['disabled']))
        self.assertTrue(e.art_buttons[0].disabled)
        settings={'format':'s16le','rate':44100,'channels':2}
        with patch.object(e,'pcm_dialog',return_value=settings),patch.object(e.player,'play') as play:
            e.play_pause();self.assertEqual(e.records[str(pcm)]['pcm'],settings)
            self.assertEqual(next(t for t in play.call_args.args[0] if t['path']==str(pcm))['pcm'],settings)

    def test_themed_scrollbars_drag_and_theme_images_survive_zoom(self):
        from tkinter import ttk
        e=self.editor;a=self.app
        for index in range(80):
            e.tree.insert('','end',iid='viewport-test-'+str(index),values=('Track '+str(index),)*8)
        a.update()
        listing=e.tree.master
        bars=[w for w in listing.winfo_children() if isinstance(w,ttk.Scrollbar)]
        vertical=next(w for w in bars if str(w.cget('orient'))=='vertical')
        horizontal=next(w for w in bars if str(w.cget('orient'))=='horizontal')
        self.assertGreater(e.tree.yview()[1],0);self.assertLess(e.tree.yview()[1],1)
        self.assertFalse(vertical.instate(['disabled']))
        # Exercise the actual themed thumb through Tk's built-in bindings.
        vertical.event_generate('<ButtonPress-1>',x=5,y=12)
        vertical.event_generate('<B1-Motion>',x=5,y=120)
        vertical.event_generate('<ButtonRelease-1>',x=5,y=120);a.update()
        self.assertGreater(e.tree.yview()[0],0)
        horizontal.event_generate('<ButtonPress-1>',x=20,y=5)
        horizontal.event_generate('<B1-Motion>',x=100,y=5)
        horizontal.event_generate('<ButtonRelease-1>',x=100,y=5);a.update()
        self.assertGreater(e.tree.xview()[0],0)
        e.player.playlist=[{**e.records[str(self.paths[0])],'duration':100}];e.player.index=0
        e.progress.configure(to=100);e.progress.set(0);a.update()
        x,y=e.progress.coords()
        with patch.object(e.player,'seek') as seek:
            e.progress.event_generate('<ButtonPress-1>',x=x,y=y)
            e.progress.event_generate('<B1-Motion>',x=e.progress.winfo_width()//2,y=y)
            e.progress.event_generate('<ButtonRelease-1>',x=e.progress.winfo_width()//2,y=y)
            seek.assert_called_once();self.assertGreater(seek.call_args.args[0],0)
        e.player.playlist=[];e.player.index=-1
        photos=[str(p) for p in a._theme_images];a.zoom(1);a.update()
        live=set(a.tk.call('image','names'))
        self.assertTrue(set(photos).issubset(live))
        for index in range(80):e.tree.delete('viewport-test-'+str(index))
        a.update();self.assertTrue(vertical.instate(['disabled']))

    def test_editor_widgets_and_branding_fit_during_resize(self):
        a=self.app;e=self.editor
        for width,height in [(800,600),(1024,768),(1536,1000),(1920,1080),(850,620)]:
            a.geometry(f'{width}x{height}');a.update();a._responsive.apply();e.resize();a.update()
            for widget in (*e.entries.values(),e.cover,e.save_button,e.undo_button,e.stage_button,e.discard_button,e.progress,e.volume,e.audio_output_button,*e.play_buttons,*e.top_buttons):
                self.assertTrue(widget.winfo_ismapped(),str(widget))
                parent=widget.master
                x=widget.winfo_rootx();y=widget.winfo_rooty()
                self.assertGreaterEqual(x,a.winfo_rootx())
                self.assertGreaterEqual(y,a.winfo_rooty())
                self.assertLessEqual(x+widget.winfo_width(),a.winfo_rootx()+width,(width,height,str(widget)))
                self.assertLessEqual(y+widget.winfo_height(),a.winfo_rooty()+height,(width,height,str(widget)))
                self.assertLessEqual(y+widget.winfo_height(),parent.winfo_rooty()+parent.winfo_height(),(width,height,str(widget),'parent'))
            self.assertIn(__version__,a.title())
        a.tabs.select(a.tab_albums);a.update()
        self.assertTrue(a.btn_apply.winfo_ismapped())
        a.geometry('1536x1000');a.update();a._responsive.apply();a.update()
        version=a._responsive.version
        import tkinter.font as tkfont
        self.assertEqual(a._responsive.w['brand'].winfo_children(),[a._logo_label])
        self.assertGreaterEqual(a.logo.width(),200)
        self.assertLessEqual(version.winfo_rooty()+version.winfo_height(),a.winfo_rooty()+a.winfo_height())
        for size in ('1120x740','1320x800','1536x1000','1920x1080'):
            a.geometry(size);a.update();a._responsive.apply();a.update()
            note=a._responsive.w['format_note'];font=tkfont.Font(master=a,font=note.cget('font'))
            self.assertTrue(note.winfo_ismapped())
            self.assertLessEqual(font.measure(note.cget('text')),note.winfo_width())
            self.assertGreaterEqual(note.winfo_height(),note.winfo_reqheight())
            self.assertLessEqual(note.winfo_rooty()+note.winfo_height(),note.master.winfo_rooty()+note.master.winfo_height())
