"""File-picker scope and local artwork safety, with generated media only."""
import hashlib
from io import BytesIO
from pathlib import Path
import unittest
from PIL import Image
from mutagen.id3 import ID3, APIC
from groove_core import scan_folders, plan_actions, apply_actions, undo_journal
from groove_artwork import read_cover


class SelectionTests(unittest.TestCase):
    def setUp(self):
        from test_groove import GrooveTests
        self.fixture=GrooveTests();self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def test_file_selection_preserves_unselected_tracks_and_blocks_folder_move(self):
        f=self.fixture
        chosen=f.add_mp3('Album','one.mp3','One')
        untouched=f.add_mp3('Album','two.mp3','Two')
        digest=hashlib.sha256(untouched.read_bytes()).digest()
        albums, errors=scan_folders([chosen,chosen])
        self.assertFalse(errors);self.assertEqual(len(albums),1)
        a=albums[0];self.assertEqual(a.file_count,1);self.assertTrue(a.partial_selection)
        a.album='Correct Album';a.year='1997';a.approved=True
        actions, issues=plan_actions(albums,{'tags':True,'folders':True,'filenames':False})
        self.assertFalse(actions);self.assertIn('only some music files',issues[0])
        actions, issues=plan_actions(albums,{'tags':True,'folders':False,'filenames':False})
        self.assertFalse(issues)
        journal=apply_actions(actions,f.root/'program',{'tags':True,'folders':False,'filenames':False})
        self.assertEqual(str(ID3(chosen)['TALB']),'Correct Album')
        self.assertEqual(hashlib.sha256(untouched.read_bytes()).digest(),digest)
        self.assertFalse(undo_journal(journal));self.assertEqual(str(ID3(chosen)['TALB']),'Bad Album')

    def test_recursion_toggle_and_combined_folder_file_deduplication(self):
        f=self.fixture
        parent=f.add_mp3('Root','one.mp3','One')
        child=f.add_mp3('Root/Nested','two.mp3','Two')
        shallow, errors=scan_folders([parent.parent],recursive=False)
        self.assertFalse(errors);self.assertEqual(len(shallow),1);self.assertEqual(shallow[0].file_count,1)
        recursive, errors=scan_folders([parent.parent,child],recursive=True)
        self.assertFalse(errors);self.assertEqual(len(recursive),2)
        self.assertEqual(sum(a.file_count for a in recursive),2)
        self.assertFalse(any(a.partial_selection for a in recursive))

    def test_embedded_artwork_read_apply_undo_preserves_picture(self):
        f=self.fixture;p=f.add_mp3('Music','track.mp3','Song')
        data=BytesIO();Image.new('RGB',(90,60),'purple').save(data,format='PNG')
        picture=data.getvalue();tags=ID3(p);tags.add(APIC(encoding=3,mime='image/png',type=3,desc='front',data=picture));tags.save(p)
        digest=hashlib.sha256(p.read_bytes()).digest()
        albums,errors=scan_folders([p.parent]);self.assertFalse(errors)
        image=read_cover(albums[0]);self.assertEqual(image.size,(90,60))
        self.assertEqual(hashlib.sha256(p.read_bytes()).digest(),digest)
        a=albums[0];a.album='New';a.year='1990';a.approved=True
        options={'tags':True,'folders':False,'filenames':False}
        actions,issues=plan_actions(albums,options);self.assertFalse(issues)
        journal=apply_actions(actions,f.root/'program',options)
        self.assertEqual(ID3(p).getall('APIC')[0].data,picture)
        self.assertFalse(undo_journal(journal))
        self.assertEqual(ID3(p).getall('APIC')[0].data,picture)
