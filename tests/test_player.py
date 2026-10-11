"""Real MP3/FLAC streaming through SDL's dummy audio device plus playlist controls."""
import os
import unittest
from unittest.mock import Mock
from groove_player import MusicPlayer


class PlaybackTests(unittest.TestCase):
    def test_real_mp3_and_flac_load_seek_pause_volume_stop(self):
        from test_groove import GrooveTests
        from groove_manual import read_track
        f=GrooveTests();f.setUp();self.addCleanup(f.tearDown)
        files=[f.add_mp3('MP3','song.mp3','Song'),f.add_flac('FLAC','song.flac','Song')]
        os.environ.setdefault('SDL_AUDIODRIVER','dummy')
        player=MusicPlayer();self.addCleanup(player.close)
        for path in files:
            with self.subTest(format=path.suffix):
                player.set_volume(40);player.play([read_track(path)])
                self.assertEqual(player.state,'playing')
                player.toggle();self.assertEqual(player.state,'paused')
                self.assertAlmostEqual(player.mixer.music.get_volume(),.4,delta=.02)
                player.seek(.05);self.assertEqual(player.state,'paused')
                player.toggle();self.assertEqual(player.state,'playing')
                player.stop();self.assertEqual(player.state,'stopped')
                self.assertEqual(player.position,0)
                player.seek(.03);self.assertEqual(player.state,'playing')
                player.stop()
    def test_playlist_next_back_completion_and_volume_clamping(self):
        mixer=Mock();mixer.get_init.return_value=True;mixer.music.get_pos.return_value=0
        mixer.music.get_busy.return_value=True
        player=MusicPlayer(mixer)
        tracks=[{'path':'first.mp3','duration':10},{'path':'second.flac','duration':20}]
        player.set_volume(120);player.play(tracks)
        mixer.music.set_volume.assert_called_with(1)
        player.next();self.assertEqual(player.index,1)
        player.previous();self.assertEqual(player.index,0)
        mixer.music.get_busy.return_value=False
        player.pump();self.assertEqual(player.index,1)
        player.pump();self.assertEqual(player.state,'finished')
        player.set_volume(-10);mixer.music.set_volume.assert_called_with(0)
        player.stop();mixer.music.unload.assert_called()
