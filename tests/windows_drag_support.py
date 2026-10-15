"""Real Shell folder target used only with disposable files in Windows tests."""
import ctypes as C
from ctypes import wintypes as W
from groove_windows_drag import GUID,FormatEtc,StorageMedium,HRESULT,DWORD,method,release,checked

IID_FOLDER=GUID.make('000214e6-0000-0000-c000-000000000046')
IID_TARGET=GUID.make('00000122-0000-0000-c000-000000000046')


class Point(C.Structure):
    _fields_=[('x',C.c_int32),('y',C.c_int32)]


class ShellFolderTarget:
    def __init__(self,api,folder):
        self.api=api;self.target=C.c_void_p();parent=C.c_void_p();pidl=C.c_void_p();child=C.c_void_p()
        api.shell.SHBindToParent.argtypes=[C.c_void_p,C.POINTER(GUID),C.POINTER(C.c_void_p),C.POINTER(C.c_void_p)]
        api.shell.SHBindToParent.restype=HRESULT
        try:
            checked(api.shell.SHParseDisplayName(str(folder),None,C.byref(pidl),0,None),'Reading destination folder')
            checked(api.shell.SHBindToParent(pidl,C.byref(IID_FOLDER),C.byref(parent),C.byref(child)),'Binding destination parent')
            children=(C.c_void_p*1)(child.value)
            checked(method(parent,10,HRESULT,W.HWND,W.UINT,C.POINTER(C.c_void_p),C.POINTER(GUID),C.c_void_p,C.POINTER(C.c_void_p))(
                parent,None,1,children,C.byref(IID_TARGET),None,C.byref(self.target)),'Creating Shell folder drop target')
        finally:
            release(parent)
            if pidl:api.ole.CoTaskMemFree(pidl)

    def enter(self,data,keys,point,effect):
        return method(self.target,3,HRESULT,C.c_void_p,DWORD,Point,C.POINTER(DWORD))(self.target,data,keys,point,effect)

    def over(self,keys,point,effect):
        return method(self.target,4,HRESULT,DWORD,Point,C.POINTER(DWORD))(self.target,keys,point,effect)

    def leave(self):return method(self.target,5,HRESULT)(self.target)

    def drop(self,data,keys,point,effect):
        return method(self.target,6,HRESULT,C.c_void_p,DWORD,Point,C.POINTER(DWORD))(self.target,data,keys,point,effect)

    def close(self):release(self.target);self.target=C.c_void_p()


def dropped_paths(api,data):
    fmt=FormatEtc(15,None,1,-1,1);medium=StorageMedium()
    checked(method(data,3,HRESULT,C.POINTER(FormatEtc),C.POINTER(StorageMedium))(
        data,C.byref(fmt),C.byref(medium)),'Reading native Unicode file list')
    api.shell.DragQueryFileW.argtypes=[W.HANDLE,W.UINT,W.LPWSTR,W.UINT]
    api.shell.DragQueryFileW.restype=W.UINT
    try:
        paths=[];count=api.shell.DragQueryFileW(medium.global_handle,0xffffffff,None,0)
        for index in range(count):
            length=api.shell.DragQueryFileW(medium.global_handle,index,None,0)
            buffer=C.create_unicode_buffer(length+1)
            api.shell.DragQueryFileW(medium.global_handle,index,buffer,len(buffer));paths.append(buffer.value)
        return paths
    finally:api.ole.ReleaseStgMedium(C.byref(medium))
