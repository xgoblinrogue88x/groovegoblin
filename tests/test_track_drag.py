"""Outgoing gestures and temporary-file reconciliation in the real editor."""
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from groove_core import scan_folders
from groove_manual import read_track
import test_lite


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Tk display required')
class DragTests(unittest.TestCase):
    setUp=test_lite.LiteTests.setUp
    tearDown=test_lite.LiteTests.tearDown
    wait=test_lite.LiteTests.wait

    def load(self):
        a=self.app;e=a.track_editor
        files=[self.fixture.add_mp3('Disc '+disc,filename,title='Track') for disc,filename in
               (('10','10.mp3'),('2','02.mp3'),('1','01.mp3'),('2','01.mp3'))]
        e.records={str(path):read_track(path) for path in files}
        for path,disc,track in zip(files,('10/12','2/12','1/12','2/12'),('1','2','1','1')):
            e.records[str(path)]['disc']=disc;e.records[str(path)]['track']=track
        e.refresh();a.tabs.select(e);a.update();e.file_drag.enabled=True
        return e,[str(path) for path in files]

    def test_numeric_disc_sort_secondary_tracks_toggle_and_refresh(self):
        e,paths=self.load();e.sort('disc')
        expected=[paths[2],paths[3],paths[1],paths[0]]
        self.assertEqual(list(e.tree.get_children()),expected)
        e.refresh();self.assertEqual(list(e.tree.get_children()),expected)
        e.sort('disc');self.assertEqual(list(e.tree.get_children()),list(reversed(expected)))
        e.sort('track');self.assertEqual([e.values(p)['track'] for p in e.tree.get_children()],['1','1','1','2'])

    def test_group_selection_survives_press_and_drag_ctrl_copy_and_click_toggle(self):
        e,paths=self.load();drag=e.file_drag;e.sort('disc')
        selected=paths[1:3];e.tree.selection_set(selected);self.app.update()
        e.tree.see(selected[0]);self.app.update();x,y,w,h=e.tree.bbox(selected[0],'#1')
        event=SimpleNamespace(x=x+8,y=y+h//2,x_root=300,y_root=300,state=4)
        self.assertEqual(drag.press(event),'break');self.assertEqual(set(e.selected()),set(selected))
        drag.release(event);self.assertEqual(e.selected(),[selected[1]])
        e.tree.selection_set(selected);self.app.update();event.state=0;drag.press(event)
        with patch.object(drag,'begin') as begin:
            drag.motion(SimpleNamespace(x_root=304,y_root=300));begin.assert_not_called()
            drag.motion(SimpleNamespace(x_root=312,y_root=304));begin.assert_called_once_with(unsaved=False)
        self.assertEqual(set(e.selected()),set(selected))

    def test_moved_tracks_relocate_bytes_keep_other_edits_and_prune_only_stale_albums(self):
        e,paths=self.load();a=self.app;drag=e.file_drag
        a.matched,issues=scan_folders(sorted({str(Path(p).parent) for p in paths}))
        a.album_map={album.uid:album for album in a.matched};a.populate_albums()
        moved=paths[1];untouched=paths[2];e.pending[untouched]={'title':'Keep staged'}
        e.tree.selection_set(moved);a.update();original=Path(moved).read_bytes()
        destination=self.fixture.root/'New Disc 2'/Path(moved).name;destination.parent.mkdir()
        def operation(items,cancel):
            self.assertEqual(items,[moved]);self.assertTrue(a.worker_busy)
            shutil.move(moved,destination)
            return {'canceled':False,'effect':2,'locations':{moved:str(destination)},'error':''}
        drag.api_factory=lambda:SimpleNamespace(drag=operation)
        self.assertTrue(drag.begin());self.wait()
        self.assertFalse(drag.active);self.assertFalse(Path(moved).exists())
        self.assertEqual(destination.read_bytes(),original)
        self.assertIn(str(destination),e.records);self.assertNotIn(moved,e.records)
        self.assertEqual(e.pending[untouched],{'title':'Keep staged'})
        self.assertEqual(e.selected(),[str(destination)])
        self.assertTrue(any(t.path==untouched for album in a.matched for t in album.tracks))
        self.assertFalse(any(t.path==moved for album in a.matched for t in album.tracks))

    def test_copy_cancel_errors_missing_cross_volume_and_unsaved_guards(self):
        e,paths=self.load();a=self.app;drag=e.file_drag;e.tree.selection_set(paths[:2]);a.update()
        original={p:Path(p).read_bytes() for p in paths}
        e.pending[paths[0]]={'title':'Unsaved'}
        with patch.object(a,'run_background') as launch:
            self.assertFalse(drag.begin());launch.assert_not_called()
        e.pending={};e.enabled['title'].set(True)
        self.assertFalse(drag.begin());e.enabled['title'].set(False)
        for canceled in (True,False):
            drag.api_factory=lambda:SimpleNamespace(drag=lambda files,cancel:{'canceled':canceled,'effect':0 if canceled else 1,'locations':{p:p for p in files},'error':''})
            self.assertTrue(drag.begin());self.wait();self.assertFalse(drag.active)
            self.assertEqual(original,{p:Path(p).read_bytes() for p in paths})
        drag.api_factory=Mock(side_effect=OSError('Native failure'))
        self.assertTrue(drag.begin());self.wait();self.assertFalse(drag.active)
        self.assertIn('Native failure',a.status.get())
        destination=self.fixture.root/'Elsewhere';destination.mkdir()
        def unknown_location(items,cancel):
            for p in items:shutil.move(p,destination/Path(p).name)
            return {'canceled':False,'effect':2,'locations':{},'error':''}
        drag.api_factory=lambda:SimpleNamespace(drag=unknown_location)
        self.assertTrue(drag.begin());self.wait()
        self.assertTrue(all(p not in e.records for p in paths[:2]));self.assertIn('destination folder',a.status.get())
        self.assertTrue(all(Path(p).is_file() for p in paths[2:]))


class DesktopDragTests(DragTests):edition_name='FULL'


class MobileDragTests(DragTests):edition_name='MOBILE'
