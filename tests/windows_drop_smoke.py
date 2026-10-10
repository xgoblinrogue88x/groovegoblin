"""Run in a child process on Windows to catch fatal Tk/native drop regressions."""
import ctypes
from ctypes import wintypes
import importlib.machinery
from pathlib import Path
import struct
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
module=importlib.machinery.SourceFileLoader('groove_windows_smoke',str(ROOT/'GrooveGoblin.pyw')).load_module()

with tempfile.TemporaryDirectory() as temporary:
    folder=Path(temporary)/'Album {Björk Live}';folder.mkdir()
    media=Path(temporary)/'Song.MP3';media.write_bytes(b'read-only drop fixture')
    app=module.GrooveGoblin()
    failures=[]
    scans=[]
    app.scan=lambda:scans.append(list(app.roots))
    def send_drop():
        try:
            assert app._folder_drop is not None
            payload=struct.pack('<IiiII',20,0,0,0,1)
            payload+=(str(folder)+'\0'+str(media)+'\0\0').encode('utf-16-le')
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            user=ctypes.WinDLL('user32',use_last_error=True)
            kernel.GlobalAlloc.argtypes=[wintypes.UINT,ctypes.c_size_t]
            kernel.GlobalAlloc.restype=wintypes.HANDLE
            kernel.GlobalLock.argtypes=[wintypes.HANDLE];kernel.GlobalLock.restype=ctypes.c_void_p
            kernel.GlobalUnlock.argtypes=[wintypes.HANDLE];kernel.GlobalUnlock.restype=wintypes.BOOL
            kernel.GlobalFree.argtypes=[wintypes.HANDLE];kernel.GlobalFree.restype=wintypes.HANDLE
            user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
            user.PostMessageW.restype=wintypes.BOOL
            handle=kernel.GlobalAlloc(0x42,len(payload))
            if not handle:raise ctypes.WinError(ctypes.get_last_error())
            address=kernel.GlobalLock(handle)
            if not address:
                kernel.GlobalFree(handle);raise ctypes.WinError(ctypes.get_last_error())
            ctypes.memmove(address,payload,len(payload));kernel.GlobalUnlock(handle)
            if not user.PostMessageW(app.album_entry.winfo_id(),0x0233,handle,0):
                kernel.GlobalFree(handle);raise ctypes.WinError(ctypes.get_last_error())
        except Exception as error:
            failures.append(repr(error))
    def verify():
        try:
            assert app.roots==[str(folder.resolve()),str(media.resolve())],app.roots
            assert media.read_bytes()==b'read-only drop fixture'
            assert scans==[app.roots],scans
            assert not app.worker_busy
            assert not app.matched
        except Exception as error:
            failures.append(repr(error))
        finally:
            app.destroy()
    app.after(150,send_drop)
    app.after(1500,verify)
    app.mainloop()
    if failures:raise AssertionError(failures)
print('Windows drop smoke passed')
