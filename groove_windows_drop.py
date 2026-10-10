"""Collect Explorer drops without replacing Tk's window procedure.

The native hook never calls Tk or forwards messages into Tk. A Tk timer drains
plain Python data after the native callback returns to the Windows message loop.
"""
import ctypes
from ctypes import wintypes
from collections import deque

WM_DROPFILES = 0x0233
WM_NULL = 0
WH_GETMESSAGE = 3
PM_REMOVE = 1


class WindowsDropAPI:
    def __init__(self):
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.shell = ctypes.WinDLL('shell32', use_last_error=True)
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        result = ctypes.c_ssize_t
        self.proc_type = ctypes.WINFUNCTYPE(result, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
        self.user.SetWindowsHookExW.argtypes = [ctypes.c_int, self.proc_type,
                                               wintypes.HINSTANCE, wintypes.DWORD]
        self.user.SetWindowsHookExW.restype = wintypes.HANDLE
        self.user.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
        self.user.UnhookWindowsHookEx.restype = wintypes.BOOL
        self.user.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                            wintypes.WPARAM, wintypes.LPARAM]
        self.user.CallNextHookEx.restype = result
        self.kernel.GetCurrentThreadId.argtypes = []
        self.kernel.GetCurrentThreadId.restype = wintypes.DWORD
        self.user.GetParent.argtypes = [wintypes.HWND]
        self.user.GetParent.restype = wintypes.HWND
        self.user.IsWindow.argtypes = [wintypes.HWND]
        self.user.IsWindow.restype = wintypes.BOOL
        self.shell.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
        self.shell.DragAcceptFiles.restype = None
        self.shell.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT,
                                             wintypes.LPWSTR, wintypes.UINT]
        self.shell.DragQueryFileW.restype = wintypes.UINT
        self.shell.DragFinish.argtypes = [wintypes.HANDLE]
        self.shell.DragFinish.restype = None

    def make_proc(self, handler):
        return self.proc_type(handler)

    def install_hook(self, proc):
        hook = self.user.SetWindowsHookExW(WH_GETMESSAGE, proc, None,
                                          self.kernel.GetCurrentThreadId())
        if not hook:
            raise ctypes.WinError(ctypes.get_last_error())
        return hook

    def remove_hook(self, hook):
        if not self.user.UnhookWindowsHookEx(hook):
            raise ctypes.WinError(ctypes.get_last_error())

    def next_hook(self, hook, code, wparam, lparam):
        return self.user.CallNextHookEx(hook, code, wparam, lparam)

    def message(self, address):
        return ctypes.cast(address, ctypes.POINTER(wintypes.MSG)).contents

    def parent(self, hwnd):
        return self.user.GetParent(hwnd)

    def exists(self, hwnd):
        return self.user.IsWindow(hwnd)

    def accept(self, hwnd, enabled):
        self.shell.DragAcceptFiles(hwnd, enabled)

    def paths(self, drop):
        count = self.shell.DragQueryFileW(drop, 0xFFFFFFFF, None, 0)
        paths = []
        for index in range(count):
            size = self.shell.DragQueryFileW(drop, index, None, 0)
            buffer = ctypes.create_unicode_buffer(size + 1)
            self.shell.DragQueryFileW(drop, index, buffer, size + 1)
            paths.append(buffer.value)
        return paths

    def finish(self, drop):
        self.shell.DragFinish(drop)


class NativeFolderDrop:
    def __init__(self, app, on_drop, api=None):
        self.app = app
        self.on_drop = on_drop
        self.api = api or WindowsDropAPI()
        self.pending = deque()
        self.hook = None
        self.timer = None
        self.closed = False
        self.handles = set()
        # Keep the callback alive until the hook is removed.
        self.proc = self.api.make_proc(self.handle_message)
        app.update_idletasks()
        def collect(widget):
            self.handles.add(widget.winfo_id())
            for child in widget.winfo_children():
                collect(child)
        collect(app)
        parent = self.api.parent(app.winfo_id())
        if parent:
            self.handles.add(parent)
        try:
            self.hook = self.api.install_hook(self.proc)
            for hwnd in self.handles:
                self.api.accept(hwnd, True)
            self.timer = app.after(50, self.drain)
        except Exception:
            self.close()
            raise

    def handle_message(self, code, wparam, lparam):
        # Windows can first peek at a message without removing it. Consume only
        # PM_REMOVE, once. Never invoke ANY app/Tk method in this native callback.
        if code >= 0 and wparam == PM_REMOVE:
            message = self.api.message(lparam)
            if message.message == WM_DROPFILES and message.hWnd in self.handles:
                drop = message.wParam
                message.message = WM_NULL
                message.wParam = message.lParam = 0
                try:
                    self.pending.append(('paths', self.api.paths(drop)))
                except Exception as error:
                    self.pending.append(('error', str(error)))
                finally:
                    self.api.finish(drop)
        return self.api.next_hook(self.hook, code, wparam, lparam)

    def drain(self):
        self.timer = None
        if self.closed:
            return
        while self.pending:
            kind, value = self.pending.popleft()
            if kind == 'error':
                self.app.log('Could not read dropped items: ' + value)
                self.app.status.set('Could not read this drop. Use Add Folders or Add Files.')
            else:
                try:
                    self.on_drop(value)
                except Exception as error:
                    self.app.report_callback_exception(type(error), error, error.__traceback__)
        self.timer = self.app.after(50, self.drain)

    def close(self):
        if self.closed:
            return
        if self.hook is not None:
            self.api.remove_hook(self.hook)
            self.hook = None
        self.closed = True
        if self.timer is not None:
            self.app.after_cancel(self.timer)
            self.timer = None
        for hwnd in self.handles:
            if self.api.exists(hwnd):
                self.api.accept(hwnd, False)
        self.pending.clear()
