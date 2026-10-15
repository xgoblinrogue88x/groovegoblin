"""Exercise native Shell data, real file moves/copies and the OLE cancel loop."""
import ctypes as C
import hashlib
from pathlib import Path
import sys
import tempfile
import threading
import faulthandler
faulthandler.enable();faulthandler.dump_traceback_later(40)
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from groove_windows_drag import WindowsFileDrag,DWORD,DROP,checked
from windows_drag_support import ShellFolderTarget,Point,dropped_paths


class FolderDrag(WindowsFileDrag):
    def __init__(self,folder,effect):super().__init__();self.folder=folder;self.effect=effect
    def _do_drag_drop(self,data,source,effect):
        self.paths=dropped_paths(self,data)
        target=ShellFolderTarget(self,self.folder)
        keys=4 if self.effect==2 else 8
        C.cast(effect,C.POINTER(DWORD))[0]=self.effect
        try:
            checked(target.enter(data,keys,Point(),effect),'Shell DragEnter')
            checked(target.drop(data,keys,Point(),effect),'Shell Drop')
            return DROP
        finally:target.close()


with tempfile.TemporaryDirectory() as temporary:
    root=Path(temporary).resolve();paths=[]
    for name in ('Disc 1/One {Björk}.mp3','Disc 2/Two 日本語.flac'):
        p=root/name;p.parent.mkdir();p.write_bytes((name*20).encode());paths.append(str(p))
    before={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
    copied=root/'Copied';copied.mkdir();api=FolderDrag(copied,1)
    result=api.drag(paths,threading.Event())
    assert {Path(p).resolve() for p in api.paths}=={Path(p).resolve() for p in paths} and not result['error'],result
    for p in paths:
        assert Path(p).is_file()
        assert hashlib.sha256((copied/Path(p).name).read_bytes()).hexdigest()==before[p]
    moved=root/'Moved';moved.mkdir();api=FolderDrag(moved,2)
    result=api.drag(paths,threading.Event())
    assert not result['error'],result
    for p in paths:
        target=moved/Path(p).name
        assert target.is_file() and not Path(p).exists(),(p,result)
        assert hashlib.sha256(target.read_bytes()).hexdigest()==before[p]
        assert result['locations'][p]==str(target),(result,str(target))
    cancel=threading.Event();cancel.set()
    result=WindowsFileDrag().drag([str(p) for p in moved.iterdir()],cancel)
    assert result['canceled'] and all(p.is_file() for p in moved.iterdir()),result
print('Native Shell drag copy, move, Unicode paths, handle following and OLE cancellation passed',flush=True)
