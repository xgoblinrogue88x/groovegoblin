"""Accept WM_DROPFILES on the main Tk window and its existing child windows.

No Tk extension, shell command, file move or external package is involved.
"""
import ctypes
from ctypes import wintypes

WM_DROPFILES = 0x0233
WM_NCDESTROY = 0x0082
GWLP_WNDPROC = -4


class WindowsDropAPI:
    def __init__(self):
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.shell = ctypes.WinDLL('shell32', use_last_error=True)
        result = ctypes.c_ssize_t
        self.proc_type = ctypes.WINFUNCTYPE(result, wintypes.HWND, wintypes.UINT,
                                           wintypes.WPARAM, wintypes.LPARAM)
        name = 'SetWindowLongPtrW' if ctypes.sizeof(ctypes.c_void_p) == 8 else 'SetWindowLongW'
        self.set_window = getattr(self.user, name)
        self.set_window.argtypes = [wintypes.HWND, ctypes.c_int, result]
        self.set_window.restype = result
        self.user.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND,
                                              wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.user.CallWindowProcW.restype = result
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

    def set_proc(self, hwnd, proc):
        address = proc if isinstance(proc, int) else ctypes.cast(proc, ctypes.c_void_p).value
        ctypes.set_last_error(0)
        previous = self.set_window(hwnd, GWLP_WNDPROC, address)
        if not previous and ctypes.get_last_error():
            raise ctypes.WinError(ctypes.get_last_error())
        return previous

    def parent(self, hwnd):
        return self.user.GetParent(hwnd)

    def exists(self, hwnd):
        return self.user.IsWindow(hwnd)

    def accept(self, hwnd, enabled):
        self.shell.DragAcceptFiles(hwnd, enabled)

    def forward(self, proc, hwnd, message, wparam, lparam):
        return self.user.CallWindowProcW(proc, hwnd, message, wparam, lparam)

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
        self.previous = {}
        # Keep this callback alive until every subclassed window is restored.
        self.proc = self.api.make_proc(self.handle_message)
        app.update_idletasks()
        handles = set()
        def collect(widget):
            handles.add(widget.winfo_id())
            for child in widget.winfo_children():
                collect(child)
        collect(app)
        parent = self.api.parent(app.winfo_id())
        if parent:
            handles.add(parent)  # Tk's outer toplevel wrapper/title bar.
        try:
            for hwnd in handles:
                self.previous[hwnd] = self.api.set_proc(hwnd, self.proc)
                self.api.accept(hwnd, True)
        except Exception:
            self.close()
            raise

    def handle_message(self, hwnd, message, wparam, lparam):
        if message == WM_DROPFILES:
            try:
                paths = self.api.paths(wparam)
                # Release the Explorer-owned drop handle before invoking Tk.
            except Exception as error:
                paths = None
                self.app.report_callback_exception(type(error), error, error.__traceback__)
            finally:
                self.api.finish(wparam)
            if paths is not None:
                # The window procedure runs on Tk's UI thread. Queue work so
                # no Tk layout changes occur inside the native message callback.
                self.app.after_idle(self.on_drop, paths)
            return 0
        previous = self.previous.get(hwnd)
        result = self.api.forward(previous, hwnd, message, wparam, lparam)
        if message == WM_NCDESTROY:
            self.previous.pop(hwnd, None)
        return result

    def close(self):
        for hwnd, previous in list(self.previous.items()):
            if self.api.exists(hwnd):
                self.api.accept(hwnd, False)
                self.api.set_proc(hwnd, previous)
            self.previous.pop(hwnd, None)
