"""Streamed playback with background decoding for additional formats; all commands are called from Tk's UI thread."""
import os
from pathlib import Path
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')


class MusicPlayer:
    def __init__(self,mixer=None,*,compatibility=None,allow_test_output=False):
        self.mixer=mixer;self.playlist=[];self.index=-1;self.state='stopped'
        self.volume=70;self.offset=0;self.paused_at=0;self.decoder=None;self.future=None;self.loaded_path=None
        self.device=None;self.compatibility=os.name=='nt' if compatibility is None else bool(compatibility)
        self.allow_test_output=allow_test_output
        self.resume_position=0;self.resume_paused=False;self.test_channel=None;self.test_clip=None

    def ready(self):
        if self.mixer is None:
            try:
                import pygame
                self.mixer=pygame.mixer
            except ImportError as error:raise RuntimeError('Playback needs pygame-ce. Start the program using START_GROOVE_GOBLIN.bat to install it.') from error
        if not self.mixer.get_init():
            try:self.mixer.init(devicename=self.device)
            except Exception as error:
                raise RuntimeError(f'Could not open audio output ({self.device or "system default"}). Connect your speakers/headphones and choose Audio Output in Track Editor.\n{error}') from error
        if os.name=='nt' and not self.allow_test_output and self.audio_driver in {'dummy','disk'}:
            driver=self.audio_driver;self.mixer.quit()
            raise RuntimeError(f'Playback is using the silent audio backend "{driver}". Clear any SDL_AUDIODRIVER override and restart Groove Goblin to use a real Windows audio output.')

    @property
    def audio_driver(self):
        if not self.mixer or not self.mixer.get_init():return 'Not connected'
        getter=getattr(self.mixer,'get_driver',None)
        return str(getter()) if getter else 'Unknown'

    def output_devices(self):
        from pygame._sdl2 import audio,sdl2
        sdl2.init_subsystem(sdl2.INIT_AUDIO)
        return list(dict.fromkeys(audio.get_audio_device_names(iscapture=False)))

    def configure_output(self,device=None,*,compatibility=None):
        """Reconnect the output and restore the current transport when possible."""
        state=self.state;position=self.position
        old_device=self.device;old_compatibility=self.compatibility
        self.stop()
        self.loaded_path=None
        if self.mixer and self.mixer.get_init():self.mixer.quit()
        self.device=device
        if compatibility is not None:self.compatibility=bool(compatibility)
        try:self.ready()
        except Exception:
            self.device=old_device;self.compatibility=old_compatibility
            raise
        if self.current and state in {'playing','paused','buffering'}:
            self.play()
            if self.state=='buffering':
                self.resume_position=position;self.resume_paused=state=='paused'
            else:
                if position:self.seek(position)
                if state=='paused':self.toggle()

    def test_sound(self):
        """A brief, faded stereo tone checks output without reading music files."""
        from array import array
        import math
        self.ready()
        rate,size,channels=self.mixer.get_init()
        if size!=-16:raise RuntimeError('The test sound requires 16-bit audio. Reconnect the output and try again.')
        samples=array('h');count=int(rate*.6);fade=max(1,int(rate*.02))
        for index in range(count):
            level=min(1,index/fade,(count-index-1)/fade)
            value=int(6000*level*math.sin(2*math.pi*440*index/rate))
            samples.extend([value]*channels)
        if self.test_channel:self.test_channel.stop()
        self.test_clip=self.mixer.Sound(buffer=samples.tobytes())
        self.test_clip.set_volume(self.volume/100)
        self.test_channel=self.test_clip.play()
        if self.test_channel is None:raise RuntimeError('No audio channel is available for the test sound. Stop playback and try again.')

    @property
    def current(self):
        return self.playlist[self.index] if 0<=self.index<len(self.playlist) else None

    @property
    def duration(self):return float(self.current.get('duration',0)) if self.current else 0

    @property
    def position(self):
        if self.state=='finished':return self.duration
        if self.state=='paused':return self.paused_at
        if self.state!='playing':return 0
        pos=self.mixer.music.get_pos()
        return min(self.duration,max(0,self.offset+max(0,pos)/1000))

    def play(self,playlist=None,index=None):
        self.ready()
        if playlist is not None:
            self.playlist=list(playlist);self.index=0 if index is None else index
        elif index is not None:self.index=index
        if not self.current:return
        if Path(self.current['path']).suffix.lower()=='.cda':
            raise ValueError('CDA files are CD track references. Rip the CD to a real audio file before playback.')
        self.stop();self.loaded_path=None
        if self.compatibility or Path(self.current['path']).suffix.lower() not in {'.mp3','.flac'}:
            if self.decoder is None:
                from groove_decode import PlaybackDecoder
                self.decoder=PlaybackDecoder()
            self.future=self.decoder.request(self.current,output_format='wav' if self.compatibility else 'flac');self.state='buffering';return
        self.start_stream(self.current['path'])

    def start_stream(self,path):
        self.mixer.music.load(path);self.loaded_path=path
        self.mixer.music.set_volume(self.volume/100);self.mixer.music.play()
        self.mixer.music.set_volume(self.volume/100)
        self.offset=0;self.paused_at=0;self.state='playing'

    def toggle(self):
        if self.state=='buffering':return
        if self.state=='playing':
            self.paused_at=self.position;self.mixer.music.pause();self.state='paused'
        elif self.state=='paused':self.mixer.music.unpause();self.state='playing'
        else:self.play()

    def seek(self,seconds):
        if not self.current or self.state=='buffering':return
        seconds=max(0,min(float(seconds),max(0,self.duration-.01)))
        paused=self.state=='paused'
        self.ready()
        if self.state=='stopped' and not self.loaded_path and (self.compatibility or Path(self.current['path']).suffix.lower() not in {'.mp3','.flac'}):
            self.play();self.resume_position=seconds;return
        if self.state=='stopped':
            self.mixer.music.load(self.loaded_path or self.current['path']);self.mixer.music.set_volume(self.volume/100)
        self.mixer.music.play(start=seconds)
        self.offset=seconds;self.paused_at=seconds;self.state='playing'
        if paused:self.mixer.music.pause();self.state='paused'

    def set_volume(self,value):
        self.volume=max(0,min(100,float(value)))
        if self.mixer and self.mixer.get_init():self.mixer.music.set_volume(self.volume/100)
        if self.test_clip:self.test_clip.set_volume(self.volume/100)

    def previous(self):
        if not self.current:return
        self.play(index=self.index if self.position>3 else max(0,self.index-1))

    def next(self):
        if self.index+1<len(self.playlist):self.play(index=self.index+1)
        else:self.stop()

    def pump(self):
        if self.state=='buffering' and self.future and self.future.done():
            future=self.future;self.future=None
            try:
                path=future.result()
                from mutagen import File
                self.current['duration']=float(File(path).info.length)
                self.start_stream(path)
                position,paused=self.resume_position,self.resume_paused
                self.resume_position=0;self.resume_paused=False
                if position:self.seek(position)
                if paused:self.toggle()
            except Exception:
                self.stop();raise
        if self.state=='playing' and not self.mixer.music.get_busy():
            if self.index+1<len(self.playlist):self.play(index=self.index+1)
            else:self.state='finished'

    def stop(self):
        if self.decoder:self.decoder.stop()
        self.future=None
        self.resume_position=0;self.resume_paused=False
        if self.test_channel:self.test_channel.stop();self.test_channel=None
        self.test_clip=None
        if self.mixer and self.mixer.get_init():
            self.mixer.music.stop();self.mixer.music.unload()
        self.state='stopped';self.offset=0;self.paused_at=0

    def close(self):
        self.stop()
        if self.mixer and self.mixer.get_init():self.mixer.quit()
        if self.decoder:self.decoder.close()
