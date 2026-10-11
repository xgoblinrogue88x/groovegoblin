import unittest
from dataclasses import replace
from pathlib import Path
from groove_core import Track,Album,filename_destination,album_destination
from groove_naming import FILE_FORMATS,FOLDER_FORMATS


class NamingTests(unittest.TestCase):
    def setUp(self):
        self.track=Track('/Music/old.mp3','.mp3','Track Artist','Album Artist','Album','Title','1997',3,2,[0,0])
        self.album=Album('id','/Music/Old',[self.track],'Album Artist','Old','Album','1997')
    def test_file_presets_and_metadata_requirements(self):
        expected=['03 - Track Artist - Title.mp3','03 - Title.mp3','03 Title.mp3','Track Artist - Title.mp3',
                  'Title.mp3','2-03 - Title.mp3','2-03 - Track Artist - Title.mp3','Track Artist - Album - 03 - Title.mp3']
        self.assertEqual([filename_destination(self.track,format_name=f) for f in FILE_FORMATS],expected)
        self.assertEqual(filename_destination(replace(self.track,number=None),format_name='Title'),'Title.mp3')
        with self.assertRaisesRegex(ValueError,'disc number'):filename_destination(replace(self.track,disc=None),format_name='Disc-## - Title')
    def test_folder_presets_and_windows_safe_names(self):
        expected=['Album Artist - Album (1997)','Album Artist - Album','Album Artist - 1997 - Album',
                  'Album Artist - (1997) Album','Album (1997)','1997 - Album','Album']
        self.assertEqual([Path(album_destination(self.album,f)).name for f in FOLDER_FORMATS],expected)
        self.album.album='Bad: Name?';self.assertNotIn(':',Path(album_destination(self.album)).name)
        with self.assertRaisesRegex(ValueError,'Unknown naming'):album_destination(self.album,'untrusted')
