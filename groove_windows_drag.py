"""Windows OLE file source. All COM work runs on a dedicated STA worker.

Shell supplies IDataObject (including Unicode file lists and Shell item IDs).
The small IDropSource callbacks below never access Tk. Explorer owns transfers,
collision dialogs and undo; this module never copies, deletes or renames music.
"""
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import os
import uuid
import struct

HRESULT=C.c_int32
DWORD=C.c_uint32
COPY,MOVE=1,2
DROP,CANCEL,DEFAULT_CURSORS=0x40100,0x40101,0x40102
S_OK=0
E_NOINTERFACE=C.c_int32(0x80004002).value


class GUID(C.Structure):
    _fields_=[('data',C.c_ubyte*16)]
    @classmethod
    def make(cls,value):return cls.from_buffer_copy(uuid.UUID(value).bytes_le)


IID_DATA=GUID.make('0000010e-0000-0000-c000-000000000046')
BHID_DATA=GUID.make('b8c0bd9f-ed24-455c-83e6-d5390c4fe8c4')
IID_UNKNOWN=GUID.make('00000000-0000-0000-c000-000000000046')
IID_SOURCE=GUID.make('00000121-0000-0000-c000-000000000046')
IID_ASYNC=GUID.make('3d8b0590-f691-11d2-8ea9-006097df5bd4')


class FormatEtc(C.Structure):
    _fields_=[('format',C.c_uint16),('target',C.c_void_p),('aspect',DWORD),('index',C.c_int32),('medium',DWORD)]


class StorageMedium(C.Structure):
    _fields_=[('medium',DWORD),('global_handle',C.c_void_p),('release',C.c_void_p)]


def method(pointer,index,result,*args):
    address=C.cast(pointer,C.POINTER(C.POINTER(C.c_void_p))).contents[index]
    return C.WINFUNCTYPE(result,C.c_void_p,*args)(address)


def release(pointer):
    if pointer:method(pointer,2,DWORD)(pointer)


def checked(result,operation):
    if result<0:raise OSError(f'{operation} failed (Windows 0x{result & 0xffffffff:08X}).')


class DropSource:
    def __init__(self,api,cancel):
        self.api=api;self.cancel=cancel;self.refs=1
        query=C.WINFUNCTYPE(HRESULT,C.c_void_p,C.POINTER(GUID),C.POINTER(C.c_void_p))
        reference=C.WINFUNCTYPE(DWORD,C.c_void_p)
        continuing=C.WINFUNCTYPE(HRESULT,C.c_void_p,W.BOOL,DWORD)
        feedback=C.WINFUNCTYPE(HRESULT,C.c_void_p,DWORD)
        def query_interface(this,iid,out):
            out[0]=None
            if bytes(iid.contents) in (bytes(IID_UNKNOWN),bytes(IID_SOURCE)):
                out[0]=this;self.refs+=1;return S_OK
            return E_NOINTERFACE
        def add_ref(this):self.refs+=1;return self.refs
        def release_ref(this):self.refs=max(0,self.refs-1);return self.refs
        def keep_dragging(this,escape,keys):
            # Async state is shared across threads; Tk received the initial
            # mouse-down, whereas this STA owns the OLE tracking loop.
            if escape or self.cancel.is_set() or api.user.GetAsyncKeyState(0x1b)&0x8000:return CANCEL
            if not api.user.GetAsyncKeyState(1)&0x8000:
                return CANCEL if api.over_our_process() else DROP
            return S_OK
        self.callbacks=(query(query_interface),reference(add_ref),reference(release_ref),
                        continuing(keep_dragging),feedback(lambda this,effect:DEFAULT_CURSORS))
        self.table=(C.c_void_p*5)(*[C.cast(callback,C.c_void_p).value for callback in self.callbacks])
        self.instance=(C.c_void_p*1)(C.cast(self.table,C.c_void_p).value)
        self.pointer=C.cast(self.instance,C.c_void_p)


