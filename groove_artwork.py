"""Load cover pictures in background workers; never upload or write music."""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
import queue
import warnings
import urllib.request
import urllib.parse
import uuid

from PIL import Image, ImageOps, ImageTk
from mutagen.flac import FLAC
from mutagen.id3 import ID3

from groove_version import __version__

MAX_COVER_BYTES = 20 * 1024 * 1024


def read_cover(album):
    """Prefer embedded front cover, then a conventional adjacent cover file."""
    data = None
    for track in album.tracks[:3]:
        try:
            pictures = FLAC(track.path).pictures if track.fmt == '.flac' else ID3(track.path).getall('APIC')
            pictures = sorted(pictures, key=lambda p: p.type != 3)
            if pictures and len(pictures[0].data) <= MAX_COVER_BYTES:
                data = pictures[0].data
                break
        except Exception:
            continue
    if data is None:
        for name in ('cover.jpg', 'folder.jpg', 'front.jpg', 'cover.png', 'folder.png'):
            p = Path(album.folder) / name
            try:
                if p.is_file() and p.stat().st_size <= MAX_COVER_BYTES:
                    data = p.read_bytes()
                    break
            except OSError:
                continue
    if data is None:
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                source.thumbnail((600, 600), Image.Resampling.LANCZOS)
                return source.convert('RGB').copy()
    except (OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        return None


class HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme != 'https':
            raise ValueError('Artwork redirect must remain HTTPS')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def read_online_cover(mbid):
    """Fetch only a search result's public cover ID; no audio or paths."""
    try:
        identity=str(uuid.UUID(str(mbid)))
        request=urllib.request.Request('https://coverartarchive.org/release-group/'+identity+'/front-250',
                                       headers={'User-Agent':f'GrooveGoblin/{__version__} (desktop music organizer)'})
        opener=urllib.request.build_opener(HTTPSRedirect())
        with opener.open(request,timeout=12) as response:
            if urllib.parse.urlsplit(response.geturl()).scheme!='https':return None
            data=response.read(MAX_COVER_BYTES+1)
        if len(data)>MAX_COVER_BYTES:return None
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                source.thumbnail((600,600),Image.Resampling.LANCZOS)
                return source.convert('RGB').copy()
    except Exception:
        return None


class CoverCache:
    def __init__(self, app):
        self.app = app
        self.images = OrderedDict()
        self.photos = OrderedDict()
        self.pending = set()
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='groove-cover')
        self.queue = queue.Queue()
        self.timer = app.after(100, self.poll)
        app.bind('<Destroy>', self.close, add='+')

    def close(self, event):
        if event.widget is not self.app:
            return
        try:self.app.after_cancel(self.timer)
        except Exception:pass
        self.pool.shutdown(wait=False, cancel_futures=True)

    def request(self, uid, size):
        album = self.app.album_map.get(uid)
        if not album:return None
        key = (album.folder, tuple((t.path, tuple(t.signature)) for t in album.tracks[:3]))
        return self.resolve(key,size,lambda:read_cover(album))

    def request_result(self,mbid,size):
        try:identity=str(uuid.UUID(str(mbid)))
        except (ValueError,AttributeError):return None
        return self.resolve(('online',identity),size,lambda:read_online_cover(identity))

    def resolve(self,key,size,loader):
        if key not in self.images:
            if key not in self.pending:
                self.pending.add(key)
                future = self.pool.submit(loader)
                future.add_done_callback(lambda f: self.queue.put((key, f.result() if not f.cancelled() else None)))
            return None
        if self.images[key] is None:return None
        self.images.move_to_end(key)
        photo_key = (key, size)
        if photo_key not in self.photos:
            img = ImageOps.contain(self.images[key], (size, size), Image.Resampling.LANCZOS)
            bg = Image.new('RGB', (size, size), '#080e12')
            bg.paste(img, ((size-img.width)//2, (size-img.height)//2))
            self.photos[photo_key] = ImageTk.PhotoImage(bg, master=self.app)
            while len(self.photos)>320:self.photos.popitem(last=False)
        return self.photos[photo_key]

    def poll(self):
        changed=False
        try:
            while True:
                key, image = self.queue.get_nowait()
                self.pending.discard(key);self.images[key]=image;changed=True
                while len(self.images)>160:
                    stale,_=self.images.popitem(last=False)
                    for photo_key in [k for k in self.photos if k[0]==stale]:self.photos.pop(photo_key,None)
        except queue.Empty:
            pass
        if changed:
            self.app.albums_tree.schedule()
            self.app.results_tree.schedule()
            self.app.update_cover()
        self.timer=self.app.after(100,self.poll)
