"""Separate-process OLE receiver delegating to a real Shell folder target."""
import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import sys
import faulthandler
faulthandler.enable();faulthandler.dump_traceback_later(45)
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from groove_windows_drag import WindowsFileDrag,GUID,HRESULT,DWORD,IID_UNKNOWN,E_NOINTERFACE,checked
from windows_drag_support import ShellFolderTarget,Point,IID_TARGET,dropped_paths

folder=Path(sys.argv[1]);report=Path(sys.argv[2]);api=WindowsFileDrag();user=api.user
user.CreateWindowExW.argtypes=[DWORD,W.LPCWSTR,W.LPCWSTR,DWORD,C.c_int,C.c_int,C.c_int,C.c_int,W.HWND,W.HMENU,W.HINSTANCE,C.c_void_p]
user.CreateWindowExW.restype=W.HWND
user.GetSystemMetrics.argtypes=[C.c_int];user.GetSystemMetrics.restype=C.c_int
user.GetMessageW.argtypes=[C.POINTER(W.MSG),W.HWND,W.UINT,W.UINT];user.GetMessageW.restype=W.BOOL
user.TranslateMessage.argtypes=[C.POINTER(W.MSG)];user.DispatchMessageW.argtypes=[C.POINTER(W.MSG)];user.DispatchMessageW.restype=C.c_ssize_t
user.PostQuitMessage.argtypes=[C.c_int];user.DestroyWindow.argtypes=[W.HWND]
api.ole.RegisterDragDrop.argtypes=[W.HWND,C.c_void_p];api.ole.RegisterDragDrop.restype=HRESULT
api.ole.RevokeDragDrop.argtypes=[W.HWND];api.ole.RevokeDragDrop.restype=HRESULT
checked(api.ole.OleInitialize(None),'Receiver OLE initialization')
width=user.GetSystemMetrics(0);left=max(500,width-260)
window=user.CreateWindowExW(8,'STATIC','Groove Goblin disposable drag target',0x10cf0000,left,100,240,300,None,None,None,None)
if not window:raise C.WinError(C.get_last_error())
target=ShellFolderTarget(api,folder)


class Receiver:
    def __init__(self):
        self.refs=1
        def query(this,iid,out):
            out[0]=None
            if bytes(iid.contents) in (bytes(IID_UNKNOWN),bytes(IID_TARGET)):
                out[0]=this;self.refs+=1;return 0
            return E_NOINTERFACE
        def add(this):self.refs+=1;return self.refs
        def remove(this):self.refs=max(0,self.refs-1);return self.refs
        def enter(this,data,keys,point,effect):return target.enter(data,keys,point,effect)
        def over(this,keys,point,effect):return target.over(keys,point,effect)
        def leave(this):return target.leave()
        def drop(this,data,keys,point,effect):
            try:
                paths=dropped_paths(api,data)
                result=target.drop(data,keys,point,effect)
                report.write_text(json.dumps({'paths':paths,'result':result,'effect':effect[0]}),encoding='utf-8')
                return result
            except Exception as error:
                report.write_text(json.dumps({'error':str(error)}),encoding='utf-8')
                return C.c_int32(0x80004005).value
            finally:user.PostQuitMessage(0)
        self.callbacks=(C.WINFUNCTYPE(HRESULT,C.c_void_p,C.POINTER(GUID),C.POINTER(C.c_void_p))(query),
            C.WINFUNCTYPE(DWORD,C.c_void_p)(add),C.WINFUNCTYPE(DWORD,C.c_void_p)(remove),
            C.WINFUNCTYPE(HRESULT,C.c_void_p,C.c_void_p,DWORD,Point,C.POINTER(DWORD))(enter),
            C.WINFUNCTYPE(HRESULT,C.c_void_p,DWORD,Point,C.POINTER(DWORD))(over),
            C.WINFUNCTYPE(HRESULT,C.c_void_p)(leave),
            C.WINFUNCTYPE(HRESULT,C.c_void_p,C.c_void_p,DWORD,Point,C.POINTER(DWORD))(drop))
        self.table=(C.c_void_p*7)(*[C.cast(callback,C.c_void_p).value for callback in self.callbacks])
        self.instance=(C.c_void_p*1)(C.cast(self.table,C.c_void_p).value)
        self.pointer=C.cast(self.instance,C.c_void_p)


receiver=Receiver()
checked(api.ole.RegisterDragDrop(window,receiver.pointer),'Registering receiver')
report.with_suffix('.ready').write_text(json.dumps({'x':left+100,'y':220}),encoding='utf-8')
try:
    message=W.MSG()
    while user.GetMessageW(C.byref(message),None,0,0)>0:
        user.TranslateMessage(C.byref(message));user.DispatchMessageW(C.byref(message))
finally:
    api.ole.RevokeDragDrop(window);target.close();user.DestroyWindow(window);api.ole.OleUninitialize()
