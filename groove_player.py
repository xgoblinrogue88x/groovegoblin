"""Streamed playback with background decoding for additional formats; all commands are called from Tk's UI thread."""
import os
from pathlib import Path
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')


class MusicPlayer:
    def __init__(self,mixer=None):
        self.mixer=mixer;self.playlist=[];self.index=-1;self.state='stopped'
        self.volume=70;self.offset=0;self.paused_at=0;self.decoder=None;self.future=None;self.loaded_path=None

    def ready(self):
        if self.mixer is None:
            try:
                import pygame
                self.mixer=pygame.mixer
            except ImportError as error:raise RuntimeError('Playback needs pygame-ce. Start the program using START_GROOVE_GOBLIN.bat to install it.') from error
        if not self.mixer.get_init():self.mixer.init()

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
        if Path(self.current['path']).suffix.lower() not in {'.mp3','.flac'}:
            if self.decoder is None:
                from groove_decode import PlaybackDecoder
                self.decoder=PlaybackDecoder()
            self.future=self.decoder.request(self.current);self.state='buffering';return
        self.start_stream(self.current['path'])

    def start_stream(self,path):
        self.mixer.music.load(path);self.loaded_path=path
        self.mixer.music.set_volume(self.volume/100);self.mixer.music.play()
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
        if self.state=='stopped' and not self.loaded_path and Path(self.current['path']).suffix.lower() not in {'.mp3','.flac'}:
            self.play();return
        if self.state=='stopped':
            self.mixer.music.load(self.loaded_path or self.current['path']);self.mixer.music.set_volume(self.volume/100)
        self.mixer.music.play(start=seconds)
        self.offset=seconds;self.paused_at=seconds;self.state='playing'
        if paused:self.mixer.music.pause();self.state='paused'

    def set_volume(self,value):
        self.volume=max(0,min(100,float(value)))
        if self.mixer and self.mixer.get_init():self.mixer.music.set_volume(self.volume/100)

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
                from mutagen.flac import FLAC
                self.current['duration']=float(FLAC(path).info.length)
                self.start_stream(path)
            except Exception:
                self.stop();raise
        if self.state=='playing' and not self.mixer.music.get_busy():
            if self.index+1<len(self.playlist):self.play(index=self.index+1)
            else:self.state='finished'

    def stop(self):
        if self.decoder:self.decoder.stop()
        self.future=None
        if self.mixer and self.mixer.get_init():
            self.mixer.music.stop();self.mixer.music.unload()
        self.state='stopped';self.offset=0;self.paused_at=0

    def close(self):
        self.stop()
        if self.mixer and self.mixer.get_init():self.mixer.quit()
        if self.decoder:self.decoder.close()
