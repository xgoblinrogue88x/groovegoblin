"""Default track naming, read-only planning, collision protection and undo."""
import hashlib
import unittest
from mutagen.id3 import ID3, TRCK
from groove_core import scan_folders, plan_actions, apply_actions, undo_journal, filename_destination


class FilenameTests(unittest.TestCase):
    def setUp(self):
        from test_groove import GrooveTests
        self.fixture=GrooveTests();self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.options={'tags':False,'folders':False,'filenames':True}

    def approved(self, folders):
        albums, errors=scan_folders(folders)
        self.assertFalse(errors)
        for album in albums:
            album.album='Approved Album';album.year='1990';album.approved=True
        return albums

    def test_flac_mp3_rename_with_folder_moves_preserves_bytes_and_undo(self):
        f=self.fixture
        fl=f.add_flac('FLAC album','old.flac','Unchained',trackno='5/12')
        mp=f.add_mp3('MP3 album','old.mp3','Jump: Live?',artist='Mötley Crüe')
        tag=ID3(mp);tag['TRCK']=TRCK(encoding=3,text=['7/12']);tag.save(mp)
        originals={p:hashlib.sha256(p.read_bytes()).digest() for p in (fl,mp)}
        albums=self.approved([fl.parent,mp.parent])
        options={**self.options,'folders':True}
        actions,issues=plan_actions(albums,options);self.assertFalse(issues)
        self.assertEqual({a['tracks'][0]['new_name'] for a in actions},
                         {'05 - Van Halen - Unchained.flac','07 - Mötley Crüe - Jump_ Live_.mp3'})
        for path,digest in originals.items():self.assertEqual(hashlib.sha256(path.read_bytes()).digest(),digest)
        journal=apply_actions(actions,f.root/'program',options)
        from pathlib import Path
        for action in actions:
            track=action['tracks'][0]
            dest=Path(action['dest_folder'])/track['new_name']
            self.assertEqual(hashlib.sha256(dest.read_bytes()).digest(),originals[Path(track['old_path'])])
        self.assertFalse(undo_journal(journal))
        for path,digest in originals.items():self.assertEqual(hashlib.sha256(path.read_bytes()).digest(),digest)

    def test_artist_fallback_missing_number_and_opt_out(self):
        f=self.fixture
        mp=f.add_mp3('Album','original.mp3','Song',artist='Track Artist')
        album=self.approved([mp.parent])[0];track=album.tracks[0]
        album.artist='Compilation Artist'
        self.assertEqual(filename_destination(track,album.artist),'01 - Track Artist - Song.mp3')
        track.artist='';track.albumartist='Album Artist'
        self.assertEqual(filename_destination(track,album.artist),'01 - Album Artist - Song.mp3')
        track.albumartist=''
        self.assertEqual(filename_destination(track,album.artist),'01 - Compilation Artist - Song.mp3')
        track.number=103
        self.assertTrue(filename_destination(track,album.artist).startswith('103 - '))
        for number in (None,0,-1):
            track.number=number
            actions,issues=plan_actions([album],self.options)
            self.assertFalse(actions);self.assertIn('track number',issues[0])
        actions,issues=plan_actions([album],{**self.options,'filenames':False})
        self.assertFalse(issues);self.assertEqual(actions[0]['tracks'][0]['new_name'],mp.name)

    def test_collisions_before_and_after_preview_are_rejected_without_writes(self):
        f=self.fixture
        mp=f.add_mp3('Album','original.mp3','Song',artist='Artist')
        albums=self.approved([mp.parent]);before=hashlib.sha256(mp.read_bytes()).digest()
        target=mp.with_name('01 - ARTIST - SONG.MP3')
        target.write_bytes(b'untouched existing file')
        actions,issues=plan_actions(albums,self.options)
        self.assertFalse(actions);self.assertIn('already exists',issues[0])
        target.unlink()
        actions,issues=plan_actions(albums,self.options);self.assertFalse(issues)
        target.write_bytes(b'created after preview')
        with self.assertRaisesRegex(ValueError,'Output filename now exists'):
            apply_actions(actions,f.root/'program',self.options)
        self.assertEqual(target.read_bytes(),b'created after preview')
        self.assertEqual(hashlib.sha256(mp.read_bytes()).digest(),before)

    def test_two_tracks_cannot_have_same_output_name(self):
        f=self.fixture
        first=f.add_mp3('Album','first.mp3','Song',artist='Artist')
        f.add_mp3('Album','second.mp3','Song',artist='ARTIST')
        actions,issues=plan_actions(self.approved([first.parent]),self.options)
        self.assertFalse(actions);self.assertIn('duplicate output filename',issues[0])

    def test_removed_source_folder_is_reported_in_preview_and_apply(self):
        f=self.fixture
        path=f.add_mp3('Album','old.mp3','Song',artist='Artist')
        albums=self.approved([path.parent])
        actions,issues=plan_actions(albums,self.options);self.assertFalse(issues)
        path.unlink();path.parent.rmdir()
        planned,issues=plan_actions(albums,self.options)
        self.assertFalse(planned);self.assertIn('cannot read source folder',issues[0])
        with self.assertRaisesRegex(ValueError,'Source folder no longer exists'):
            apply_actions(actions,f.root/'program',self.options)