class WindowsFileDrag:
    def __init__(self,gui_thread=None):
        self.gui_thread=gui_thread
        self.ole=C.WinDLL('ole32',use_last_error=True)
        self.shell=C.WinDLL('shell32',use_last_error=True)
        self.kernel=C.WinDLL('kernel32',use_last_error=True)
        self.user=C.WinDLL('user32',use_last_error=True)
        def bind(lib,name,result,args):
            function=getattr(lib,name);function.restype=result;function.argtypes=args
        bind(self.ole,'OleInitialize',HRESULT,[C.c_void_p])
        bind(self.ole,'OleUninitialize',None,[])
        bind(self.ole,'CoTaskMemFree',None,[C.c_void_p])
        bind(self.ole,'ReleaseStgMedium',None,[C.POINTER(StorageMedium)])
        bind(self.ole,'DoDragDrop',HRESULT,[C.c_void_p,C.c_void_p,DWORD,C.POINTER(DWORD)])
        bind(self.shell,'SHParseDisplayName',HRESULT,[W.LPCWSTR,C.c_void_p,C.POINTER(C.c_void_p),DWORD,C.c_void_p])
        bind(self.shell,'SHCreateShellItemArrayFromIDLists',HRESULT,[DWORD,C.POINTER(C.c_void_p),C.POINTER(C.c_void_p)])
        bind(self.kernel,'CreateFileW',W.HANDLE,[W.LPCWSTR,DWORD,DWORD,C.c_void_p,DWORD,DWORD,W.HANDLE])
        bind(self.kernel,'CloseHandle',W.BOOL,[W.HANDLE])
        bind(self.kernel,'GetCurrentThreadId',DWORD,[])
        bind(self.kernel,'GetFileInformationByHandle',W.BOOL,[W.HANDLE,C.c_void_p])
        bind(self.kernel,'GetFinalPathNameByHandleW',DWORD,[W.HANDLE,W.LPWSTR,DWORD,DWORD])
        bind(self.kernel,'GlobalAlloc',W.HGLOBAL,[W.UINT,C.c_size_t])
        bind(self.kernel,'GlobalLock',C.c_void_p,[W.HGLOBAL])
        bind(self.kernel,'GlobalUnlock',W.BOOL,[W.HGLOBAL])
        bind(self.user,'RegisterClipboardFormatW',W.UINT,[W.LPCWSTR])
        bind(self.user,'GetAsyncKeyState',C.c_short,[C.c_int])
        bind(self.user,'GetCursorPos',W.BOOL,[C.POINTER(W.POINT)])
        bind(self.user,'WindowFromPoint',W.HWND,[W.POINT])
        bind(self.user,'GetWindowThreadProcessId',DWORD,[W.HWND,C.POINTER(DWORD)])
        bind(self.user,'AttachThreadInput',W.BOOL,[DWORD,DWORD,W.BOOL])
        bind(self.user,'PeekMessageW',W.BOOL,[C.POINTER(W.MSG),W.HWND,W.UINT,W.UINT,W.UINT])

    def over_our_process(self):
        point=W.POINT();pid=DWORD()
        if not self.user.GetCursorPos(C.byref(point)):return True
        window=self.user.WindowFromPoint(point)
        self.user.GetWindowThreadProcessId(window,C.byref(pid))
        return pid.value==os.getpid()

    def data_object(self,paths):
        pidls=[];items=C.c_void_p();data=C.c_void_p()
        try:
            for path in paths:
                pidl=C.c_void_p()
                checked(self.shell.SHParseDisplayName(path,None,C.byref(pidl),0,None),'Reading file for drag')
                pidls.append(pidl)
            pointers=(C.c_void_p*len(pidls))(*[p.value for p in pidls])
            checked(self.shell.SHCreateShellItemArrayFromIDLists(len(pidls),pointers,C.byref(items)),'Creating Shell file list')
            checked(method(items,3,HRESULT,C.c_void_p,C.POINTER(GUID),C.POINTER(GUID),C.POINTER(C.c_void_p))(
                items,None,C.byref(BHID_DATA),C.byref(IID_DATA),C.byref(data)),'Creating Windows file drag')
            return data
        finally:
            release(items)
            for pidl in pidls:self.ole.CoTaskMemFree(pidl)

    def prefer_move(self,data):
        asynchronous=C.c_void_p()
        result=method(data,0,HRESULT,C.POINTER(GUID),C.POINTER(C.c_void_p))(
            data,C.byref(IID_ASYNC),C.byref(asynchronous))
        if result>=0 and asynchronous:
            try:checked(method(asynchronous,3,HRESULT,W.BOOL)(asynchronous,False),'Setting synchronous file transfer')
            finally:release(asynchronous)
        format_id=self.user.RegisterClipboardFormatW('Preferred DropEffect')
        if not format_id:raise C.WinError(C.get_last_error())
        handle=self.kernel.GlobalAlloc(0x42,4)
        if not handle:raise C.WinError(C.get_last_error())
        medium=StorageMedium(1,handle,None)
        try:
            pointer=self.kernel.GlobalLock(handle)
            if not pointer:raise C.WinError(C.get_last_error())
            try:C.cast(pointer,C.POINTER(DWORD))[0]=MOVE
            finally:self.kernel.GlobalUnlock(handle)
            fmt=FormatEtc(format_id,None,1,-1,1)
            checked(method(data,7,HRESULT,C.POINTER(FormatEtc),C.POINTER(StorageMedium),W.BOOL)(
                data,C.byref(fmt),C.byref(medium),True),'Setting drag preference')
            # SetData accepted ownership of the HGLOBAL.
            medium.global_handle=None
        finally:
            if medium.global_handle:self.ole.ReleaseStgMedium(C.byref(medium))

    def follow_handle(self,handle):
        size=self.kernel.GetFinalPathNameByHandleW(handle,None,0,0)
        if not size:return None
        buffer=C.create_unicode_buffer(size+1)
        if not self.kernel.GetFinalPathNameByHandleW(handle,buffer,len(buffer),0):return None
        name=buffer.value
        if name.startswith('\\\\?\\UNC\\'):name='\\\\'+name[8:]
        elif name.startswith('\\\\?\\'):name=name[4:]
        if not Path(name).is_file():return None
        # Do not mistake a replacement at the old pathname for the dragged file.
        candidate=self.kernel.CreateFileW(name,0x80,7,None,3,0,None)
        if candidate in (None,C.c_void_p(-1).value):return None
        try:
            identities=[]
            for file in (handle,candidate):
                info=C.create_string_buffer(52)
                if not self.kernel.GetFileInformationByHandle(file,info):return None
                words=struct.unpack('<13I',info.raw)
                if not (words[11] or words[12]):return None
                identities.append((words[7],words[11],words[12]))
            return str(Path(name).resolve()) if identities[0]==identities[1] else None
        finally:self.kernel.CloseHandle(candidate)

    def _do_drag_drop(self,data,source,effect):
        return self.ole.DoDragDrop(data,source,COPY|MOVE,effect)

    def drag(self,paths,cancel):
        # OLE needs input events to enter its tracking loop. A request canceled
        # before that loop starts must return without waiting for mouse input.
        if cancel.is_set():
            return {'canceled':True,'effect':0,'locations':{},'error':''}
        initialized=False;attached=False;handles={};data=C.c_void_p()
        worker=self.kernel.GetCurrentThreadId()
        try:
            checked(self.ole.OleInitialize(None),'Starting Windows drag');initialized=True
            if self.gui_thread and self.gui_thread!=worker:
                message=W.MSG();self.user.PeekMessageW(C.byref(message),None,0,0,0)
                if not self.user.AttachThreadInput(worker,self.gui_thread,True):raise C.WinError(C.get_last_error())
                attached=True
            for path in paths:
                # Share DELETE so Explorer can rename/move the file while the
                # handle lets us follow a same-volume move to its new folder.
                handle=self.kernel.CreateFileW(path,0x80,7,None,3,0,None)
                if handle in (None,C.c_void_p(-1).value):raise C.WinError(C.get_last_error())
                handles[path]=handle
            data=self.data_object(paths);self.prefer_move(data)
            source=DropSource(self,cancel);effect=DWORD()
            result=self._do_drag_drop(data,source.pointer,C.byref(effect))
            locations={path:self.follow_handle(handle) for path,handle in handles.items()}
            return {'canceled':result==CANCEL,'effect':effect.value,'locations':locations,
                    'error':f'Windows drag failed (0x{result & 0xffffffff:08X}).' if result<0 else ''}
        finally:
            release(data)
            for handle in handles.values():self.kernel.CloseHandle(handle)
            if initialized:self.ole.OleUninitialize()
            if attached:self.user.AttachThreadInput(worker,self.gui_thread,False)
