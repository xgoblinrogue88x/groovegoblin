"""Decode listening copies in a worker; never convert or write the source music."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time

PCM_FORMATS={'Signed 16-bit little-endian':'s16le','Signed 24-bit little-endian':'s24le',
             'Signed 32-bit little-endian':'s32le','Float 32-bit little-endian':'f32le',
             'Unsigned 8-bit':'u8','Signed 16-bit big-endian':'s16be','Float 32-bit big-endian':'f32be'}


class PlaybackDecoder:
    def __init__(self):
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='GroovePlayback')
        self.temporary=tempfile.TemporaryDirectory(prefix='GrooveGoblin_Playback_',ignore_cleanup_errors=True)
        self.cancel=None;self.future=None;self.closed=False;self.process=None;self.jobs=[]

    def request(self,record):
        self.stop();self.cancel=threading.Event()
        self.future=self.executor.submit(self.decode,dict(record),self.cancel)
        self.jobs=[job for job in self.jobs if not job.done()]+[self.future]
        return self.future

    def decode(self,record,cancel):
        import imageio_ffmpeg
        path=Path(record['path']);pcm=record.get('pcm')
        key=hashlib.sha256((str(path)+str(path.stat().st_size)+str(path.stat().st_mtime_ns)+str(pcm)).encode()).hexdigest()
        output=Path(self.temporary.name)/(key+'.flac')
        if output.is_file():return str(output)
        command=[imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-nostdin','-y']
        if path.suffix.lower()=='.pcm':
            if not pcm:raise ValueError('Select this raw PCM track and specify its sample format, rate and channels before playback.')
            if pcm.get('format') not in PCM_FORMATS.values() or not 8000<=int(pcm.get('rate',0))<=384000 or int(pcm.get('channels',0)) not in (1,2,4,6,8):
                raise ValueError('Invalid raw PCM playback settings.')
            command+=['-f',pcm['format'],'-ar',str(pcm['rate']),'-ac',str(pcm['channels'])]
        command+=['-i',str(path),'-map','0:a:0','-vn','-ar','48000','-ac','2','-sample_fmt','s16','-c:a','flac',str(output)]
        flags={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
        if cancel.is_set():raise RuntimeError('Playback preparation canceled.')
        process=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,**flags)
        self.process=process
        deadline=time.monotonic()+600
        try:
            while True:
                if cancel.is_set() or time.monotonic()>deadline:
                    process.terminate();process.communicate(timeout=5)
                    raise RuntimeError('Playback preparation canceled or timed out.')
                try:
                    _,error=process.communicate(timeout=.2);break
                except subprocess.TimeoutExpired:continue
            if process.returncode:
                raise ValueError('Unable to decode this audio file. It may be corrupt, encrypted or use an unsupported codec.\n'+error.decode(errors='replace')[-1800:])
            if cancel.is_set():raise RuntimeError('Playback preparation canceled.')
            # Bound the listening-copy cache; current music is unloaded before a new request.
            old=sorted(Path(self.temporary.name).glob('*.flac'),key=lambda p:p.stat().st_mtime,reverse=True)
            for item in old[4:]:item.unlink(missing_ok=True)
            return str(output)
        except Exception:
            if process.poll() is None:process.kill();process.communicate()
            output.unlink(missing_ok=True);raise
        finally:
            if self.process is process:self.process=None

    def stop(self):
        if self.cancel:self.cancel.set()
        if self.future:self.future.cancel()
        process=self.process
        if process and process.poll() is None:
            try:process.terminate()
            except OSError:pass

    def close(self):
        if self.closed:return
        self.closed=True;self.stop();self.executor.shutdown(wait=False,cancel_futures=True)
        pending=[job for job in self.jobs if not job.done()]
        def cleanup_when_done(f):
            if all(job.done() for job in self.jobs):self.temporary.cleanup()
        if pending:
            for job in pending:job.add_done_callback(cleanup_when_done)
        else:self.temporary.cleanup()
