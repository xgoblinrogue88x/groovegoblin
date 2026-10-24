"""Regression: filenames can look correct while all six embedded fields are absent."""
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
from groove_core import scan_folders,plan_actions,apply_actions,undo_journal
from groove_formats import read_fields,write_fields,can_tag

FIELDS=('title','album','year','track','artist','albumartist')
class BlankTagsTests(unittest.TestCase):
    def setUp(self):
        from test_groove import GrooveTests
        self.f=GrooveTests();self.f.setUp();self.addCleanup(self.f.tearDown)
    def test_all_taggable_containers_fill_six_blank_fields_and_restore_absence(self):
        from test_formats import fixtures
        root=self.f.root/'containers';root.mkdir()
        paths=[self.f.masterflac,self.f.mastermp3,*fixtures(root)]
        for i,source in enumerate(paths):
            if not can_tag(source):continue
            with self.subTest(fmt=source.suffix):
                folder=self.f.root/('album'+str(i));folder.mkdir()
                p=folder/('01 - ACDC - Are You Ready'+source.suffix);shutil.copyfile(source,p)
                write_fields(p,p.suffix,{k:'' for k in FIELDS});before=p.read_bytes()
                albums,issues=scan_folders([folder]);self.assertFalse(issues);a=albums[0]
                self.assertEqual(a.artist,'ACDC');self.assertEqual(a.tracks[0].title,'Are You Ready')
                self.assertEqual(a.tracks[0].number,1);self.assertEqual(p.read_bytes(),before)
                a.artist='AC/DC';a.album='The Razors Edge';a.year='1990';a.approved=True
                options={'folders':True,'filenames':True,'tags':True};actions,issues=plan_actions(albums,options);self.assertFalse(issues)
                journal=apply_actions(actions,self.f.root/'program',options)
                q=Path(actions[0]['dest_folder'])/actions[0]['tracks'][0]['new_name']
                after=read_fields(q)
                self.assertEqual({k:after[k] for k in FIELDS},dict(zip(FIELDS,('Are You Ready','The Razors Edge','1990','1','AC/DC','AC/DC'))))
                self.assertFalse(undo_journal(journal));restored=read_fields(p)
                self.assertEqual({k:restored[k] for k in FIELDS},{k:'' for k in FIELDS})
    def test_failed_persistence_stops_before_rename_and_leaves_undo(self):
        p=self.f.add_flac('Album','01 - ACDC - Are You Ready.flac','')
        write_fields(p,'.flac',{k:'' for k in FIELDS});a=scan_folders([p.parent])[0][0]
        a.artist='AC/DC';a.album='The Razors Edge';a.year='1990';a.approved=True
        actions,issues=plan_actions([a],{'tags':True,'filenames':True});self.assertFalse(issues)
        with patch('groove_core.set_tags',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'Tag verification failed'):apply_actions(actions,self.f.root/'program',{})
        self.assertTrue(p.exists());self.assertFalse(Path(actions[0]['dest_folder']).exists())
        journal=next((self.f.root/'program/Logs').glob('Groove_Goblin_Undo_*.json'))
        self.assertFalse(undo_journal(journal))
    def test_compilation_artists_and_unrelated_fields_are_preserved(self):
        p=self.f.add_flac('Compilation','01 - Singer - Song.flac','Song');write_fields(p,'.flac',{'artist':'Singer','albumartist':'Various Artists'})
        a=scan_folders([p.parent])[0][0];a.artist='Various Artists';a.album='Compilation';a.year='1990';a.approved=True
        actions,issues=plan_actions([a],{'folders':False});self.assertFalse(issues)
        journal=apply_actions(actions,self.f.root/'program',{});values=read_fields(p)
        self.assertEqual(values['artist'],'Singer');self.assertEqual(values['albumartist'],'Various Artists')
        from mutagen.flac import FLAC
        self.assertEqual(FLAC(p)['comment'],['DO NOT TOUCH']);self.assertFalse(undo_journal(journal))
    def test_missing_edition_artist_credit_does_not_block_verified_titles_and_numbers(self):
        from musicbrainz_client import MusicBrainz
        p=self.f.add_flac('Album','01 - ACDC - Song.flac','Song')
        a=scan_folders([p.parent])[0][0];a.artist='AC/DC';a.album='Album';a.mbid='group'
        mb=MusicBrainz()
        def get(endpoint,params):
            if endpoint=='release/':return {'releases':[{'id':'a','status':'Official'},{'id':'b','status':'Official'}]}
            track={'position':1,'title':'Song'}
            if endpoint=='release/a':track['artist-credit']=[{'name':'AC/DC'}]
            return {'media':[{'position':1,'tracks':[track]}]}
        mb.get=get;match=mb.track_title_match(a,{'id':'group','title':'Album','artist':'AC/DC'})
        self.assertEqual(match['titles'],{str(p):'Song'});self.assertEqual(match['numbers'],{str(p):'1'})
        self.assertFalse(match['artists'])
