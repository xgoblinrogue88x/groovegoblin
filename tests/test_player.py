"""Real MP3/FLAC streaming through SDL's dummy audio device plus playlist controls."""
import os
import unittest
from unittest.mock import Mock,patch
from groove_player import MusicPlayer


class PlaybackTests(unittest.TestCase):
    def test_windows_rejects_silent_driver_except_explicit_audio_tests(self):
        mixer=Mock();mixer.get_init.return_value=(44100,-16,2);mixer.get_driver.return_value='dummy'
        player=MusicPlayer(mixer,compatibility=False)
        with patch('groove_player.os.name','nt'):
            with self.assertRaisesRegex(RuntimeError,'silent audio backend'):player.ready()
            mixer.quit.assert_called_once()
            player.allow_test_output=True;player.ready()

    def test_listening_copy_cache_bounds_wav_and_flac_together(self):
        from test_groove import GrooveTests
        from groove_decode import PlaybackDecoder
        from pathlib import Path
        f=GrooveTests();f.setUp();self.addCleanup(f.tearDown)
        decoder=PlaybackDecoder();self.addCleanup(decoder.close)
        sources=[]
        for index in range(5):
            source=f.root/f'copy-{index}.flac';source.write_bytes(f.masterflac.read_bytes());sources.append(source)
            output=decoder.request({'path':str(source)},output_format='wav' if index%2==0 else 'flac').result(timeout=8)
            self.assertTrue(Path(output).is_file())
        copies=list(Path(decoder.temporary.name).iterdir())
        self.assertEqual(len(copies),4)
        self.assertEqual({p.suffix for p in copies},{'.wav','.flac'})
        self.assertTrue(all(p.read_bytes()==f.masterflac.read_bytes() for p in sources))

    def test_compatibility_flac_is_non_silent_stereo_wav_and_preserves_source(self):
        import subprocess,tempfile,time,wave
        from pathlib import Path
        from array import array
        from groove_manual import read_track
        os.environ.setdefault('SDL_AUDIODRIVER','dummy')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'24bit.flac'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=2','-ac','2','-sample_fmt','s32','-c:a','flac',str(path)],check=True)
            before=path.read_bytes();player=MusicPlayer(compatibility=True,allow_test_output=True)
            self.addCleanup(player.close)
            player.set_volume(70);player.play([read_track(path)])
            self.assertEqual(player.state,'buffering')
            deadline=time.monotonic()+8
            while player.state=='buffering' and time.monotonic()<deadline:time.sleep(.02);player.pump()
            self.assertEqual(player.state,'playing')
            self.assertEqual(Path(player.loaded_path).suffix,'.wav')
            with wave.open(player.loaded_path,'rb') as audio:
                self.assertEqual((audio.getnchannels(),audio.getsampwidth(),audio.getframerate()),(2,2,48000))
                samples=array('h',audio.readframes(4800));self.assertGreater(max(map(abs,samples)),1000)
            self.assertAlmostEqual(player.mixer.music.get_volume(),.7,delta=.02)
            player.seek(.5);self.assertAlmostEqual(player.offset,.5)
            player.toggle();self.assertEqual(player.state,'paused')
            player.configure_output(compatibility=True)
            deadline=time.monotonic()+8
            while player.state=='buffering' and time.monotonic()<deadline:time.sleep(.02);player.pump()
            self.assertEqual(player.state,'paused');self.assertGreaterEqual(player.position,.5)
            player.test_sound();self.assertIsNotNone(player.test_channel)
            self.assertGreater(max(map(abs,array('h',player.test_clip.get_raw()))),1000)
            player.stop();self.assertEqual(player.state,'stopped')
            self.assertEqual(path.read_bytes(),before)
            player.close()

    def test_explicit_output_reconnect_and_failed_device_never_falls_back_silently(self):
        mixer=Mock();mixer.get_init.return_value=(44100,-16,2)
        mixer.music.get_pos.return_value=1250;mixer.music.get_busy.return_value=True
        mixer.quit.side_effect=lambda:setattr(mixer.get_init,'return_value',None)
        mixer.init.side_effect=lambda **kwargs:setattr(mixer.get_init,'return_value',(44100,-16,2))
        player=MusicPlayer(mixer,compatibility=False)
        player.play([{'path':'track.flac','duration':10}]);player.toggle()
        mixer.music.play.side_effect=lambda **kwargs:setattr(mixer.music.get_pos,'return_value',0)
        player.configure_output('Headphones')
        mixer.init.assert_called_with(devicename='Headphones')
        self.assertEqual(player.device,'Headphones');self.assertEqual(player.state,'paused')
        self.assertEqual(player.position,1.25)
        mixer.init.side_effect=RuntimeError('device disconnected')
        with self.assertRaisesRegex(RuntimeError,'Could not open audio output'):
            player.configure_output('Disconnected output')
        self.assertEqual(player.device,'Headphones');self.assertEqual(player.state,'stopped')
        mixer.init.assert_called_with(devicename='Disconnected output')

    def test_real_mp3_and_flac_load_seek_pause_volume_stop(self):
        from test_groove import GrooveTests
        from groove_manual import read_track
        f=GrooveTests();f.setUp();self.addCleanup(f.tearDown)
        files=[f.add_mp3('MP3','song.mp3','Song'),f.add_flac('FLAC','song.flac','Song')]
        os.environ.setdefault('SDL_AUDIODRIVER','dummy')
        player=MusicPlayer(compatibility=False,allow_test_output=True);self.addCleanup(player.close)
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
        player=MusicPlayer(mixer,compatibility=False)
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

    def test_stop_cancels_preparation_and_never_starts_late_audio(self):
        from groove_decode import PlaybackDecoder
        import threading,time
        from pathlib import Path
        from tempfile import TemporaryDirectory
        started=threading.Event()
        def prepare(record,cancel):
            started.set()
            if cancel.wait(3):raise RuntimeError('Canceled')
            raise RuntimeError('Test decoder did not receive cancellation')
        mixer=Mock();mixer.get_init.return_value=True
        player=MusicPlayer(mixer);self.addCleanup(player.close)
        with patch.object(PlaybackDecoder,'decode',side_effect=prepare):
            player.play([{'path':'test.wav','duration':10}])
            self.assertTrue(started.wait(2));future=player.future;folder=Path(player.decoder.temporary.name)
            player.stop()
            deadline=time.monotonic()+3
            while not future.done() and time.monotonic()<deadline:time.sleep(.01)
            self.assertTrue(future.done());player.pump()
            self.assertEqual(player.state,'stopped');mixer.music.play.assert_not_called()
            player.close();self.assertFalse(folder.exists())
